"""Postgres persistence for prospects, categories, settings, clients and health snapshots."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any, Iterable, Optional

import psycopg
from psycopg import sql
from psycopg.rows import tuple_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from backend.config.settings import settings
from backend.domain.cleanup import (
    clean_address,
    extract_google_place_id,
    plausible_reviews_count,
    split_legacy_photo,
)
from backend.domain.prospect import Prospect, ProspectStatus
from backend.infrastructure.persistence.pg import (
    get_default_pool,
    get_readonly_pool,
    to_api_value,
)

# (name, label, default_lucide_icon_id). La migración 0001 los inserta.
DEFAULT_CATEGORIES = [
    ("cafe", "Cafe", "Coffee"),
    ("restaurante", "Restaurante", "UtensilsCrossed"),
    ("gimnasio", "Gimnasio", "Dumbbell"),
    ("barberia", "Barberia", "Scissors"),
    ("odontologia", "Odontologia", "Stethoscope"),
    ("veterinaria", "Veterinaria", "Dog"),
    ("ferreteria", "Ferreteria", "Hammer"),
    ("panaderia", "Panaderia", "CakeSlice"),
    ("estetica", "Estetica", "Sparkles"),
    ("taller", "Taller", "Wrench"),
    ("petshop", "Pet Shop", "Dog"),
    ("coworking", "Coworking", "Laptop"),
    ("reposteria", "Reposteria", "CakeSlice"),
    ("spa", "Spa", "Sparkles"),
    ("tienda", "Tienda de Ropa", "Shirt"),
    ("otros", "Otros Negocios", "Briefcase"),
]

PROSPECT_COLUMNS = frozenset(
    {
        *(f for f in Prospect.__dataclass_fields__ if f != "id"),
        "google_place_id",
        "business_photo_path",
        "business_photo_source",
        "business_photo_fetched_at",
        "business_photo_attribution",
        "legacy_photo_url",
    }
)

CLIENT_COLUMNS = (
    "prospect_id",
    "display_name",
    "category",
    "contact_email",
    "phone",
    "notes",
    "stage",
    "quote_amount",
    "quote_currency",
    "quote_pdf_path",
    "estimated_delivery_at",
    "quoted_at",
    "contract_required",
    "contract_skipped",
    "contract_signed_at",
    "contract_pdf_path",
    "payment_status",
    "github_repo_url",
    "production_domain",
    "drive_folder_url",
    "staging_url",
    "maps_url",
    "latitude",
    "longitude",
)

_TIMESTAMP_COLUMNS = frozenset(
    {
        "scraped_at",
        "contacted_at",
        "business_photo_fetched_at",
        "estimated_delivery_at",
        "quoted_at",
        "contract_signed_at",
        "scheduled_at",
    }
)
_BOOL_COLUMNS = frozenset({"is_contacted", "contract_required", "contract_skipped"})
_JSON_COLUMNS = frozenset({"business_photo_attribution"})


def _to_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def _db_value(column: str, value: Any) -> Any:
    """Adapta valores que la app manda con forma SQLite a los tipos Postgres."""
    if column in _TIMESTAMP_COLUMNS:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        return value
    if column in _BOOL_COLUMNS:
        return False if value is None else _to_bool(value)
    if column in _JSON_COLUMNS and value is not None:
        if isinstance(value, str):
            value = json.loads(value) if value.strip() else None
        return Jsonb(value) if value is not None else None
    return value


def _checked(columns: Iterable[str], allowed: Iterable[str], table: str) -> list[str]:
    allowed_set = set(allowed)
    cols = list(columns)
    unknown = [c for c in cols if c not in allowed_set]
    if unknown:
        raise ValueError(f"Columnas desconocidas en {table}: {', '.join(sorted(unknown))}")
    return cols


def _setting_to_db(raw: str) -> Jsonb:
    """Objetos y arreglos JSON se guardan como tales; todo lo demás como string JSON."""
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        parsed = None
    if isinstance(parsed, (dict, list)):
        return Jsonb(parsed)
    return Jsonb(str(raw))


def _leading_sql_verb(stmt: str) -> str:
    """
    Primer verbo de la sentencia, ignorando líneas vacías y comentarios `--` / `/* */`
    al inicio. Así un SELECT con comentario previo no se clasifica mal como mutación.
    """
    for raw in stmt.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("--"):
            continue
        while line.startswith("/*"):
            end = line.find("*/")
            if end == -1:
                break
            line = line[end + 2 :].strip()
        if not line:
            continue
        parts = line.split(None, 1)
        return parts[0].upper() if parts else ""
    return ""


_SQL_WRITE_VERBS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "MERGE",
    "DROP",
    "ALTER",
    "CREATE",
    "REPLACE",
    "ATTACH",
    "DETACH",
    "VACUUM",
    "REINDEX",
    "PRAGMA",
    "ANALYZE",
    "BEGIN",
    "COMMIT",
    "ROLLBACK",
    "SAVEPOINT",
    "RELEASE",
    "TRUNCATE",
    "GRANT",
    "REVOKE",
    "COPY",
    "LOCK",
    "CALL",
    "LISTEN",
    "NOTIFY",
    "DISCARD",
)
_SQL_DANGEROUS_FUNCTIONS = (
    "LOAD_EXTENSION",
    "WRITEFILE",
    "READFILE",
    "EDIT",
    "SET_CONFIG",
    "PG_READ_FILE",
    "PG_READ_BINARY_FILE",
    "PG_LS_DIR",
    "PG_STAT_FILE",
    "LO_IMPORT",
    "LO_EXPORT",
    "DBLINK",
    "PG_TERMINATE_BACKEND",
    "PG_CANCEL_BACKEND",
    "PG_SLEEP",
)


def _strip_sql_literals_and_comments(stmt: str) -> str:
    without_block = re.sub(r"/\*.*?\*/", " ", stmt, flags=re.S)
    without_line = re.sub(r"--.*?$", " ", without_block, flags=re.M)
    return re.sub(r"'(?:''|[^'])*'", "''", without_line)


def assert_sql_console_readonly(stmt: str) -> None:
    """Primer filtro (el segundo es la transacción READ ONLY y el rol crm_readonly)."""
    scrubbed = _strip_sql_literals_and_comments(stmt)
    verb = _leading_sql_verb(stmt)
    if verb not in {"SELECT", "WITH", "EXPLAIN"}:
        raise ValueError(
            "Sentencia rechazada: la consola solo acepta consultas de lectura (SELECT)"
        )
    for forbidden in _SQL_WRITE_VERBS:
        if re.search(rf"\b{forbidden}\b", scrubbed, re.IGNORECASE):
            raise ValueError(f"Sentencia rechazada: {forbidden} no está permitido")
    for function_name in _SQL_DANGEROUS_FUNCTIONS:
        if re.search(rf"\b{function_name}\b", scrubbed, re.IGNORECASE):
            raise ValueError(f"Sentencia rechazada: {function_name} no está permitido")
    if verb == "EXPLAIN":
        tail = re.sub(r"(?is)^\s*EXPLAIN(\s+QUERY\s+PLAN)?", "", scrubbed).strip()
        inner = _leading_sql_verb(tail)
        if inner not in {"SELECT", "WITH"}:
            raise ValueError("Sentencia rechazada: EXPLAIN solo puede envolver un SELECT")


class ProspectRepository:
    SQL_CONSOLE_MAX_ROWS = 2000
    SQL_CONSOLE_TIMEOUT = "5s"

    def __init__(
        self,
        pool: Optional[ConnectionPool] = None,
        readonly_pool: Optional[ConnectionPool] = None,
    ):
        self._pool = pool or get_default_pool()
        # Sin pool propio usa el principal; la transacción sigue siendo READ ONLY.
        self._readonly_pool = readonly_pool if pool is not None else (readonly_pool or get_readonly_pool())

    def _conn(self):
        """Conexión del pool; al salir del `with` hace commit (o rollback si hubo error)."""
        return self._pool.connection()

    def _readonly_pool_or_main(self) -> ConnectionPool:
        return self._readonly_pool or self._pool

    # ------------------------------------------------------------ prospects

    @staticmethod
    def _find_id(conn, name: str, address: str) -> Optional[int]:
        """Id del lead por (name, address). Prefiere la dirección exacta guardada y si no,
        la versión limpia: un re-scrape trae la dirección sucia y debe casar con la limpia."""
        raw = address or ""
        row = conn.execute(
            "SELECT id FROM prospects WHERE name = %s AND address = ANY(%s) "
            "ORDER BY (address = %s) DESC, id LIMIT 1",
            (name, list({raw, clean_address(raw)}), raw),
        ).fetchone()
        return int(row["id"]) if row else None

    def exists_by_name_and_address(self, name: str, address: str) -> bool:
        """True si ya hay un lead con la misma clave única (name, address) que en el scrape."""
        with self._conn() as conn:
            return self._find_id(conn, name, address) is not None

    def delete_prospect_by_id(self, prospect_id: int) -> bool:
        """Elimina el lead. clients.prospect_id queda NULL por ON DELETE SET NULL."""
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM prospects WHERE id = %s", (prospect_id,))
            return cur.rowcount > 0

    def insert_prospect(self, prospect: Prospect) -> bool:
        data = prospect.to_dict()
        data.pop("id", None)
        data["address"] = clean_address(data.get("address"))
        data["reviews_count"] = plausible_reviews_count(data.get("reviews_count"))
        place_id = extract_google_place_id(data.get("maps_url"))
        if place_id:
            data["google_place_id"] = place_id
        data["screenshot_path"], legacy_photo = split_legacy_photo(data.get("screenshot_path"))
        if legacy_photo:
            data["legacy_photo_url"] = legacy_photo
        cols = _checked(data.keys(), PROSPECT_COLUMNS, "prospects")
        query = sql.SQL(
            "INSERT INTO prospects ({cols}) VALUES ({vals}) "
            "ON CONFLICT (name, address) DO NOTHING RETURNING id"
        ).format(
            cols=sql.SQL(", ").join(map(sql.Identifier, cols)),
            vals=sql.SQL(", ").join(sql.Placeholder() * len(cols)),
        )
        try:
            with self._conn() as conn:
                row = conn.execute(query, [_db_value(c, data[c]) for c in cols]).fetchone()
                return row is not None
        except psycopg.IntegrityError:
            return False

    def insert_many(self, prospects: list[Prospect]) -> tuple[int, int]:
        inserted = sum(1 for p in prospects if self.insert_prospect(p))
        return inserted, len(prospects) - inserted

    def get_prospects(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        city: Optional[str] = None,
        is_contacted: Optional[bool] = None,
        name_query: Optional[str] = None,
        has_instagram: Optional[bool] = None,
        limit: Optional[int] = None,
    ) -> list[Prospect]:
        query = "SELECT * FROM prospects WHERE true"
        params: list[Any] = []
        if status:
            query += " AND status = %s"
            params.append(status)
        if category:
            query += " AND category = %s"
            params.append(category)
        if city:
            query += " AND city = %s"
            params.append(city)
        if is_contacted is not None:
            query += " AND is_contacted = %s"
            params.append(bool(is_contacted))
        if name_query:
            query += " AND name ILIKE %s"
            params.append(f"%{name_query}%")
        if has_instagram is not None:
            if has_instagram:
                query += " AND instagram_url IS NOT NULL AND instagram_url <> ''"
            else:
                query += " AND (instagram_url IS NULL OR instagram_url = '')"
        query += " ORDER BY scraped_at DESC NULLS LAST, id DESC"
        if limit:
            query += " LIMIT %s"
            params.append(int(limit))
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
            return [Prospect.from_dict(r) for r in rows]

    def update_status(
        self,
        name: str,
        address: str,
        status: ProspectStatus | str,
        **kwargs,
    ) -> None:
        try:
            status_val = (
                status.value
                if isinstance(status, ProspectStatus)
                else ProspectStatus(str(status)).value
            )
        except (ValueError, TypeError):
            status_val = str(status)
        self._update_prospect(name, address, {"status": status_val, **kwargs})

    def patch_prospect(self, name: str, address: str, data: dict) -> None:
        if not data:
            return
        self._update_prospect(name, address, data)

    def _update_prospect(self, name: str, address: str, data: dict) -> None:
        cols = _checked(data.keys(), PROSPECT_COLUMNS, "prospects")
        query = sql.SQL("UPDATE prospects SET {sets} WHERE id = %s").format(
            sets=sql.SQL(", ").join(
                sql.SQL("{} = %s").format(sql.Identifier(c)) for c in cols
            )
        )
        with self._conn() as conn:
            prospect_id = self._find_id(conn, name, address)
            if prospect_id is None:
                return
            conn.execute(query, [_db_value(c, data[c]) for c in cols] + [prospect_id])

    def get_random_prospect(
        self, status: str = "scraped", exclude_name: Optional[str] = None
    ) -> Optional[Prospect]:
        query = "SELECT * FROM prospects WHERE status = %s"
        params: list[Any] = [status]
        if exclude_name:
            query += " AND name <> %s"
            params.append(exclude_name)
        query += " ORDER BY random() LIMIT 1"
        with self._conn() as conn:
            row = conn.execute(query, params).fetchone()
            return Prospect.from_dict(row) if row else None

    def get_prospect_id_by_name(self, name: str) -> Optional[int]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id FROM prospects WHERE name = %s ORDER BY id LIMIT 1", (name,)
            ).fetchone()
            return int(row["id"]) if row else None

    def get_prospect_by_id(self, prospect_id: int) -> Optional[Prospect]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM prospects WHERE id = %s", (prospect_id,)).fetchone()
            return Prospect.from_dict(row) if row else None

    def count_by_status(self) -> dict[str, int]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) AS count FROM prospects GROUP BY status"
            ).fetchall()
            return {r["status"]: int(r["count"]) for r in rows}

    def get_categories(self) -> list[str]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT category FROM prospects ORDER BY category"
            ).fetchall()
            return [r["category"] for r in rows]

    def get_cities(self) -> list[str]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT city FROM prospects "
                "WHERE city IS NOT NULL AND city <> '' ORDER BY city"
            ).fetchall()
            return [r["city"] for r in rows]

    def compute_lead_score(self, p: Prospect) -> int:
        score = 0
        if p.phone:
            score += 25
        if p.ig_phone:
            score += 10
        if p.ig_email:
            score += 20
        if p.website or p.ig_website:
            score += 10
        if p.instagram_url:
            score += 10
        if p.ig_bio:
            score += 5
        if (p.rating or 0) > 0:
            score += 10
        if (p.reviews_count or 0) > 0:
            score += 10
        return min(score, 100)

    # ------------------------------------------------------------ SQL console

    def execute_sql_console(self, sql_text: str) -> dict[str, Any]:
        """Una sola sentencia de lectura, en transacción READ ONLY con timeout, siempre rollback."""
        raw = (sql_text or "").strip()
        if not raw:
            raise ValueError("SQL vacío")
        stmt = raw.rstrip(";").strip()
        if not stmt:
            raise ValueError("SQL vacío")
        if ";" in stmt:
            raise ValueError("Solo una sentencia a la vez (sin punto y coma interior)")
        assert_sql_console_readonly(stmt)

        pool = self._readonly_pool_or_main()
        cap = self.SQL_CONSOLE_MAX_ROWS
        with pool.connection() as conn:
            with conn.transaction(force_rollback=True):
                conn.execute("SET TRANSACTION READ ONLY")
                conn.execute(f"SET LOCAL statement_timeout = '{self.SQL_CONSOLE_TIMEOUT}'")
                cur = conn.cursor(row_factory=tuple_row)
                # Sin parámetros psycopg no interpreta '%', así que LIKE '%x%' funciona.
                cur.execute(stmt, prepare=False)  # type: ignore[arg-type]
                desc = [d.name for d in (cur.description or [])]
                rows_out: list[dict[str, Any]] = []
                while len(rows_out) < cap:
                    chunk = cur.fetchmany(min(500, cap - len(rows_out)))
                    if not chunk:
                        break
                    for row in chunk:
                        rows_out.append({col: to_api_value(v) for col, v in zip(desc, row)})
                truncated = len(rows_out) == cap and cur.fetchone() is not None
        return {
            "kind": "select",
            "columns": desc,
            "rows": rows_out,
            "rowcount": len(rows_out),
            "truncated": truncated,
        }

    # ------------------------------------------------------------ categories

    def normalize_categories(self) -> None:
        catalog = self.get_catalog_categories()
        with self._conn() as conn:
            for cat in catalog:
                name = cat["name"]
                label = cat.get("label", "")
                label_clean = label.split(" ", 1)[-1].strip().lower() if label else name
                conn.execute(
                    "UPDATE prospects SET category = %s "
                    "WHERE category <> %s AND (lower(category) = %s OR lower(category) = %s)",
                    (name, name, name, label_clean),
                )

    def update_category(self, old_name: str, new_name: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE prospects SET category = %s WHERE category = %s",
                (new_name, old_name),
            )

    def rename_category_globally(self, old_name: str, new_name: str) -> None:
        """Rename catalog id and all prospect rows using that category (transactional)."""
        if not old_name or not new_name or old_name == new_name:
            raise ValueError("Nombres invalidos")
        with self._conn() as conn:
            cat = conn.execute(
                "SELECT 1 FROM category_catalog WHERE name = %s FOR UPDATE", (old_name,)
            ).fetchone()
            if not cat:
                raise ValueError("La categoria no existe en el catalogo")
            taken = conn.execute(
                "SELECT 1 FROM category_catalog WHERE name = %s", (new_name,)
            ).fetchone()
            if taken:
                raise ValueError("Ya existe una categoria con ese id")
            conn.execute(
                "UPDATE prospects SET category = %s WHERE category = %s",
                (new_name, old_name),
            )
            conn.execute(
                "UPDATE category_catalog SET name = %s WHERE name = %s",
                (new_name, old_name),
            )

    def patch_catalog_category(
        self, name: str, label: Optional[str] = None, icon: Optional[str] = None
    ) -> bool:
        if label is None and icon is None:
            return False
        sets: list[str] = []
        params: list[Any] = []
        if label is not None:
            sets.append("label = %s")
            params.append(label)
        if icon is not None:
            sets.append("icon = %s")
            params.append(icon)
        params.append(name)
        with self._conn() as conn:
            cur = conn.execute(
                f"UPDATE category_catalog SET {', '.join(sets)} WHERE name = %s",
                params,
            )
            return cur.rowcount > 0

    def delete_category(self, category: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE prospects SET category = 'Sin categoría' WHERE category = %s",
                (category,),
            )

    def get_catalog_categories(self) -> list[dict]:
        with self._conn() as conn:
            return conn.execute(
                "SELECT name, label, icon FROM category_catalog ORDER BY label"
            ).fetchall()

    def add_catalog_category(self, name: str, label: str, icon: str = "") -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO category_catalog (name, label, icon) VALUES (%s, %s, %s)",
                (name, label, icon),
            )

    def delete_catalog_category(self, name: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM category_catalog WHERE name = %s", (name,))

    # ------------------------------------------------------------ settings

    def get_app_settings_raw(self) -> dict[str, str]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT key, CASE WHEN jsonb_typeof(value) = 'string' "
                "THEN value #>> '{}' ELSE value::text END AS value FROM app_settings"
            ).fetchall()
            return {str(r["key"]): str(r["value"]) for r in rows}

    def upsert_app_settings(self, partial: dict[str, str]) -> None:
        if not partial:
            return
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO app_settings (key, value, updated_at)
                    VALUES (%s, %s, now())
                    ON CONFLICT (key) DO UPDATE SET
                        value = EXCLUDED.value,
                        updated_at = EXCLUDED.updated_at
                    """,
                    [(k, _setting_to_db(v)) for k, v in partial.items()],
                )

    # ------------------------------------------------------------ health

    def get_health_snapshot(self) -> dict:
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE rating > 0) AS rating_gt_0,
                    COUNT(*) FILTER (WHERE reviews_count > 0) AS reviews_gt_0,
                    COUNT(*) FILTER (WHERE COALESCE(website, '') <> '') AS website_non_empty,
                    COUNT(*) FILTER (WHERE COALESCE(phone, '') <> '') AS phone_non_empty,
                    COUNT(*) FILTER (WHERE COALESCE(instagram_url, '') <> '') AS instagram_url_non_empty,
                    COUNT(*) FILTER (WHERE COALESCE(ig_bio, '') <> '') AS ig_bio_non_empty,
                    COUNT(*) FILTER (WHERE ig_followers > 0) AS ig_followers_gt_0,
                    COUNT(*) FILTER (WHERE COALESCE(ig_email, '') <> '') AS ig_email_non_empty,
                    COUNT(*) FILTER (WHERE COALESCE(ig_phone, '') <> '') AS ig_phone_non_empty,
                    now() AS created_at
                FROM prospects
                """
            ).fetchone()
        snap = {k: (int(v) if k != "created_at" else v) for k, v in row.items()}
        return {"created_at": snap.pop("created_at"), **snap}

    def record_health_snapshot(self) -> dict:
        snap = self.get_health_snapshot()
        cols = list(snap.keys())
        query = sql.SQL("INSERT INTO health_history ({cols}) VALUES ({vals})").format(
            cols=sql.SQL(", ").join(map(sql.Identifier, cols)),
            vals=sql.SQL(", ").join(sql.Placeholder() * len(cols)),
        )
        with self._conn() as conn:
            conn.execute(query, [snap[k] for k in cols])
        return snap

    def get_recent_health_history(self, limit: int = 20) -> list[dict]:
        with self._conn() as conn:
            return conn.execute(
                "SELECT * FROM health_history ORDER BY id DESC LIMIT %s",
                (int(limit),),
            ).fetchall()

    # ------------------------------------------------------------ exports

    def export_json(self, filepath: Optional[Path] = None, **filters) -> Path:
        prospects = self.get_prospects(**filters)
        path = filepath or settings.data_dir / "prospects.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump([p.to_dict() for p in prospects], f, ensure_ascii=False, indent=2)
        return path

    def export_csv(self, filepath: Optional[Path] = None, **filters) -> Path:
        prospects = self.get_prospects(**filters)
        path = filepath or settings.data_dir / "prospects.csv"
        first = prospects[0].to_dict() if prospects else {}
        fieldnames = list(first.keys())
        with open(path, "w", newline="", encoding="utf-8") as f:
            if fieldnames:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for p in prospects:
                    writer.writerow(p.to_dict())
        return path

    # ------------------------------------------------------------ clients

    def client_exists_for_prospect(self, prospect_id: int) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM clients WHERE prospect_id = %s LIMIT 1",
                (prospect_id,),
            ).fetchone()
            return row is not None

    def list_clients(self) -> list[dict]:
        with self._conn() as conn:
            return conn.execute("SELECT * FROM clients ORDER BY updated_at DESC").fetchall()

    def list_clients_map_markers(self) -> list[dict]:
        """Clientes con coordenadas: propias o heredadas del lead vinculado."""
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT c.id, c.display_name, c.category, c.stage, c.prospect_id,
                    COALESCE(NULLIF(c.latitude, 0), NULLIF(pr.latitude, 0)) AS lat,
                    COALESCE(NULLIF(c.longitude, 0), NULLIF(pr.longitude, 0)) AS lng,
                    COALESCE(NULLIF(c.maps_url, ''), NULLIF(pr.maps_url, ''), '') AS maps_url
                FROM clients c
                LEFT JOIN prospects pr ON c.prospect_id = pr.id
                """
            ).fetchall()
        out: list[dict] = []
        for r in rows:
            lat, lng = r["lat"], r["lng"]
            if lat is None or lng is None:
                continue
            try:
                la, ln = float(lat), float(lng)
            except (TypeError, ValueError):
                continue
            if la == 0 and ln == 0:
                continue
            out.append(
                {
                    "id": int(r["id"]),
                    "display_name": r["display_name"] or "",
                    "category": r["category"] or "",
                    "stage": r["stage"] or "quote_sent",
                    "latitude": la,
                    "longitude": ln,
                    "maps_url": r["maps_url"] or "",
                }
            )
        return out

    def get_client(self, client_id: int) -> Optional[dict]:
        with self._conn() as conn:
            return conn.execute("SELECT * FROM clients WHERE id = %s", (client_id,)).fetchone()

    def insert_client(self, data: dict) -> int:
        row = {c: data[c] for c in CLIENT_COLUMNS if c in data}
        row.setdefault("display_name", "")
        row.setdefault("stage", "quote_sent")
        cols = list(row.keys())
        query = sql.SQL("INSERT INTO clients ({cols}) VALUES ({vals}) RETURNING id").format(
            cols=sql.SQL(", ").join(map(sql.Identifier, cols)),
            vals=sql.SQL(", ").join(sql.Placeholder() * len(cols)),
        )
        with self._conn() as conn:
            new = conn.execute(query, [_db_value(c, row[c]) for c in cols]).fetchone()
            return int(new["id"])

    def update_client(self, client_id: int, data: dict) -> None:
        if not data:
            return
        updates = {k: v for k, v in data.items() if k in CLIENT_COLUMNS}
        if not updates:
            return
        cols = list(updates.keys())
        query = sql.SQL("UPDATE clients SET {sets}, updated_at = now() WHERE id = %s").format(
            sets=sql.SQL(", ").join(
                sql.SQL("{} = %s").format(sql.Identifier(c)) for c in cols
            )
        )
        with self._conn() as conn:
            conn.execute(query, [_db_value(c, updates[c]) for c in cols] + [client_id])

    def delete_client(self, client_id: int) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM clients WHERE id = %s", (client_id,))

    def touch_client_updated_at(self, client_id: int) -> None:
        with self._conn() as conn:
            conn.execute("UPDATE clients SET updated_at = now() WHERE id = %s", (client_id,))

    def get_client_meeting(self, meeting_id: int) -> Optional[dict]:
        with self._conn() as conn:
            return conn.execute(
                "SELECT * FROM client_meetings WHERE id = %s", (meeting_id,)
            ).fetchone()

    def list_client_meetings(self, client_id: int) -> list[dict]:
        with self._conn() as conn:
            return conn.execute(
                "SELECT * FROM client_meetings WHERE client_id = %s ORDER BY scheduled_at, id",
                (client_id,),
            ).fetchall()

    def insert_client_meeting(self, client_id: int, data: dict) -> int:
        title = data.get("title", "")
        scheduled_at = _db_value("scheduled_at", data.get("scheduled_at"))
        duration_min = int(data.get("duration_min", 60))
        notes = data.get("notes", "")
        status = data.get("status", "scheduled")
        with self._conn() as conn:
            row = conn.execute(
                """
                INSERT INTO client_meetings (client_id, title, scheduled_at, duration_min, notes, status)
                VALUES (%s, %s, COALESCE(%s::timestamptz, now()), %s, %s, %s)
                RETURNING id
                """,
                (client_id, title, scheduled_at, duration_min, notes, status),
            ).fetchone()
            conn.execute("UPDATE clients SET updated_at = now() WHERE id = %s", (client_id,))
            return int(row["id"])

    def update_client_meeting(self, meeting_id: int, data: dict) -> None:
        allowed = ("title", "scheduled_at", "duration_min", "notes", "status")
        updates = {k: v for k, v in data.items() if k in allowed}
        if not updates:
            return
        if "duration_min" in updates:
            updates["duration_min"] = int(updates["duration_min"])
        cols = list(updates.keys())
        query = sql.SQL(
            "UPDATE client_meetings SET {sets} WHERE id = %s RETURNING client_id"
        ).format(
            sets=sql.SQL(", ").join(
                sql.SQL("{} = %s").format(sql.Identifier(c)) for c in cols
            )
        )
        with self._conn() as conn:
            row = conn.execute(
                query, [_db_value(c, updates[c]) for c in cols] + [meeting_id]
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE clients SET updated_at = now() WHERE id = %s", (row["client_id"],)
                )

    def delete_client_meeting(self, meeting_id: int) -> None:
        with self._conn() as conn:
            row = conn.execute(
                "DELETE FROM client_meetings WHERE id = %s RETURNING client_id", (meeting_id,)
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE clients SET updated_at = now() WHERE id = %s", (row["client_id"],)
                )

    def create_client_from_prospect_name(self, prospect_name: str) -> int:
        pid = self.get_prospect_id_by_name(prospect_name)
        if pid is None:
            raise ValueError("Prospecto no encontrado")
        if self.client_exists_for_prospect(pid):
            raise ValueError("Ya existe un cliente para este lead")
        p = self.get_prospect_by_id(pid)
        if not p:
            raise ValueError("Prospecto no encontrado")
        data = {
            "prospect_id": pid,
            "display_name": p.name,
            "category": p.category,
            "phone": p.get_best_phone(),
            "contact_email": p.ig_email or "",
            "notes": (p.notes or "")[:2000],
            "stage": "quote_sent",
            "latitude": float(p.latitude or 0),
            "longitude": float(p.longitude or 0),
        }
        return self.insert_client(data)
