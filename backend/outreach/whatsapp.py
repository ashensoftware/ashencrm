"""
Módulo para automatizar el envío de mensajes por WhatsApp Web.
"""

import asyncio
import os
from pathlib import Path
from typing import Optional
from urllib.parse import quote
from playwright.async_api import async_playwright

from backend.config.settings import settings


class WhatsAppAutomation:
    def __init__(self):
        self.session_path = settings.sessions_dir / "whatsapp"
        self.session_path.mkdir(parents=True, exist_ok=True)
        self.playwright = None
        self.context = None
        self.page = None

    async def start(self, headless: bool = True):
        """
        Inicia el navegador con la sesión persistente de WhatsApp.
        """
        self.playwright = await async_playwright().start()
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.session_path.absolute()),
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        self.page = await self.context.new_page()
        return self.page

    async def login(self):
        """
        Navega a WhatsApp Web y permite el login manual si es necesario.
        """
        await self.page.goto("https://web.whatsapp.com", wait_until="networkidle")
        print("Si es la primera vez, escanea el codigo QR en la ventana del navegador.")

        try:
            await self.page.wait_for_selector("#pane-side", timeout=60000)
            print("WhatsApp Web esta listo.")
            return True
        except:
            print("Tiempo de espera agotado para el login de WhatsApp.")
            return False

    def _normalize_phone(self, phone: str) -> str:
        """Normaliza teléfono a formato internacional numérico para WhatsApp."""
        clean_phone = "".join(filter(str.isdigit, phone or ""))

        if len(clean_phone) == 10:
            clean_phone = f"57{clean_phone }"
        return clean_phone

    def _build_send_url(self, phone: str, message: str) -> str:
        """Construye URL de envío con texto URL-encoded."""
        clean_phone = self._normalize_phone(phone)
        encoded_message = quote(message or "", safe="")
        return f"https://web.whatsapp.com/send?phone={clean_phone }&text={encoded_message }"

    async def send_message(self, phone: str, message: str) -> bool:
        """
        Envía un mensaje a un número específico vía URL directa.
        """
        url = self._build_send_url(phone, message)

        try:
            await self.page.goto(url, wait_until="networkidle")

            send_btn_selector = "span[data-icon='send']"
            await self.page.wait_for_selector(send_btn_selector, timeout=30000)
            await self.page.click(send_btn_selector)

            await asyncio.sleep(2)
            print(f"Mensaje enviado a {phone }")
            return True
        except Exception as e:
            print(f"Error enviando mensaje a {phone }: {e }")
            return False

    async def stop(self):
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()


if __name__ == "__main__":

    async def test():
        wa = WhatsAppAutomation()
        try:

            await wa.start(headless=False)
            if await wa.login():

                pass
            await asyncio.sleep(10)
        finally:
            await wa.stop()
