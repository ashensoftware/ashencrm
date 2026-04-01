"""
Script para re-scrapear leads en bloque sin perder estados manuales existentes.
Ejecutar con el venv activo:
  python rescrape_all.py
  python rescrape_all.py --workers 3

Varias categorías se scrapean en paralelo (cada una con su propio navegador Playwright).
Las inserciones en SQLite van serializadas para evitar "database is locked".

Si quieres reiniciar todo desde cero:
  python rescrape_all.py --clear-existing
"""

from __future__ import annotations

import argparse
import asyncio
import platform
import sqlite3
import sys
import time
from pathlib import Path

# Windows event loop policy
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

sys.path.insert(0, str(Path(__file__).parent))

from backend.config.settings import settings
from backend.infrastructure.persistence.prospect_repository import ProspectRepository
from backend.scraper.google_maps import GoogleMapsScraper

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


def clear_all_leads() -> None:
    """Borra TODOS los leads de la base de datos."""
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("DELETE FROM prospects")
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    print(f"[LIMPIEZA] Eliminados {deleted} leads de la base de datos.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Re-scrape masivo de leads preservando estados existentes por defecto."
    )
    parser.add_argument(
        "--clear-existing",
        action="store_true",
        help="Borra todos los leads antes de scrapear (pierde estados manuales).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=2,
        metavar="N",
        help="Categorías en paralelo (cada una = un Chromium). Por defecto 2; sube con RAM disponible.",
    )
    return parser.parse_args()


async def scrape_plan_item(
    category: str,
    city: str,
    limit: int,
    semaphore: asyncio.Semaphore,
    db_lock: asyncio.Lock,
    db: ProspectRepository,
) -> dict:
    async with semaphore:
        t0 = time.perf_counter()
        scraper = GoogleMapsScraper(headless=True)
        try:

            def log(msg: str) -> None:
                print(f"  [{category}] {msg}")

            print(f"[INICIO] {category} (objetivo: {limit} leads NUEVOS; duplicados en BD se saltan sin scrapear)")
            results = await scraper.search(
                category,
                city,
                limit=limit,
                log_callback=log,
                skip_if_in_db=db.exists_by_name_and_address,
            )
            for p in results:
                p.category = category
                p.notes = ""

            async with db_lock:
                ins, dup = await asyncio.to_thread(db.insert_many, results)

            elapsed = time.perf_counter() - t0
            phones = sum(1 for p in results if p.phone)
            websites = sum(1 for p in results if p.website)
            instagrams = sum(1 for p in results if p.instagram_url)
            photos = sum(1 for p in results if p.screenshot_path)
            n = len(results)

            print(
                f"[OK] {category} en {elapsed:.1f}s → {n} nuevos scrapeados, "
                f"{ins} insertados, {dup} fallos al insertar (carrera/clave)"
            )
            print(
                f"  [CALIDAD] {category}  Tel: {phones}/{n} | Web: {websites}/{n} | IG: {instagrams}/{n} | Foto: {photos}/{n}"
            )

            return {
                "category": category,
                "ok": True,
                "inserted": ins,
                "duplicates": dup,
                "found": n,
                "elapsed": elapsed,
            }
        except Exception as e:
            print(f"[ERROR] {category}: {e}")
            return {
                "category": category,
                "ok": False,
                "inserted": 0,
                "duplicates": 0,
                "found": 0,
                "elapsed": time.perf_counter() - t0,
                "error": str(e),
            }
        finally:
            await scraper.close()


async def run_scrape(clear_existing: bool = False, workers: int = 2) -> None:
    if clear_existing:
        clear_all_leads()
    else:
        print(
            "[MODO SEGURO] No se borrarán leads existentes; se preservan estados manuales."
        )

    workers = max(1, min(workers, len(SCRAPE_PLAN)))
    print(f"[PARALELO] Hasta {workers} categorías a la vez (una instancia de navegador por categoría).")

    db = ProspectRepository(db_path=DB_PATH)
    semaphore = asyncio.Semaphore(workers)
    db_lock = asyncio.Lock()

    t_wall = time.perf_counter()
    tasks = [
        scrape_plan_item(cat, city, lim, semaphore, db_lock, db)
        for cat, city, lim in SCRAPE_PLAN
    ]
    outcomes = await asyncio.gather(*tasks)

    total_inserted = sum(o["inserted"] for o in outcomes)
    total_duplicates = sum(o["duplicates"] for o in outcomes)
    failed = [o["category"] for o in outcomes if not o.get("ok")]

    wall = time.perf_counter() - t_wall
    print(f"\n{'='*60}")
    print(f"[TOTAL] {total_inserted} leads insertados, {total_duplicates} duplicados")
    print(f"[TIEMPO] Pared: {wall:.1f}s (con {workers} workers)")
    if failed:
        print(f"[AVISO] Categorías con error: {', '.join(failed)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(
        run_scrape(clear_existing=args.clear_existing, workers=args.workers)
    )
