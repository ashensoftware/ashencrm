"""La generación no puede marcar éxito sin artefacto verificable."""

import asyncio
import tempfile
from pathlib import Path

from backend.domain.prospect import Prospect, ProspectStatus
from backend.generator import service as generator_service
from backend.generator.verification import conclude_lovable_preview


class MemoryDb:
    def __init__(self):
        self.patches = []

    def patch_prospect(self, name, address, data):
        self.patches.append(dict(data))


def _run(url, screenshot):
    class Lo:
        def __init__(self, account):
            self.account = account

        async def start(self, headless=True):
            return None

        async def create_site(self, prompt):
            return url

        async def stop(self):
            return None

    class Shots:
        async def capture(self, target, filename):
            return screenshot

    class Accounts:
        def get_next_account(self):
            return {"id": "account_1", "path": "unused"}

    original = generator_service.LovableAutomation
    generator_service.LovableAutomation = Lo
    db = MemoryDb()
    service = generator_service.GeneratorService.__new__(
        generator_service.GeneratorService
    )
    service.db = db
    service.account_manager = Accounts()
    service.screenshot_taker = Shots()
    prospect = Prospect(name="Negocio Demo", category="cafe", address="Calle 1")
    try:
        result = asyncio.run(service.run_full_generation(prospect))
    finally:
        generator_service.LovableAutomation = original
    return result, db


def test_timeout_does_not_succeed():
    assert conclude_lovable_preview(None, timed_out=True) is None
    result, db = _run(None, None)
    assert result["success"] is False
    assert result["status"] == "incomplete"
    assert result["status"] != ProspectStatus.DEMO_CREATED.value
    assert result["status"] != "demo_ready"
    assert all(patch.get("status") != "demo_created" for patch in db.patches)


def test_placeholder_url_does_not_succeed():
    placeholder = "https://demo-account_1.lovable.app"
    assert conclude_lovable_preview(placeholder, timed_out=False) is None
    result, db = _run(placeholder, "C:/no/existe.png")
    assert result["success"] is False
    assert result["status"] != "demo_created"
    assert result["status"] != "demo_ready"
    assert all(patch.get("demo_url", "") != placeholder for patch in db.patches)
    assert all(patch.get("status") != "demo_created" for patch in db.patches)


def test_failed_screenshot_does_not_produce_demo_ready():
    result, db = _run("https://acme.lovable.app", None)
    assert result["success"] is False
    assert result["status"] == "incomplete"
    assert result["status"] != "demo_ready"
    assert result["status"] != ProspectStatus.DEMO_CREATED.value
    assert "demo_url" not in result
    assert all(patch.get("status") != "demo_created" for patch in db.patches)

    missing = _run("https://acme.lovable.app", "C:/tmp/captura-inexistente.png")[0]
    assert missing["success"] is False
    assert missing["status"] != "demo_ready"


def test_verified_url_and_screenshot_can_mark_demo_created():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        shot = Path(tmp) / "hero.png"
        shot.write_bytes(b"png")
        result, db = _run("https://acme.lovable.app/preview?x=1", str(shot))
        assert shot.stat().st_size > 0
    assert result["success"] is True
    assert result["status"] == ProspectStatus.DEMO_CREATED.value
    assert result["demo_url"] == "https://acme.lovable.app/preview?x=1"
    assert db.patches[-1]["status"] == "demo_created"
    assert db.patches[-1]["screenshot_path"] == str(shot)
