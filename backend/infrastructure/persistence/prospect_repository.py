"""SQLite persistence for prospects, categories and health snapshots."""

import csv
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from backend.config.settings import settings
from backend.domain.prospect import Prospect, ProspectStatus

# (name, label, default_lucide_icon_id) — iconos persistidos en category_catalog.icon
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

MIGRATION_CATEGORY_DEFAULT_ICONS_V1 = "migration_category_default_icons_v1"


class ProspectRepository:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _conn(self) -> sqlite3.Connection:
        return self._get_conn()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS prospects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    address TEXT DEFAULT '',
                    city TEXT DEFAULT '',
                    phone TEXT DEFAULT '',
                    website TEXT DEFAULT '',
                    rating REAL DEFAULT 0.0,
                    reviews_count INTEGER DEFAULT 0,
                    maps_url TEXT DEFAULT '',
                    latitude REAL DEFAULT 0.0,
                    longitude REAL DEFAULT 0.0,
                    instagram_url TEXT DEFAULT '',
                    instagram_handle TEXT DEFAULT '',
                    ig_followers INTEGER DEFAULT 0,
                    ig_bio TEXT DEFAULT '',
                    ig_email TEXT DEFAULT '',
                    ig_phone TEXT DEFAULT '',
                    ig_website TEXT DEFAULT '',
                    demo_url TEXT DEFAULT '',
                    screenshot_path TEXT DEFAULT '',
                    lovable_account_used TEXT DEFAULT '',
                    prompt_used TEXT DEFAULT '',
                    whatsapp_message TEXT DEFAULT '',
                    status TEXT DEFAULT 'scraped',
                    scraped_at TEXT DEFAULT '',
                    contacted_at TEXT DEFAULT '',
                    is_contacted INTEGER DEFAULT 0,
                    notes TEXT DEFAULT '',
                    UNIQUE(name, address)
                );
                CREATE TABLE IF NOT EXISTS category_catalog (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    label TEXT NOT NULL,
                    icon TEXT DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS health_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    total INTEGER DEFAULT 0,
                    rating_gt_0 INTEGER DEFAULT 0,
                    reviews_gt_0 INTEGER DEFAULT 0,
                    website_non_empty INTEGER DEFAULT 0,
                    phone_non_empty INTEGER DEFAULT 0,
                    instagram_url_non_empty INTEGER DEFAULT 0,
                    ig_bio_non_empty INTEGER DEFAULT 0,
                    ig_followers_gt_0 INTEGER DEFAULT 0,
                    ig_email_non_empty INTEGER DEFAULT 0,
                    ig_phone_non_empty INTEGER DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prospect_id INTEGER UNIQUE,
                    display_name TEXT NOT NULL,
                    category TEXT DEFAULT '',
                    contact_email TEXT DEFAULT '',
                    phone TEXT DEFAULT '',
                    notes TEXT DEFAULT '',
                    stage TEXT NOT NULL DEFAULT 'quote_sent',
                    quote_amount REAL,
                    quote_currency TEXT DEFAULT 'COP',
                    quote_pdf_path TEXT DEFAULT '',
                    estimated_delivery_at TEXT DEFAULT '',
                    quoted_at TEXT DEFAULT '',
                    contract_required INTEGER DEFAULT 0,
                    contract_skipped INTEGER DEFAULT 0,
                    contract_signed_at TEXT DEFAULT '',
                    contract_pdf_path TEXT DEFAULT '',
                    payment_status TEXT DEFAULT 'pending',
                    github_repo_url TEXT DEFAULT '',
                    production_domain TEXT DEFAULT '',
                    drive_folder_url TEXT DEFAULT '',
                    staging_url TEXT DEFAULT '',
                    maps_url TEXT DEFAULT '',
                    latitude REAL DEFAULT 0,
                    longitude REAL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (prospect_id) REFERENCES prospects(id) ON DELETE SET NULL
                );
                CREATE TABLE IF NOT EXISTS client_meetings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER NOT NULL,
                    title TEXT DEFAULT '',
                    scheduled_at TEXT NOT NULL,
                    duration_min INTEGER DEFAULT 60,
                    notes TEXT DEFAULT '',
                    status TEXT DEFAULT 'scheduled',
                    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_clients_stage ON clients(stage);
                CREATE INDEX IF NOT EXISTS idx_meetings_client ON client_meetings(client_id);
            """)
            cur = conn.execute("SELECT COUNT(*) FROM category_catalog")
            if cur.fetchone()[0] == 0:
                conn.executemany(
                    "INSERT INTO category_catalog (name, label, icon) VALUES (?, ?, ?)",
                    DEFAULT_CATEGORIES,
                )
            self._maybe_backfill_default_category_icons(conn)
            try:
                conn.execute(
                    "ALTER TABLE prospects ADD COLUMN is_contacted INTEGER DEFAULT 0"
                )
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute(
                    "ALTER TABLE prospects ADD COLUMN whatsapp_message TEXT DEFAULT ''"
                )
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE clients ADD COLUMN latitude REAL DEFAULT 0")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE clients ADD COLUMN longitude REAL DEFAULT 0")
            except sqlite3.OperationalError:
                pass
            conn.commit()

    def _maybe_backfill_default_category_icons(self, conn: sqlite3.Connection) -> None:
        """Una sola vez: rellena icon Lucide vacío según DEFAULT_CATEGORIES (BD existentes)."""
        if conn.execute(
            "SELECT 1 FROM app_settings WHERE key = ?",
            (MIGRATION_CATEGORY_DEFAULT_ICONS_V1,),
        ).fetchone():
            return
        for name, _label, icon in DEFAULT_CATEGORIES:
            conn.execute(
                "UPDATE category_catalog SET icon = ? WHERE name = ? AND (icon IS NULL OR TRIM(icon) = '')",
                (icon, name),
            )
        conn.execute(
            """
            INSERT INTO app_settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """,
            (
                MIGRATION_CATEGORY_DEFAULT_ICONS_V1,
                "1",
                datetime.now().isoformat(),
            ),
        )

    def insert_prospect(self, prospect: Prospect) -> bool:
        try:
            with self._conn() as conn:
                data = prospect.to_dict()
                data.pop("id", None)
                cols = ", ".join(data.keys())
                placeholders = ", ".join(["?"] * len(data))
                conn.execute(
                    f"INSERT INTO prospects ({cols }) VALUES ({placeholders })",
                    list(data.values()),
                )
                conn.commit()
                return True
        except sqlite3.IntegrityError:
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
        query = "SELECT * FROM prospects WHERE 1=1"
        params: list = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if category:
            query += " AND category = ?"
            params.append(category)
        if city:
            query += " AND city = ?"
            params.append(city)
        if is_contacted is not None:
            query += " AND is_contacted = ?"
            params.append(1 if is_contacted else 0)
        if name_query:
            query += " AND name LIKE ?"
            params.append(f"%{name_query }%")
        if has_instagram is not None:
            if has_instagram:
                query += " AND instagram_url IS NOT NULL AND instagram_url <> ''"
            else:
                query += " AND (instagram_url IS NULL OR instagram_url = '')"
        query += " ORDER BY scraped_at DESC"
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
            return [Prospect.from_dict(dict(r)) for r in rows]

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
        updates = ["status = ?"]
        params: list = [status_val]
        for k, v in kwargs.items():
            updates.append(f"{k } = ?")
            params.append(v)
        params.extend([name, address])
        with self._conn() as conn:
            conn.execute(
                f"UPDATE prospects SET {', '.join (updates )} WHERE name = ? AND address = ?",
                params,
            )
            conn.commit()

    def patch_prospect(self, name: str, address: str, data: dict) -> None:
        if not data:
            return
        updates = [f"{k } = ?" for k in data]
        params = list(data.values()) + [name, address]
        with self._conn() as conn:
            conn.execute(
                f"UPDATE prospects SET {', '.join (updates )} WHERE name = ? AND address = ?",
                params,
            )
            conn.commit()

    def count_by_status(self) -> dict[str, int]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) as count FROM prospects GROUP BY status"
            ).fetchall()
            return {r["status"]: r["count"] for r in rows}

    def get_categories(self) -> list[str]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT category FROM prospects ORDER BY category"
            ).fetchall()
            return [r["category"] for r in rows]

    def get_cities(self) -> list[str]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT city FROM prospects WHERE city IS NOT NULL AND city <> '' ORDER BY city"
            ).fetchall()
            return [r["city"] for r in rows]

    def normalize_categories(self) -> None:
        catalog = self.get_catalog_categories()
        with self._conn() as conn:
            for cat in catalog:
                name = cat["name"]
                label = cat.get("label", "")
                label_clean = label.split(" ", 1)[-1].strip().lower() if label else name
                conn.execute(
                    "UPDATE prospects SET category = ? WHERE LOWER(category) = ? OR LOWER(category) = ?",
                    (name, name, label_clean),
                )
            conn.commit()

    def update_category(self, old_name: str, new_name: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE prospects SET category = ? WHERE category = ?",
                (new_name, old_name),
            )
            conn.commit()

    def rename_category_globally(self, old_name: str, new_name: str) -> None:
        """Rename catalog id and all prospect rows using that category (transactional)."""
        if not old_name or not new_name or old_name == new_name:
            raise ValueError("Nombres invalidos")
        with self._conn() as conn:
            cat = conn.execute(
                "SELECT 1 FROM category_catalog WHERE name = ?", (old_name,)
            ).fetchone()
            if not cat:
                raise ValueError("La categoria no existe en el catalogo")
            taken = conn.execute(
                "SELECT 1 FROM category_catalog WHERE name = ?", (new_name,)
            ).fetchone()
            if taken:
                raise ValueError("Ya existe una categoria con ese id")
            conn.execute(
                "UPDATE prospects SET category = ? WHERE category = ?",
                (new_name, old_name),
            )
            conn.execute(
                "UPDATE category_catalog SET name = ? WHERE name = ?",
                (new_name, old_name),
            )
            conn.commit()

    def patch_catalog_category(
        self, name: str, label: Optional[str] = None, icon: Optional[str] = None
    ) -> bool:
        if label is None and icon is None:
            return False
        sets: list[str] = []
        params: list = []
        if label is not None:
            sets.append("label = ?")
            params.append(label)
        if icon is not None:
            sets.append("icon = ?")
            params.append(icon)
        params.append(name)
        with self._conn() as conn:
            cur = conn.execute(
                f"UPDATE category_catalog SET {', '.join(sets)} WHERE name = ?",
                params,
            )
            conn.commit()
            return cur.rowcount > 0

    def get_app_settings_raw(self) -> dict[str, str]:
        with self._conn() as conn:
            rows = conn.execute("SELECT key, value FROM app_settings").fetchall()
            return {str(r["key"]): str(r["value"]) for r in rows}

    def upsert_app_settings(self, partial: dict[str, str]) -> None:
        if not partial:
            return
        now = datetime.now().isoformat()
        with self._conn() as conn:
            for k, v in partial.items():
                conn.execute(
                    """
                    INSERT INTO app_settings (key, value, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        updated_at = excluded.updated_at
                    """,
                    (k, v, now),
                )
            conn.commit()

    def delete_category(self, category: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE prospects SET category = 'Sin categoría' WHERE category = ?",
                (category,),
            )
            conn.commit()

    def get_catalog_categories(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT name, label, icon FROM category_catalog ORDER BY label"
            ).fetchall()
            return [dict(r) for r in rows]

    def add_catalog_category(self, name: str, label: str, icon: str = "") -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO category_catalog (name, label, icon) VALUES (?, ?, ?)",
                (name, label, icon),
            )
            conn.commit()

    def delete_catalog_category(self, name: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM category_catalog WHERE name = ?", (name,))
            conn.commit()

    def get_random_prospect(self, status: str = "scraped", exclude_name: Optional[str] = None) -> Optional[Prospect]:
        with self._conn() as conn:
            query = "SELECT * FROM prospects WHERE status = ?"
            params = [status]
            if exclude_name:
                query += " AND name != ?"
                params.append(exclude_name)
            query += " ORDER BY RANDOM() LIMIT 1"
            
            row = conn.execute(query, params).fetchone()
            return Prospect.from_dict(dict(row)) if row else None

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
        if p.rating > 0:
            score += 10
        if p.reviews_count > 0:
            score += 10
        return min(score, 100)

    def get_health_snapshot(self) -> dict:
        with self._conn() as conn:

            def q(s):
                return conn.execute(s).fetchone()[0]

            return {
                "created_at": datetime.now().isoformat(),
                "total": q("SELECT COUNT(*) FROM prospects"),
                "rating_gt_0": q("SELECT COUNT(*) FROM prospects WHERE rating > 0"),
                "reviews_gt_0": q(
                    "SELECT COUNT(*) FROM prospects WHERE reviews_count > 0"
                ),
                "website_non_empty": q(
                    "SELECT COUNT(*) FROM prospects WHERE COALESCE(website,'')<>''"
                ),
                "phone_non_empty": q(
                    "SELECT COUNT(*) FROM prospects WHERE COALESCE(phone,'')<>''"
                ),
                "instagram_url_non_empty": q(
                    "SELECT COUNT(*) FROM prospects WHERE COALESCE(instagram_url,'')<>''"
                ),
                "ig_bio_non_empty": q(
                    "SELECT COUNT(*) FROM prospects WHERE COALESCE(ig_bio,'')<>''"
                ),
                "ig_followers_gt_0": q(
                    "SELECT COUNT(*) FROM prospects WHERE ig_followers > 0"
                ),
                "ig_email_non_empty": q(
                    "SELECT COUNT(*) FROM prospects WHERE COALESCE(ig_email,'')<>''"
                ),
                "ig_phone_non_empty": q(
                    "SELECT COUNT(*) FROM prospects WHERE COALESCE(ig_phone,'')<>''"
                ),
            }

    def record_health_snapshot(self) -> dict:
        snap = self.get_health_snapshot()
        cols = [
            "created_at",
            "total",
            "rating_gt_0",
            "reviews_gt_0",
            "website_non_empty",
            "phone_non_empty",
            "instagram_url_non_empty",
            "ig_bio_non_empty",
            "ig_followers_gt_0",
            "ig_email_non_empty",
            "ig_phone_non_empty",
        ]
        with self._conn() as conn:
            conn.execute(
                f"INSERT INTO health_history ({','.join (cols )}) VALUES ({','.join ('?'*len (cols ))})",
                [snap[k] for k in cols],
            )
            conn.commit()
        return snap

    def get_recent_health_history(self, limit: int = 20) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM health_history ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

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

    # --- Clientes (post-venta) ---

    def get_prospect_id_by_name(self, name: str) -> Optional[int]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id FROM prospects WHERE name = ? LIMIT 1", (name,)
            ).fetchone()
            return int(row["id"]) if row else None

    def get_prospect_by_id(self, prospect_id: int) -> Optional[Prospect]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM prospects WHERE id = ?", (prospect_id,)
            ).fetchone()
            return Prospect.from_dict(dict(row)) if row else None

    def client_exists_for_prospect(self, prospect_id: int) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM clients WHERE prospect_id = ? LIMIT 1",
                (prospect_id,),
            ).fetchone()
            return row is not None

    def list_clients(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM clients ORDER BY datetime(updated_at) DESC"
            ).fetchall()
            return [dict(r) for r in rows]

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
            row = conn.execute(
                "SELECT * FROM clients WHERE id = ?", (client_id,)
            ).fetchone()
            return dict(row) if row else None

    def insert_client(self, data: dict) -> int:
        now = datetime.now().isoformat()
        cols = [
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
        ]
        row = {c: data[c] for c in cols if c in data}
        row.setdefault("display_name", "")
        row.setdefault("stage", "quote_sent")
        row["created_at"] = now
        row["updated_at"] = now
        for k in ("contract_required", "contract_skipped"):
            if k in row and row[k] is not None:
                row[k] = 1 if row[k] else 0
        keys = list(row.keys())
        placeholders = ",".join("?" * len(keys))
        with self._conn() as conn:
            cur = conn.execute(
                f"INSERT INTO clients ({','.join(keys)}) VALUES ({placeholders})",
                [row[k] for k in keys],
            )
            conn.commit()
            return int(cur.lastrowid)

    def update_client(self, client_id: int, data: dict) -> None:
        if not data:
            return
        allowed = {
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
        }
        updates = {k: v for k, v in data.items() if k in allowed}
        if not updates:
            return
        for k in ("contract_required", "contract_skipped"):
            if k in updates and updates[k] is not None:
                updates[k] = 1 if updates[k] else 0
        updates["updated_at"] = datetime.now().isoformat()
        sets = ", ".join(f"{k} = ?" for k in updates)
        params = list(updates.values()) + [client_id]
        with self._conn() as conn:
            conn.execute(f"UPDATE clients SET {sets} WHERE id = ?", params)
            conn.commit()

    def delete_client(self, client_id: int) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))
            conn.commit()

    def touch_client_updated_at(self, client_id: int) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE clients SET updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(), client_id),
            )
            conn.commit()

    def get_client_meeting(self, meeting_id: int) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM client_meetings WHERE id = ?", (meeting_id,)
            ).fetchone()
            return dict(row) if row else None

    def list_client_meetings(self, client_id: int) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM client_meetings WHERE client_id = ? ORDER BY datetime(scheduled_at)",
                (client_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def insert_client_meeting(self, client_id: int, data: dict) -> int:
        title = data.get("title", "")
        scheduled_at = data.get("scheduled_at") or datetime.now().isoformat()
        duration_min = int(data.get("duration_min", 60))
        notes = data.get("notes", "")
        status = data.get("status", "scheduled")
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO client_meetings (client_id, title, scheduled_at, duration_min, notes, status)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (client_id, title, scheduled_at, duration_min, notes, status),
            )
            conn.commit()
            self.touch_client_updated_at(client_id)
            return int(cur.lastrowid)

    def update_client_meeting(self, meeting_id: int, data: dict) -> None:
        allowed = {"title", "scheduled_at", "duration_min", "notes", "status"}
        updates = {k: v for k, v in data.items() if k in allowed}
        if not updates:
            return
        if "duration_min" in updates:
            updates["duration_min"] = int(updates["duration_min"])
        cid_row = None
        with self._conn() as conn:
            row = conn.execute(
                "SELECT client_id FROM client_meetings WHERE id = ?", (meeting_id,)
            ).fetchone()
            if not row:
                return
            cid_row = int(row["client_id"])
            sets = ", ".join(f"{k} = ?" for k in updates)
            conn.execute(
                f"UPDATE client_meetings SET {sets} WHERE id = ?",
                list(updates.values()) + [meeting_id],
            )
            conn.commit()
        if cid_row is not None:
            self.touch_client_updated_at(cid_row)

    def delete_client_meeting(self, meeting_id: int) -> None:
        cid_row = None
        with self._conn() as conn:
            row = conn.execute(
                "SELECT client_id FROM client_meetings WHERE id = ?", (meeting_id,)
            ).fetchone()
            if row:
                cid_row = int(row["client_id"])
            conn.execute("DELETE FROM client_meetings WHERE id = ?", (meeting_id,))
            conn.commit()
        if cid_row is not None:
            self.touch_client_updated_at(cid_row)

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
