"""
Chequeo rápido de calidad de datos para la base de prospectos.
"""

import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from backend.config.settings import settings


def main():
    conn = sqlite3.connect(str(settings.db_path))
    cur = conn.cursor()

    metrics = {
        "total": "SELECT COUNT(*) FROM prospects",
        "rating_gt_0": "SELECT COUNT(*) FROM prospects WHERE rating > 0",
        "reviews_gt_0": "SELECT COUNT(*) FROM prospects WHERE reviews_count > 0",
        "website_non_empty": "SELECT COUNT(*) FROM prospects WHERE website IS NOT NULL AND website <> ''",
        "phone_non_empty": "SELECT COUNT(*) FROM prospects WHERE phone IS NOT NULL AND phone <> ''",
        "instagram_url_non_empty": "SELECT COUNT(*) FROM prospects WHERE instagram_url IS NOT NULL AND instagram_url <> ''",
        "ig_bio_non_empty": "SELECT COUNT(*) FROM prospects WHERE ig_bio IS NOT NULL AND ig_bio <> ''",
        "ig_followers_gt_0": "SELECT COUNT(*) FROM prospects WHERE ig_followers > 0",
        "ig_email_non_empty": "SELECT COUNT(*) FROM prospects WHERE ig_email IS NOT NULL AND ig_email <> ''",
        "ig_phone_non_empty": "SELECT COUNT(*) FROM prospects WHERE ig_phone IS NOT NULL AND ig_phone <> ''",
    }

    print("=== DATA HEALTH CHECK ===")
    for key, q in metrics.items():
        value = cur.execute(q).fetchone()[0]
        print(f"{key }: {value }")

    print("\n=== STATUS BREAKDOWN ===")
    rows = cur.execute(
        "SELECT status, COUNT(*) AS c FROM prospects GROUP BY status ORDER BY c DESC"
    ).fetchall()
    for status, c in rows:
        print(f"{status }: {c }")


if __name__ == "__main__":
    main()
