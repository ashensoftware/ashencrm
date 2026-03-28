"""
Scrapea prospectos en Medellín hasta alcanzar un objetivo en la base de datos.

Estrategia:
- En vez de repetir siempre `category="*"`, recorre categorías del catálogo local para maximizar variedad.
- NO hace chequeo de Instagram en esta fase para llegar rápido a >= target leads.
"""

import argparse
import asyncio
import random
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from backend.config.settings import settings
from backend.database.db import Database
from backend.scraper.google_maps import GoogleMapsScraper


def get_total_prospects(db: Database) -> int:
    stats = db.count_by_status()
    return sum(stats.values())


async def main():
    parser = argparse.ArgumentParser(
        description="Scrape Medellín por categorías hasta llegar a un target."
    )
    parser.add_argument("--city", default="Medellín", help="Ciudad a buscar")
    parser.add_argument(
        "--target", type=int, default=1000, help="Cantidad mínima de leads en DB"
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=100,
        help="Cuántos resultados intentar por categoría",
    )
    parser.add_argument(
        "--shuffle", action="store_true", help="Barajar orden de categorías cada ronda"
    )
    parser.add_argument(
        "--max-rounds", type=int, default=3, help="Cuántas rondas de categorías máximo"
    )
    args = parser.parse_args()

    db = Database()
    scraper = GoogleMapsScraper(headless=settings.scraper.headless)

    try:
        total = get_total_prospects(db)
        print(f"Estado inicial: total prospectos = {total } (target={args .target })")

        catalog = db.get_catalog_categories()
        categories = [c["name"] for c in catalog if c.get("name")]

        for round_idx in range(1, args.max_rounds + 1):
            if total >= args.target:
                break

            order = categories[:]
            if args.shuffle:
                random.shuffle(order)

            print(f"\n--- Ronda {round_idx }: categorías={len (order )} ---")

            for cat in order:
                if total >= args.target:
                    break

                remaining = args.target - total
                current_limit = min(args.batch, remaining)

                print(
                    f"Scrape cat={cat } limit={current_limit } (total={total }/{args .target })"
                )
                results = await scraper.search(
                    category=cat, city=args.city, limit=current_limit
                )

                ins_count, dup_count = db.insert_many(results)
                total = get_total_prospects(db)
                print(
                    f"Cat {cat } terminado: results={len (results )} insertados={ins_count } duplicados={dup_count }"
                )
                print(f"Progreso: total prospectos = {total }/{args .target }")

                if not results:

                    print(f"Cat {cat } no devolvió resultados. Continuando...")

        print("\nProceso finalizado.")
        print(f"Total prospectos: {total }")
        print(db.stats())

    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
