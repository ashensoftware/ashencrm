"""Lovable.dev automation via Playwright for demo site generation."""

import asyncio
import re
import time
from typing import Optional

from playwright.async_api import async_playwright

from backend.config.settings import settings


class LovableAutomation:
    def __init__(self, account_info: dict):
        self.account_id = account_info["id"]
        self.session_path = account_info["path"]
        self.playwright = None
        self.context = None
        self.page = None

    async def start(self, headless: bool = True):
        self.playwright = await async_playwright().start()
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.session_path,
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        self.page = await self.context.new_page()
        return self.page

    async def _find_preview_url(self) -> Optional[str]:
        """Intenta obtener la URL del preview (.lovable.app o proyecto en lovable.dev)."""
        if not self.page:
            return None
        try:
            current = self.page.url or ""
            if "lovable.app" in current:
                return current.split("?", 1)[0]
            if "lovable.dev" in current and "/projects/" in current:
                return current.split("?", 1)[0]

            for sel in (
                'a[href*="lovable.app"]',
                'a[href*="lovable.dev"]',
                '[href*="lovable.app"]',
            ):
                links = await self.page.query_selector_all(sel)
                for link in links:
                    href = await link.get_attribute("href")
                    if href and "lovable.app" in href:
                        return href.split("?", 1)[0]

            body = await self.page.content()
            m = re.search(
                r"https?://[a-zA-Z0-9_.-]+\.lovable\.app[^\s\"'<>]*",
                body,
            )
            if m:
                return m.group(0).split("?", 1)[0]
        except Exception:
            pass
        return None

    async def create_site(self, prompt: str) -> Optional[str]:
        """
        Navega a Lovable y crea un nuevo sitio basado en el prompt.
        Retorna la URL del sitio generado si se detecta; si no, un placeholder estable.
        """
        timeout_sec = max(30, settings.generator.lovable_timeout)

        try:
            await self.page.goto(
                "https://lovable.dev/projects",
                wait_until="domcontentloaded",
                timeout=90000,
            )

            new_btn = await self.page.query_selector("button:has-text('New project')")
            if not new_btn:
                new_btn = await self.page.query_selector("text=New project")
            if not new_btn:
                new_btn = await self.page.query_selector("[data-testid*='new']")

            if new_btn:
                await new_btn.click()
                await asyncio.sleep(1.5)
            else:
                await self.page.goto(
                    "https://lovable.dev",
                    wait_until="domcontentloaded",
                    timeout=90000,
                )
                for label in ("Generate with AI", "Get started", "Sign in"):
                    try:
                        await self.page.click(f"text={label }", timeout=5000)
                        break
                    except Exception:
                        continue

            textarea = await self.page.query_selector("textarea")
            if not textarea:
                print(
                    f"[{self .account_id }] Lovable: no se encontro textarea para el prompt."
                )
                return None

            await textarea.fill(prompt)
            await textarea.press("Enter")

            print(
                f"[{self .account_id }] Generando sitio en Lovable (timeout {timeout_sec }s)..."
            )

            deadline = time.monotonic() + timeout_sec
            while time.monotonic() < deadline:
                await asyncio.sleep(5)
                url = await self._find_preview_url()
                if url:
                    print(f"[{self .account_id }] Preview detectado: {url }")
                    return url

            url = await self._find_preview_url()
            if url:
                return url

            placeholder = f"https://demo-{self .account_id }.lovable.app"
            print(
                f"[{self .account_id }] Lovable: no se detecto URL de preview; "
                f"usando placeholder {placeholder } (revisa la sesion/UI)."
            )
            return placeholder

        except Exception as e:
            print(f"[{self .account_id }] Error en Lovable: {e }")
            return None

    async def stop(self):
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()


if __name__ == "__main__":

    async def test():
        from backend.generator.account_manager import AccountManager

        am = AccountManager()
        acc = am.get_next_account()
        lo = LovableAutomation(acc)
        try:
            await lo.start(headless=False)
            print("Lovable abierto. Cierra manualmente para terminar.")
            await asyncio.sleep(10)
        finally:
            await lo.stop()
