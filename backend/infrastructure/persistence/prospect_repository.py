"""SQLite persistence for prospects, categories and health snapshots."""

import csv
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from backend.config.settings import settings
from backend.domain.prospect import Prospect, ProspectStatus

DEFAULT_CATEGORIES = [
    ("cafe", "Cafe"),
    ("restaurante", "Restaurante"),
    ("gimnasio", "Gimnasio"),
    ("barberia", "Barberia"),
    ("odontologia", "Odontologia"),
    ("veterinaria", "Veterinaria"),
    ("ferreteria", "Ferreteria"),
    ("panaderia", "Panaderia"),
    ("estetica", "Estetica"),
    ("taller", "Taller"),
    ("petshop", "Pet Shop"),
    ("coworking", "Coworking"),
    ("reposteria", "Reposteria"),
    ("spa", "Spa"),
    ("tienda", "Tienda de Ropa"),
    ("otros", "Otros Negocios"),
]


class ProspectRepository:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
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
            """)
            cur = conn.execute("SELECT COUNT(*) FROM category_catalog")
            if cur.fetchone()[0] == 0:
                conn.executemany(
                    "INSERT INTO category_catalog (name, label) VALUES (?, ?)",
                    DEFAULT_CATEGORIES,
                )
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
            conn.commit()

    def insert_prospect(self, prospect: Prospect) -> bool:
        try:
            with self._conn() as conn:
                data = prospect.to_dict()
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
