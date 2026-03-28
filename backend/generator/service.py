"""Orchestrates demo generation: prompt, Lovable, screenshot."""

import re

from backend.config.settings import settings
from backend.domain.prospect import Prospect, ProspectStatus
from backend.generator.account_manager import AccountManager
from backend.generator.lovable import LovableAutomation
from backend.generator.prompt_builder import build_demo_prompt
from backend.generator.screenshot import ScreenshotTaker


class GeneratorService:
    def __init__(self, db):
        self.db = db
        self.account_manager = AccountManager()
        self.screenshot_taker = ScreenshotTaker()

    async def run_full_generation(self, prospect: Prospect) -> dict:
        prompt = build_demo_prompt(prospect)
        self.db.patch_prospect(prospect.name, prospect.address, {"prompt_used": prompt})
        account = self.account_manager.get_next_account()
        lo = LovableAutomation(account)
        try:
            await lo.start(headless=settings.generator.lovable_headless)
            demo_url = await lo.create_site(prompt)
            if not demo_url:
                return {"error": "No se pudo generar el sitio en Lovable"}
            safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", prospect.name.strip().lower())
            screenshot_path = await self.screenshot_taker.capture(
                demo_url, f"hero_{safe_name }"
            )
            update_data = {
                "demo_url": demo_url,
                "screenshot_path": screenshot_path,
                "lovable_account_used": account["id"],
                "status": ProspectStatus.DEMO_CREATED.value,
            }
            self.db.patch_prospect(prospect.name, prospect.address, update_data)
            return {
                "success": True,
                "demo_url": demo_url,
                "screenshot_path": screenshot_path,
            }
        except Exception as e:
            print(f"[GeneratorService] Error: {e }")
            return {"error": str(e)}
        finally:
            await lo.stop()
