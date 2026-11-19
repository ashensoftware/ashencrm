"""Ningún test de este módulo abre WhatsApp ni marca un envío real."""

import asyncio

import pytest

from backend.config.settings import settings
from backend.domain.prospect import Prospect
from backend.outreach.policy import OutreachDeliveryBlocked
from backend.outreach.service import OutreachService
from backend.outreach.whatsapp import WhatsAppAutomation


@pytest.fixture()
def restore_outreach_flags():
    previous = (settings.app_env, settings.outreach_enabled)
    yield
    settings.app_env, settings.outreach_enabled = previous


def _prospect() -> Prospect:
    return Prospect(
        name="Negocio Seguridad",
        category="cafe",
        address="Calle 1",
        phone="3001234567",
        demo_url="https://acme.lovable.app",
    )


def test_send_proposal_dry_run_never_starts_browser(restore_outreach_flags):
    settings.app_env = "test"
    settings.outreach_enabled = True
    started = {"n": 0}

    class GuardedWhatsApp(WhatsAppAutomation):
        async def start(self, headless=True):
            started["n"] += 1
            raise AssertionError("no debe abrir navegador")

        async def send_message(self, phone: str, message: str) -> bool:
            raise AssertionError("no debe enviar")

    service = OutreachService(object())
    service.wa = GuardedWhatsApp()
    result = asyncio.run(service.send_proposal(_prospect()))
    assert result["dry_run"] is True
    assert result["delivered"] is False
    assert result["success"] is False
    assert started["n"] == 0
    assert "3001234567" not in str(result)


def test_send_message_is_blocked_in_development_even_if_flag_is_on(
    restore_outreach_flags,
):
    settings.app_env = "development"
    settings.outreach_enabled = True
    wa = WhatsAppAutomation()

    async def attempt():
        await wa.send_message("3001234567", "hola")

    with pytest.raises(OutreachDeliveryBlocked):
        asyncio.run(attempt())


def test_default_outreach_flag_is_off():
    import os

    if os.getenv("OUTREACH_ENABLED") is None:
        assert settings.outreach_enabled is False
