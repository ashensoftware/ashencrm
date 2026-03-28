"""
Script para borrar todos los leads existentes y re-scrapear 200+ leads frescos.
Ejecutar con el venv activo: python rescrape_all.py
"""

import asyncio
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

DB_PATH = Path("data/prospects.db")

# Categorías y cantidad de leads a scrapear por cada una
SCRAPE_PLAN = [
    ("cafe", "Medellín", 30),
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


async def run_scrape():
    clear_all_leads()

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
            print(f"[CALIDAD]  Teléfonos: {phones}/{len(results)} | Webs: {websites}/{len(results)} | Instagram: {instagrams}/{len(results)}")

        except Exception as e:
            print(f"[ERROR] {category}: {e}")
        finally:
            await scraper.close()

    print(f"\n{'='*60}")
    print(f"[TOTAL] {total_inserted} leads insertados, {total_duplicates} duplicados")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(run_scrape())
