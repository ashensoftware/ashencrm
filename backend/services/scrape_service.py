"""Scrape orchestration service for interactive dashboard scraping."""

import asyncio
import platform
import traceback

import h3

from backend.core.config import H3_RESOLUTION
from backend.core.logger import add_scrape_log
from backend.scraper.google_maps import GoogleMapsScraper
from backend.services.app_settings_service import scrape_runtime_options

KEYWORDS = {
    "cafe": ["cafete", "coffee", "panader", "reposter"],
    "restaurante": ["restauran", "comida", "gastronom", "parrilla", "piz"],
    "gimnasio": ["gym", "entrenamiento", "fitness", "crossfit"],
    "estetica": ["peluquer", "barber", "spa", "estetic", "belleza"],
    "tienda-ropa": ["boutique", "ropa", "moda", "almacen"],
    "veterinaria": ["vete", "animal", "pet shop"],
    "odontologia": ["dentista", "odontol", "clinica dental"],
    "taller": ["mecanic", "taller", "automotriz"],
}


class ScrapeService:
    def __init__(self, db):
        self.db = db

    def map_native_to_catalog(self, native_cat: str, catalog: list) -> str:
        if not native_cat:
            return "otros"
        native_clean = native_cat.lower().strip()
        for cat in catalog:
            label_clean = cat["label"].split(" ", 1)[-1].lower()
            if (
                label_clean in native_clean
                or native_clean in label_clean
                or cat["name"] in native_clean
            ):
                return cat["name"]
        for cat_id, keys in KEYWORDS.items():
            if any(k in native_clean for k in keys):
                return cat_id
        return "otros"

    async def run_scrape_task(
        self,
        category: str,
        city: str,
        limit: int,
        lat: float | None = None,
        lon: float | None = None,
    ) -> None:
        add_scrape_log(f"Iniciando busqueda de '{category }' en {city }...")
        opts = scrape_runtime_options(self.db)
        scraper = GoogleMapsScraper(headless=opts["scraper_headless"])
        try:
            results = await scraper.search(
                category,
                city,
                limit=limit,
                lat=lat,
                lon=lon,
                log_callback=add_scrape_log,
            )
            in_zone_count = 0
            if lat and lon:
                try:
                    origin_h3 = h3.latlng_to_cell(lat, lon, H3_RESOLUTION)
                    allowed_h3 = h3.grid_disk(origin_h3, 2)
                except AttributeError:
                    origin_h3 = h3.geo_to_h3(lat, lon, H3_RESOLUTION)
                    allowed_h3 = h3.k_ring(origin_h3, 2)
                for p in results:
                    if p.latitude and p.longitude:
                        try:
                            p_h3 = h3.latlng_to_cell(
                                p.latitude, p.longitude, H3_RESOLUTION
                            )
                        except AttributeError:
                            p_h3 = h3.geo_to_h3(p.latitude, p.longitude, H3_RESOLUTION)
                        if p_h3 in allowed_h3:
                            in_zone_count += 1
                add_scrape_log(
                    f"Info: {in_zone_count } de {len (results )} leads en zona objetivo."
                )
            if category == "*":
                catalog = self.db.get_catalog_categories()
                add_scrape_log("Clasificando negocios automaticamente...")
                for p in results:
                    p.category = self.map_native_to_catalog(p.notes, catalog)
                    p.notes = ""
            ins_count, dup_count = self.db.insert_many(results)
            add_scrape_log(
                f"FINALIZADO: {len (results )} leads ({ins_count } nuevos, {dup_count } repetidos)."
            )
        except Exception as e:
            add_scrape_log(f"ERROR: {str (e )}")
            add_scrape_log(f"Traceback:\n{traceback .format_exc ()}")
        finally:
            await scraper.close()

    def threaded_scrape_launcher(
        self,
        category: str,
        city: str,
        limit: int,
        lat: float | None = None,
        lon: float | None = None,
    ) -> None:
        add_scrape_log(f"Hilo de scraping iniciado para {category }...")
        if platform.system() == "Windows":
            if not isinstance(
                asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy
            ):
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        try:
            asyncio.run(self.run_scrape_task(category, city, limit, lat, lon))
        except Exception as e:
            add_scrape_log(f"Error fatal en hilo: {str (e )}")
