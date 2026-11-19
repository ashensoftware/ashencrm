"""Política pura de CORS, SQL console y outreach."""

import os

import pytest

from backend.config.settings import settings
from backend.core.security_policy import (
    PRODUCTION_SQL_ACK,
    outreach_is_live,
    resolve_allowed_origins,
    resolve_sql_console_enabled,
)


def test_development_defaults_to_localhost_without_wildcard():
    origins = resolve_allowed_origins("development", None)
    assert "http://localhost:5173" in origins
    assert "http://127.0.0.1:5173" in origins
    assert "*" not in origins


def test_wildcard_is_rejected_in_every_environment():
    for env in ("development", "test", "production"):
        with pytest.raises(RuntimeError, match=r"\*"):
            resolve_allowed_origins(env, "*")


def test_production_requires_explicit_origins():
    with pytest.raises(RuntimeError):
        resolve_allowed_origins("production", "")
    assert resolve_allowed_origins("production", "https://crm.example.com") == [
        "https://crm.example.com"
    ]


def test_sql_console_is_off_by_default_and_locked_in_production():
    assert resolve_sql_console_enabled("development", None, "") is False
    assert resolve_sql_console_enabled("production", "1", "") is False
    assert resolve_sql_console_enabled("production", "true", "yes") is False
    assert resolve_sql_console_enabled("production", "1", PRODUCTION_SQL_ACK) is True
    assert resolve_sql_console_enabled("development", "1", "") is True


def test_process_defaults_keep_sql_console_off():
    if os.getenv("ALLOW_SQL_CONSOLE") is None and (
        os.getenv("APP_ENV") in (None, "", "development")
    ):
        assert settings.sql_console_enabled is False
        assert "*" not in settings.allowed_origins


def test_outreach_stays_dry_run_outside_production_even_if_enabled():
    assert outreach_is_live("development", True) is False
    assert outreach_is_live("test", True) is False
    assert outreach_is_live("staging", True) is False
    assert outreach_is_live("production", False) is False
    assert outreach_is_live("production", True) is True
