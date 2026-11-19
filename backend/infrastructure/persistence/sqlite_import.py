"""Plan de importación SQLite → Postgres. No escribe ni imprime filas."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def sqlite_import_plan(source: Path) -> dict:
    path = Path(source)
    with sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True) as conn:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        ]
        counts = {}
        for name in tables:
            if not name.replace("_", "").isalnum():
                continue
            counts[name] = int(conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0])
    return {"mode": "dry-run", "writes": 0, "tables": counts}
