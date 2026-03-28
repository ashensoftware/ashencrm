"""Runs Google Maps and optional Instagram enrichment."""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from backend.config.settings import settings
from backend.database.db import Database
from backend.scraper.google_maps import GoogleMapsScraper
from backend.scraper.instagram import InstagramChecker

try:
    from rich.console import Console
    from rich.table import Table

    console = Console()
except ImportError:

    class Console:
        def print(self, msg, *args, **kwargs):
            print(msg)

    console = Console()
    Table = None


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", default=settings.scraper.city)
    parser.add_argument("--category", default="gym")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--no-ig", action="store_true")
    args = parser.parse_args()

    db = Database()
    scraper = GoogleMapsScraper(headless=settings.scraper.headless)
    ig_checker = InstagramChecker(headless=settings.scraper.headless)

    console.print(
        f"[bold blue]Buscando {args .category } en {args .city }...[/bold blue]"
    )
    try:
        prospects = await scraper.search(
            args.category,
            args.city,
            limit=args.limit,
            log_callback=lambda msg: console.print(f"[dim]{msg }[/dim]"),
        )

        if not prospects:
            console.print("[yellow]Sin resultados válidos encontrados.[/yellow]")
            return

        ins, dup = db.insert_many(prospects)

        if Table:
            table = Table(title="Resultados del Scraping")
            table.add_column("Nombre", style="cyan", no_wrap=True)
            table.add_column("Teléfono", style="green")
            table.add_column("Sitio Web", style="magenta")

            for p in prospects[:10]:
                table.add_row(p.name[:30], p.phone or "N/A", p.website or "N/A")
            console.print(table)

        console.print(
            f"[bold green]DB:[/bold green] {ins } nuevos guardados, {dup } descartados/duplicados."
        )

        if not args.no_ig and ins > 0:
            for p in prospects[: min(5, len(prospects))]:
                await ig_checker.check_profile(p)
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
            print("IG: enriquecimiento aplicado a los primeros 5.")
    finally:
        await scraper.close()
        await ig_checker.close()


if __name__ == "__main__":
    asyncio.run(main())
