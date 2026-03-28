"""Enriches prospects with Instagram data (batch)."""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from backend.database.db import Database
from backend.domain.prospect import Prospect
from backend.scraper.instagram import InstagramChecker

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--city", default=None)
    parser.add_argument("--status", default="scraped")
    parser.add_argument("--needs-enrichment", action="store_true")
    args = parser.parse_args()

    db = Database()
    ig = InstagramChecker(headless=True)

    if args.needs_enrichment:
        with db._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM prospects
                WHERE status IN ('scraped', 'ready')
                AND (
                    (instagram_url IS NULL OR instagram_url = '')
                    OR (ig_bio IS NULL OR ig_bio = '')
                    OR (ig_email IS NULL OR ig_email = '')
                    OR (ig_phone IS NULL OR ig_phone = '')
                )
                ORDER BY RANDOM()
                LIMIT ?
            """,
                (args.limit,),
            ).fetchall()
        candidates = [Prospect.from_dict(dict(r)) for r in rows]
    else:
        candidates = db.get_prospects(
            status=args.status, city=args.city, limit=args.limit
        )

    print(f"Procesando {len (candidates )} prospectos.")
    try:
        for p in candidates:
            await ig.check_profile(p)
            db.patch_prospect(
                p.name,
                p.address,
                {
                    "instagram_url": p.instagram_url,
                    "instagram_handle": p.instagram_handle,
                    "ig_bio": p.ig_bio,
                    "ig_followers": p.ig_followers,
                    "ig_email": p.ig_email,
                    "ig_phone": p.ig_phone,
                    "ig_website": p.ig_website,
                },
            )
    finally:
        await ig.close()


if __name__ == "__main__":
    asyncio.run(main())
