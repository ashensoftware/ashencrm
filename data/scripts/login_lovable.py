"""Abre el navegador de la cuenta 1 para iniciar sesión manualmente en Lovable."""

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.append(str(Path(__file__).parent.parent))
from backend.config.settings import settings


async def main():
    session_path = str(Path(__file__).parent.parent / "config/sessions/account_1")
    print(f"Abriendo sesión persistente en: {session_path }")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=session_path,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = await context.new_page()
        await page.goto("https://lovable.dev")
        print("Navegador de automatización abierto.")
        print(
            "=> POR FAVOR inicia sesión en Lovable.dev (puedes usar Google u otro método)."
        )
        print(
            "=> Cuando hayas terminado e iniciado sesión, puedes cerrar la ventana del navegador."
        )

        while len(context.pages) > 0:
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
