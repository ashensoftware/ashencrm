"""Scripts locales (D6): solo con el rol crm_ingest, nunca con DATABASE_URL."""

import pytest

from backend.config.settings import settings
from backend.infrastructure.persistence import ingest


@pytest.mark.parametrize(
    "url, role",
    [
        ("postgresql://crm_ingest.abcdef:pw@aws-0-us-east-2.pooler.supabase.com:5432/postgres", "crm_ingest"),
        ("postgresql://crm_ingest:pw@localhost:5432/ashencrm", "crm_ingest"),
        ("postgresql://crm_app.abcdef:pw@host:5432/postgres", "crm_app"),
        ("postgresql://postgres:pw@host/postgres", "postgres"),
    ],
)
def test_ingest_role_reads_pooler_and_plain_users(url, role):
    assert ingest.ingest_role(url) == role


def test_ingest_repository_requires_its_own_url(monkeypatch):
    monkeypatch.setattr(settings, "database_ingest_url", "")
    monkeypatch.setattr(settings, "database_url", "postgresql://crm_app:pw@host/db")
    with pytest.raises(RuntimeError, match="DATABASE_INGEST_URL"):
        ingest.ingest_repository()


def test_ingest_repository_refuses_other_roles(monkeypatch):
    monkeypatch.setattr(settings, "database_ingest_url", "postgresql://crm_app.ref:pw@host/db")
    with pytest.raises(RuntimeError, match="crm_ingest"):
        ingest.ingest_repository()
