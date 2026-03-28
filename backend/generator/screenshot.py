"""
Módulo para capturar pantallas de los sitios generados.
"""

import asyncio
import os
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright

SCREENSHOTS_DIR = Path("data/screenshots")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


class ScreenshotTaker:
    def __init__(self, viewport_width: int = 1280, viewport_height: int = 720):
        self.width = viewport_width
        self.height = viewport_height

    async def capture(self, url: str, filename: str) -> Optional[str]:
        """
        Navega a la URL y guarda una captura de pantalla.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(
                viewport={"width": self.width, "height": self.height}
            )

            try:
                print(f"[Screenshot] Capturando {url }...")
                await page.goto(url, wait_until="networkidle", timeout=60000)

                await asyncio.sleep(2)

                output_path = SCREENSHOTS_DIR / f"{filename }.png"
                await page.screenshot(path=str(output_path), full_page=False)

                await browser.close()
                print(f"[Screenshot] Captura guardada: {output_path }")
                return str(output_path.absolute())
            except Exception as e:
                print(f"[Screenshot] Error capturando pantalla: {e }")
                await browser.close()
                return None


if __name__ == "__main__":

    async def test():
        st = ScreenshotTaker()
        await st.capture("https://google.com", "test_google")

    asyncio.run(test())
