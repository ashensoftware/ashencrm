"""
Script para re-scrapear leads en bloque sin perder estados manuales existentes.
Ejecutar con el venv activo:
  python rescrape_all.py
Si quieres reiniciar todo desde cero:
  python rescrape_all.py --clear-existing
"""

import asyncio
import argparse
import platform
import sqlite3
from pathlib import Path

# Windows event loop policy
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import sys
sys.path.insert(0, str(Path(__file__).parent))

from backend.scraper.google_maps import GoogleMapsScraper
from backend.infrastructure.persistence.prospect_repository import ProspectRepository
from backend.domain.prospect import Prospect
from backend.config.settings import settings

DB_PATH = settings.db_path

# Categorías y cantidad de leads a scrapear por cada una
SCRAPE_PLAN = [
    ("cafe", "Medellín", 10),
    ("restaurante", "Medellín", 30),
    ("gimnasio", "Medellín", 25),
    ("barberia", "Medellín", 25),
    ("odontologia", "Medellín", 20),
    ("veterinaria", "Medellín", 20),
    ("panaderia", "Medellín", 20),
    ("estetica", "Medellín", 15),
    ("taller", "Medellín", 15),
    ("coworking", "Medellín", 10),
]


def clear_all_leads():
    """Borra TODOS los leads de la base de datos."""
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("DELETE FROM prospects")
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    print(f"[LIMPIEZA] Eliminados {deleted} leads de la base de datos.")


def map_native_to_catalog(native_cat: str, catalog_name: str) -> str:
    """Mapea la categoría nativa de Google Maps al nombre del catálogo."""
    if not native_cat:
        return catalog_name
    return catalog_name


def parse_args():
    parser = argparse.ArgumentParser(
        description="Re-scrape masivo de leads preservando estados existentes por defecto."
    )
    parser.add_argument(
        "--clear-existing",
        action="store_true",
        help="Borra todos los leads antes de scrapear (pierde estados manuales).",
    )
    return parser.parse_args()


async def run_scrape(clear_existing: bool = False):
    if clear_existing:
        clear_all_leads()
    else:
        print(
            "[MODO SEGURO] No se borrarán leads existentes; se preservan estados manuales."
        )

    db = ProspectRepository(db_path=DB_PATH)
    total_inserted = 0
    total_duplicates = 0

    for category, city, limit in SCRAPE_PLAN:
        print(f"\n{'='*60}")
        print(f"[SCRAPING] Categoría: {category} | Ciudad: {city} | Limit: {limit}")
        print(f"{'='*60}")

        scraper = GoogleMapsScraper(headless=True)
        try:
            results = await scraper.search(
                category,
                city,
                limit=limit,
                log_callback=lambda msg: print(f"  >> {msg}"),
            )

            # Asignar categoría correcta
            for p in results:
                p.category = category
                p.notes = ""

            ins, dup = db.insert_many(results)
            total_inserted += ins
            total_duplicates += dup

            print(f"[RESULTADO] {len(results)} encontrados → {ins} nuevos, {dup} duplicados")

            # Calidad de datos
            phones = sum(1 for p in results if p.phone)
            websites = sum(1 for p in results if p.website)
            instagrams = sum(1 for p in results if p.instagram_url)
            photos = sum(1 for p in results if p.screenshot_path)
            print(f"[CALIDAD]  Tel: {phones}/{len(results)} | Web: {websites}/{len(results)} | IG: {instagrams}/{len(results)} | Foto: {photos}/{len(results)}")

        except Exception as e:
            print(f"[ERROR] {category}: {e}")
        finally:
            await scraper.close()

    print(f"\n{'='*60}")
    print(f"[TOTAL] {total_inserted} leads insertados, {total_duplicates} duplicados")
    print(f"{'='*60}")


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run_scrape(clear_existing=args.clear_existing))
