"""
Chequeo rápido de calidad de datos de los prospectos (Postgres, rol crm_ingest).
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from backend.infrastructure.persistence.ingest import ingest_repository

METRICS = {
    "total": "SELECT COUNT(*) AS n FROM prospects",
    "rating_gt_0": "SELECT COUNT(*) AS n FROM prospects WHERE rating > 0",
    "reviews_gt_0": "SELECT COUNT(*) AS n FROM prospects WHERE reviews_count > 0",
    "website_non_empty": "SELECT COUNT(*) AS n FROM prospects WHERE website IS NOT NULL AND website <> ''",
    "phone_non_empty": "SELECT COUNT(*) AS n FROM prospects WHERE phone IS NOT NULL AND phone <> ''",
    "instagram_url_non_empty": "SELECT COUNT(*) AS n FROM prospects WHERE instagram_url IS NOT NULL AND instagram_url <> ''",
    "ig_bio_non_empty": "SELECT COUNT(*) AS n FROM prospects WHERE ig_bio IS NOT NULL AND ig_bio <> ''",
    "ig_followers_gt_0": "SELECT COUNT(*) AS n FROM prospects WHERE ig_followers > 0",
    "ig_email_non_empty": "SELECT COUNT(*) AS n FROM prospects WHERE ig_email IS NOT NULL AND ig_email <> ''",
    "ig_phone_non_empty": "SELECT COUNT(*) AS n FROM prospects WHERE ig_phone IS NOT NULL AND ig_phone <> ''",
}


def main():
    db = ingest_repository()
    with db._conn() as conn:
        print("=== DATA HEALTH CHECK ===")
        for key, query in METRICS.items():
            print(f"{key}: {conn.execute(query).fetchone()['n']}")

        print("\n=== STATUS BREAKDOWN ===")
        rows = conn.execute(
            "SELECT status, COUNT(*) AS c FROM prospects GROUP BY status ORDER BY c DESC"
        ).fetchall()
        for row in rows:
            print(f"{row['status']}: {row['c']}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
