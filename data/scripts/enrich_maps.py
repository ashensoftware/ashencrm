"""
Enriquece prospectos usando la página de detalle de Google Maps.

Objetivo:
- Llenar `website` y `reviews_count` (y opcionalmente `rating`) para leads
  que aún no tienen esos campos.

Importante:
- Esto es más lento porque abre la ficha de Maps por prospecto.
"""

import argparse
import asyncio
import random
import re
import sys
from pathlib import Path
from typing import Optional

sys.path.append(str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright

from backend.config.settings import settings
from backend.database.db import Database
from backend.scraper.models import Prospect


def normalize_external_url(url: str) -> str:
    return url.strip().rstrip(")")


async def pick_website_from_page(page) -> Optional[str]:

    links = await page.query_selector_all('a[href^="http"]')
    for link in links:
        try:
            href = await link.get_attribute("href")
        except Exception:
            href = None
        if not href:
            continue

        u_l = href.lower()
        if "google.com" in u_l:
            continue
        if "instagram.com" in u_l:
            continue
        if "facebook.com" in u_l:
            continue
        if "whatsapp.com" in u_l:
            continue
        if "youtu" in u_l:
            continue

        if re.search(r"\\.[a-z]{2,}(/|$)", u_l):
            return normalize_external_url(href)

    return None


def parse_rating_and_reviews(html: str) -> tuple[float, int]:
    rating = 0.0
    reviews_count = 0

    m_rating = re.search(
        r"([0-5](?:[\\.,][0-9])?)\\s*(?:stars|estrellas)",
        html,
        flags=re.IGNORECASE,
    )
    if m_rating:
        try:
            rating = float(m_rating.group(1).replace(",", "."))
        except ValueError:
            rating = 0.0

    m_reviews = re.search(
        r"([0-9][0-9\\.,\\s]*)\\s*(?:rese\\u00f1as|rese\\u00f1a|rese\\u00f1as[s]?|reviews?|review|opiniones|opinion(?:es)?)",
        html,
        flags=re.IGNORECASE,
    )
    if m_reviews:
        raw = m_reviews.group(1)
        reviews_count = int(re.sub(r"\\D", "", raw) or 0)

    return rating, reviews_count


async def enrich_one(page, db: Database, p: Prospect) -> None:
    if not p.maps_url:
        return

    details_url = p.maps_url
    if not details_url.startswith("http"):
        details_url = f"https://www.google.com{details_url }"

    await page.goto(details_url, wait_until="domcontentloaded", timeout=60000)

    await asyncio.sleep(random.uniform(4, 7))

    try:
        consent_btn = await page.query_selector(
            'button[aria-label="Aceptar todo"], button[aria-label="Aceptar"], button:has-text("Aceptar todo"), button:has-text("Aceptar")'
        )
        if consent_btn:
            await consent_btn.click()
            await asyncio.sleep(random.uniform(2, 3))
    except Exception:
        pass

    for _ in range(3):
        await page.mouse.wheel(0, 1800)
        await asyncio.sleep(random.uniform(1.5, 2.5))

    html = await page.content()
    rating, reviews_count = parse_rating_and_reviews(html)
    website = await pick_website_from_page(page)

    patch = {}
    if website and not p.website:
        patch["website"] = website
    if reviews_count and (not p.reviews_count or p.reviews_count == 0):
        patch["reviews_count"] = reviews_count
    if rating and (not p.rating or p.rating == 0):
        patch["rating"] = rating

    if patch:
        db.patch_prospect(p.name, p.address, patch)


async def main():
    parser = argparse.ArgumentParser(
        description="Enriquecer website/reviews_count desde la ficha Maps"
    )
    parser.add_argument(
        "--limit", type=int, default=50, help="Cantidad máxima de prospectos a procesar"
    )
    parser.add_argument(
        "--needs-website", action="store_true", help="Solo donde website vacío"
    )
    parser.add_argument(
        "--needs-reviews", action="store_true", help="Solo donde reviews_count=0"
    )
    parser.add_argument(
        "--headless", action="store_true", default=True, help="Headless (por defecto)"
    )
    parser.add_argument(
        "--no-headless", dest="headless", action="store_false", help="Browser visible"
    )
    args = parser.parse_args()

    db = Database()

    if (not args.needs_website) and (not args.needs_reviews):
        needs_website = True
        needs_reviews = True
    else:
        needs_website = bool(args.needs_website)
        needs_reviews = bool(args.needs_reviews)

    where_clauses = []
    if needs_website:
        where_clauses.append("(website IS NULL OR website='')")
    if needs_reviews:
        where_clauses.append("(reviews_count=0 OR reviews_count IS NULL)")

    where_sql = " OR ".join(where_clauses) if where_clauses else "1=0"

    with db._get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM prospects
            WHERE ({where_sql }) AND maps_url IS NOT NULL AND maps_url<>''
            ORDER BY scraped_at DESC
            LIMIT ?
            """,
            (args.limit,),
        ).fetchall()

    prospects = [Prospect.from_dict(dict(r)) for r in rows]
    print(
        f"Procesando {len (prospects )} prospectos (website vacío={needs_website }, reviews vacías={needs_reviews })..."
    )

    if not prospects:
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=args.headless)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        if hasattr(page, "set_default_timeout"):
            page.set_default_timeout(60000)

        processed = 0
        for pr in prospects:
            processed += 1
            print(f"[{processed }/{len (prospects )}] {pr .name }")
            try:
                await enrich_one(page, db, pr)
            except Exception as e:
                print(f"  Error: {e }")
            finally:
                await asyncio.sleep(random.uniform(1, 2))

        await browser.close()

    print("Done.")
    print(db.stats())


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    asyncio.run(main())
