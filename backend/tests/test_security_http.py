"""HTTP: CORS, auth de /api/admin y consola SQL de solo lectura."""

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api.app_factory import RuntimeSecurity, create_app
from backend.core.auth import issue_local_token
from backend.infrastructure.persistence.prospect_repository import ProspectRepository

SECRET = "test-local-secret"


def _security(**overrides) -> RuntimeSecurity:
    base = dict(
        app_env="development",
        allowed_origins=(
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ),
        sql_console_enabled=False,
        outreach_enabled=False,
        auth_mode="local",
        auth_local_secret=SECRET,
    )
    base.update(overrides)
    return RuntimeSecurity(**base)


@pytest.fixture()
def repo():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        yield ProspectRepository(db_path=Path(tmp) / "t.db")


def _token(role: str) -> str:
    return issue_local_token(SECRET, role, subject=f"user-{role}", ttl_seconds=600)


def _auth(role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(role)}"}


def test_cors_echoes_localhost_and_never_wildcard(repo):
    app = create_app(security=_security(), db=repo)
    with TestClient(app) as client:
        allowed = client.get(
            "/api/auth/me",
            headers={"Origin": "http://localhost:5173"},
        )
        assert (
            allowed.headers.get("access-control-allow-origin")
            == "http://localhost:5173"
        )
        blocked = client.get(
            "/api/auth/me",
            headers={"Origin": "https://evil.example"},
        )
        echoed = blocked.headers.get("access-control-allow-origin")
        assert echoed != "*"
        assert echoed != "https://evil.example"


def test_production_rejects_local_auth_and_wildcard():
    with pytest.raises(RuntimeError, match="oidc"):
        create_app(
            security=_security(
                app_env="production",
                allowed_origins=("https://crm.example.com",),
                auth_mode="local",
            )
        )
    with pytest.raises(RuntimeError, match=r"\*"):
        create_app(
            security=_security(
                app_env="production",
                allowed_origins=("*",),
                auth_mode="oidc",
                oidc_issuer="https://issuer.example",
                oidc_audience="ashencrm",
                oidc_jwks_url="https://issuer.example/jwks",
            )
        )


def test_production_cors_is_explicit(repo):
    app = create_app(
        security=_security(
            app_env="production",
            allowed_origins=("https://crm.example.com",),
            auth_mode="oidc",
            oidc_issuer="https://issuer.example",
            oidc_audience="ashencrm",
            oidc_jwks_url="https://issuer.example/jwks",
        ),
        db=repo,
    )
    with TestClient(app) as client:
        response = client.get(
            "/api/auth/me",
            headers={"Origin": "https://crm.example.com"},
        )
        assert (
            response.headers.get("access-control-allow-origin")
            == "https://crm.example.com"
        )
        assert response.headers.get("access-control-allow-origin") != "*"


def test_admin_requires_admin_role(repo):
    app = create_app(security=_security(), db=repo)
    with TestClient(app) as client:
        missing = client.get("/api/admin/settings")
        assert missing.status_code == 401
        viewer = client.get("/api/admin/settings", headers=_auth("viewer"))
        assert viewer.status_code == 403
        operator = client.patch(
            "/api/admin/settings",
            headers=_auth("operator"),
            json={"default_city": "Bogotá"},
        )
        assert operator.status_code == 403
        admin = client.get("/api/admin/settings", headers=_auth("admin"))
        assert admin.status_code == 200
        assert "default_city" in admin.json()
        me = client.get("/api/auth/me", headers=_auth("reviewer"))
        body = me.json()
        assert body["role"] == "reviewer"
        assert "demos:approve" in body["permissions"]
        assert "admin:settings" not in body["permissions"]
        assert "outreach:send" not in body["permissions"]


def test_sql_console_absent_when_disabled(repo):
    app = create_app(security=_security(sql_console_enabled=False), db=repo)
    with TestClient(app) as client:
        hidden = client.post(
            "/api/admin/sql",
            headers=_auth("admin"),
            json={"sql": "SELECT 1"},
        )
        assert hidden.status_code == 404
        status = client.get("/api/admin/sql/status", headers=_auth("admin"))
        assert status.status_code == 200
        assert status.json() == {"enabled": False}
        anonymous = client.get("/api/admin/sql/status")
        assert anonymous.status_code == 401


def test_sql_console_read_only_and_authorized(repo):
    app = create_app(security=_security(sql_console_enabled=True), db=repo)
    with TestClient(app) as client:
        assert (
            client.post("/api/admin/sql", json={"sql": "SELECT 1"}).status_code == 401
        )
        assert (
            client.post(
                "/api/admin/sql",
                headers=_auth("viewer"),
                json={"sql": "SELECT 1"},
            ).status_code
            == 403
        )
        rejected = client.post(
            "/api/admin/sql",
            headers=_auth("admin"),
            json={"sql": "DELETE FROM prospects"},
        )
        assert rejected.status_code == 400
        assert "rechazada" in rejected.json()["detail"].lower()
        for statement in (
            "INSERT INTO prospects (name, category) VALUES ('a', 'b')",
            "DROP TABLE prospects",
            "UPDATE prospects SET notes = 'x'",
            "PRAGMA writable_schema = ON",
        ):
            response = client.post(
                "/api/admin/sql",
                headers=_auth("admin"),
                json={"sql": statement},
            )
            assert response.status_code == 400
        selected = client.post(
            "/api/admin/sql",
            headers=_auth("admin"),
            json={"sql": "SELECT 1 AS n"},
        )
        assert selected.status_code == 200
        assert selected.json()["rows"] == [{"n": 1}]
