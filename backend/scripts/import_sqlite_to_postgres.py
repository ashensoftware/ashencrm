"""Importación única SQLite -> Supabase Postgres (data-platform D4, paso 2).

Reemplaza el contenido de las tablas destino con el de los archivos SQLite
(SQLite es la fuente de verdad) y aplica las limpiezas D9 en el camino:

- reviews_count > 50 000 -> NULL
- address: sin prefijo de categoría, íconos ni texto de la tarjeta de Maps
- screenshot_path con URL -> legacy_photo_url (screenshot_path queda vacío)
- google_place_id extraído de maps_url

Todo ocurre en una transacción: TRUNCATE, inserción con los ids originales,
reinicio de secuencias y verificación por checksum. Sin --apply se hace
ROLLBACK al final, así que el ensayo valida contra las restricciones reales
sin dejar nada escrito. Es idempotente: correrlo dos veces deja lo mismo.

No imprime filas ni datos personales: solo conteos, ids y checksums.

Uso:
  python -m backend.scripts.import_sqlite_to_postgres                      # ensayo
  python -m backend.scripts.import_sqlite_to_postgres --apply
  python -m backend.scripts.import_sqlite_to_postgres --platform-db ruta/platform.db --apply
"""

from __future__ import annotations

import argparse
import hashlib
import sqlite3
import sys
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

from backend.config.settings import settings
from backend.domain.cleanup import (
    REVIEWS_COUNT_MAX,
    clean_address,
    extract_google_place_id,
    plausible_reviews_count,
    split_legacy_photo,
)
from backend.domain.prospect import ProspectStatus
from backend.infrastructure.persistence.pg import BUSINESS_TIME_ZONE, connection_kwargs
from backend.infrastructure.persistence.prospect_repository import _setting_to_db

# Orden de inserción (padres antes que hijos).
CRM_TABLES = (
    "category_catalog",
    "prospects",
    "clients",
    "client_meetings",
    "app_settings",
    "health_history",
)
PLATFORM_TABLES = (
    "pipeline_runs",
    "pipeline_steps",
    "pipeline_events",
    "businesses",
    "field_observations",
    "provider_connections",
    "suppression_entries",
    "outreach_consents",
    "outreach_messages",
    "audit_log",
)
# Columnas que entran al checksum (se comparan origen limpio vs. lo leído de Postgres).
KEY_COLUMNS = {
    "category_catalog": ("id", "name", "label", "icon"),
    "prospects": ("id", "name", "address", "category", "status", "phone", "maps_url", "google_place_id"),
    "clients": ("id", "prospect_id", "display_name", "stage", "quote_pdf_path"),
    "client_meetings": ("id", "client_id", "title", "status"),
    "app_settings": ("key",),
    "health_history": ("id", "total"),
    "pipeline_runs": ("id", "campaign_id", "status"),
    "pipeline_steps": ("id", "run_id", "sequence", "status", "attempt"),
    "pipeline_events": ("id", "run_id", "event_type"),
    "businesses": ("id", "provider", "external_id", "version"),
    "field_observations": ("id", "business_id", "field_name"),
    "provider_connections": ("id", "status", "enabled"),
    "suppression_entries": ("id", "normalized_contact", "channel"),
    "outreach_consents": ("id", "normalized_contact", "channel", "status"),
    "outreach_messages": ("id", "status", "dry_run"),
    "audit_log": ("id", "method", "path", "status_code"),
}
_STATUS_RANK = {s.value: i for i, s in enumerate(ProspectStatus)}


def _read_sqlite(path: Path, tables: tuple[str, ...]) -> dict[str, list[dict[str, Any]]]:
    if not path.exists():
        raise SystemExit(f"No existe {path}")
    conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        present = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        unknown = present - set(tables)
        if unknown:
            raise SystemExit(f"{path.name} tiene tablas sin destino: {sorted(unknown)}")
        order_by = {"app_settings": "key"}
        return {
            t: [dict(r) for r in conn.execute(f'SELECT * FROM "{t}" ORDER BY {order_by.get(t, "id")}')]
            for t in tables
            if t in present
        }
    finally:
        conn.close()


def _clean_prospects(rows: list[dict[str, Any]], report: dict[str, Any]) -> None:
    """Aplica D9. Si la dirección limpia choca con otra fila del mismo nombre
    (mismo negocio scrapeado dos veces), solo la fila más avanzada la recibe;
    las demás conservan la original para no romper UNIQUE(name, address)."""
    counts = {"reviews_nulled": 0, "address_cleaned": 0, "photo_moved": 0, "place_id": 0}
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        if row.get("reviews_count") is not None and plausible_reviews_count(row["reviews_count"]) is None:
            counts["reviews_nulled"] += 1
        row["reviews_count"] = plausible_reviews_count(row.get("reviews_count"))
        shot, legacy = split_legacy_photo(row.get("screenshot_path"))
        if legacy:
            counts["photo_moved"] += 1
        row["screenshot_path"], row["legacy_photo_url"] = shot, legacy
        row["google_place_id"] = extract_google_place_id(row.get("maps_url"))
        counts["place_id"] += row["google_place_id"] is not None
        groups.setdefault((row["name"], clean_address(row.get("address"))), []).append(row)

    kept_raw: list[int] = []
    for (_, cleaned), members in groups.items():
        members.sort(key=lambda r: (-_STATUS_RANK.get(r.get("status") or "", -1), r["id"]))
        winner, *others = members
        if winner.get("address") != cleaned:
            counts["address_cleaned"] += 1
        winner["address"] = cleaned
        kept_raw.extend(r["id"] for r in others)
    counts["duplicates_kept_raw_address"] = len(kept_raw)
    report["prospects_cleanup"] = counts
    report["duplicate_ids_kept_raw_address"] = sorted(kept_raw)


def _target_columns(conn: psycopg.Connection, table: str) -> dict[str, str]:
    rows = conn.execute(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = %s",
        (table,),
    ).fetchall()
    return {name: dtype for name, dtype in rows}


def _convert(table: str, column: str, dtype: str, value: Any) -> Any:
    if value is None:
        return None
    if dtype == "timestamp with time zone":
        return value if isinstance(value, str) and value.strip() else None
    if dtype == "boolean":
        return bool(int(value)) if not isinstance(value, bool) else value
    if dtype == "jsonb":
        if table == "app_settings" and column == "value":
            return _setting_to_db(value)
        return value if isinstance(value, str) else Jsonb(value)
    return value


def _checksum(rows: list[dict[str, Any]], columns: tuple[str, ...]) -> str:
    def norm(v: Any) -> str:
        if isinstance(v, bool):
            return str(int(v))
        if isinstance(v, float) and v.is_integer():
            return str(int(v))
        return "" if v is None else str(v)

    lines = sorted("\x1f".join(norm(r.get(c)) for c in columns) for r in rows)
    return hashlib.sha256("\x1e".join(lines).encode("utf-8")).hexdigest()[:16]


def _count(conn: psycopg.Connection, table: str) -> int:
    return conn.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))).fetchone()[0]


def run(prospects_db: Path, platform_db: Path | None, apply: bool) -> int:
    url = settings.database_url
    if not url:
        raise SystemExit("Falta DATABASE_URL (rol crm_app) en .env")
    schema = settings.database_schema

    sources: dict[str, list[dict[str, Any]]] = {}
    sources.update(_read_sqlite(prospects_db, CRM_TABLES))
    if platform_db is not None:
        sources.update(_read_sqlite(platform_db, PLATFORM_TABLES))
    tables = [t for t in (*CRM_TABLES, *PLATFORM_TABLES) if t in sources]

    report: dict[str, Any] = {}
    if "prospects" in sources:
        _clean_prospects(sources["prospects"], report)
    for client in sources.get("clients", []):
        if (client.get("quote_pdf_path") or "").strip() or (client.get("contract_pdf_path") or "").strip():
            raise SystemExit(
                f"El cliente {client['id']} tiene PDF local. Falta D2 (bucket ashencrm-files) para subirlo."
            )

    kwargs = connection_kwargs(url)
    kwargs.pop("row_factory", None)
    print(f"Destino: schema {schema} | modo: {'APPLY' if apply else 'ENSAYO (rollback)'}")
    print(f"Origen: {prospects_db}" + (f" + {platform_db}" if platform_db else " (sin platform.db: tablas de plataforma intactas)"))

    with psycopg.connect(url, **kwargs) as conn:
        conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        # Los ISO sin zona de SQLite se escribieron en Medellín.
        conn.execute(sql.SQL("SET TIME ZONE {}").format(sql.Literal(BUSINESS_TIME_ZONE)))
        conn.commit()
        failed = False
        tx = conn.transaction(force_rollback=not apply)
        with tx:
            before = {t: _count(conn, t) for t in tables}
            conn.execute(
                sql.SQL("TRUNCATE {} RESTART IDENTITY CASCADE").format(
                    sql.SQL(", ").join(map(sql.Identifier, tables))
                )
            )
            for table in tables:
                rows = sources[table]
                target = _target_columns(conn, table)
                source_cols = list(rows[0].keys()) if rows else []
                missing = [c for c in source_cols if c not in target]
                if missing:
                    raise SystemExit(f"{table}: columnas sin destino en Postgres: {missing}")
                if rows:
                    query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                        sql.Identifier(table),
                        sql.SQL(", ").join(map(sql.Identifier, source_cols)),
                        sql.SQL(", ").join(sql.Placeholder() * len(source_cols)),
                    )
                    with conn.cursor() as cur:
                        cur.executemany(
                            query,
                            [
                                [_convert(table, c, target[c], r[c]) for c in source_cols]
                                for r in rows
                            ],
                        )
                if "id" in target and target["id"] == "bigint":
                    conn.execute(
                        sql.SQL(
                            "SELECT setval(pg_get_serial_sequence({t}, 'id'), "
                            "COALESCE((SELECT max(id) FROM {i}), 0) + 1, false)"
                        ).format(t=sql.Literal(table), i=sql.Identifier(table))
                    )

            print(f"\n{'tabla':<22}{'antes':>7}{'origen':>8}{'después':>9}  checksum")
            for table in tables:
                cols = KEY_COLUMNS[table]
                after_rows = [
                    dict(zip(cols, r))
                    for r in conn.execute(
                        sql.SQL("SELECT {} FROM {}").format(
                            sql.SQL(", ").join(map(sql.Identifier, cols)), sql.Identifier(table)
                        )
                    ).fetchall()
                ]
                src_sum = _checksum(sources[table], cols)
                dst_sum = _checksum(after_rows, cols)
                ok = src_sum == dst_sum and len(after_rows) == len(sources[table])
                failed |= not ok
                print(
                    f"{table:<22}{before[table]:>7}{len(sources[table]):>8}{len(after_rows):>9}  "
                    f"{dst_sum} {'OK' if ok else 'DIFIERE de ' + src_sum}"
                )

            if "prospects" in sources:
                c = report["prospects_cleanup"]
                ts = conn.execute(
                    "SELECT count(*) FILTER (WHERE scraped_at IS NOT NULL), "
                    "min(scraped_at)::text, max(scraped_at)::text FROM prospects"
                ).fetchone()
                print(
                    f"\nD9: reviews_count > {REVIEWS_COUNT_MAX:,} anulados: {c['reviews_nulled']} | "
                    f"direcciones limpiadas: {c['address_cleaned']} | fotos -> legacy_photo_url: {c['photo_moved']} | "
                    f"google_place_id: {c['place_id']}"
                )
                print(
                    f"Duplicados (mismo nombre y dirección limpia) que conservan la dirección original: "
                    f"{c['duplicates_kept_raw_address']} -> ids {report['duplicate_ids_kept_raw_address']}"
                )
                print(f"scraped_at: {ts[0]} con valor, rango {ts[1]} .. {ts[2]}")
            if failed:
                raise SystemExit("Checksum o conteo distinto: transacción revertida, nada escrito.")
        print("\nAPLICADO." if apply else "\nEnsayo correcto. Nada escrito. Repite con --apply.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--prospects-db", type=Path, default=settings.db_path)
    parser.add_argument(
        "--platform-db",
        type=Path,
        default=None,
        help="platform.db del VM. Sin él, las tablas de plataforma no se tocan.",
    )
    parser.add_argument("--apply", action="store_true", help="Escribe. Sin esto, ensayo con rollback.")
    args = parser.parse_args()
    return run(args.prospects_db, args.platform_db, args.apply)


if __name__ == "__main__":
    sys.exit(main())
