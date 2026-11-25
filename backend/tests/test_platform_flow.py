"""Autorización, cola durable, identidad, Places y Lovable sin red real."""

import json
import threading

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.api.app_factory import RuntimeSecurity, create_app
from backend.api.authorization import RateLimiter, required_access
from backend.core.auth import issue_local_token
from backend.core.secrets import decrypt_secret, encrypt_secret
from backend.core.ssrf import is_safe_public_url
from backend.domain.identity import canonical_domain, identity_keys, phone_e164
from backend.domain.prospect import Prospect
from backend.infrastructure.persistence.platform_repository import POSTGRES_CLAIM_SQL, PlatformRepository
from backend.infrastructure.providers.google_places import GooglePlacesClient, PlacesError
from backend.infrastructure.providers.lovable_mcp import API_KEY_SUPPORTED, LovableMcpClient
from backend.workers.runner import drain

SECRET = "test-local-secret"


def _security() -> RuntimeSecurity:
    return RuntimeSecurity(
        app_env="development",
        allowed_origins=("http://localhost:5173",),
        sql_console_enabled=False,
        outreach_enabled=False,
        auth_mode="local",
        auth_local_secret=SECRET,
    )


def _headers(role: str) -> dict[str, str]:
    token = issue_local_token(SECRET, role, subject=f"user-{role}", ttl_seconds=600)
    return {"Authorization": f"Bearer {token}"}


def test_route_classification():
    assert required_access("GET", "/api/livez") is None
    assert required_access("GET", "/api/auth/config") is None
    assert required_access("GET", "/api/prospects") == "authenticated"
    assert required_access("POST", "/api/scrape-interactive") == "campaigns:run"
    assert required_access("POST", "/api/prospects/Cafe/send-whatsapp") == "outreach:send"
    assert required_access("GET", "/api/admin/settings") == "role:admin"
    assert required_access("POST", "/api/v1/pipeline-runs/abc/cancel") == "runs:cancel"


def test_sensitive_routes_require_a_role(prospect_repo, platform_repo, monkeypatch):
    monkeypatch.setattr(
        "backend.api.routes.providers.settings.platform_secret_key",
        "master-key-for-tests",
    )
    repo = prospect_repo
    repo.insert_prospect(Prospect(name="Cafe Norte", category="cafe", address="Calle 1"))
    platform = platform_repo
    app = create_app(security=_security(), db=repo, platform=platform)
    with TestClient(app) as client:
        assert client.get("/api/livez").status_code == 200
        config = client.get("/api/auth/config").json()
        assert config["auth_mode"] == "local"
        assert "supabase_secret_key" not in config
        assert "sb_secret_" not in json.dumps(config)
        assert client.get("/api/prospects").status_code == 401
        assert client.get("/api/prospects", headers=_headers("viewer")).status_code == 200
        assert client.post("/api/scrape-interactive", json={}, headers=_headers("viewer")).status_code == 403
        scrape = client.post(
            "/api/scrape-interactive",
            json={"category": "cafe", "city": "Medellin", "limit": 1},
            headers=_headers("operator"),
        )
        assert scrape.status_code == 409
        patched = client.patch(
            "/api/prospects/Cafe%20Norte",
            json={"status": "demo_created", "demo_url": "https://demo-account-1.lovable.app"},
            headers=_headers("operator"),
        )
        assert patched.status_code == 400
        validated = client.post(
            "/api/demos/validate",
            json={"url": "https://demo-account-1.lovable.app"},
            headers=_headers("operator"),
        )
        assert validated.json()["success"] is False
        assert validated.json()["verified"] is False
        automate = client.post("/api/prospects/Cafe%20Norte/automate", headers=_headers("operator"))
        assert automate.json()["status"] == "MANUAL_ACTION_REQUIRED"
        assert client.get("/api/admin/providers/lovable", headers=_headers("operator")).status_code == 403
        created = client.post(
            "/api/admin/providers/lovable",
            json={"label": "principal", "access_token": "oauth-token-value", "workspace": "main"},
            headers=_headers("admin"),
        )
        assert created.status_code == 200
        body = created.json()
        assert body["secret_last4"] == "alue"
        assert "oauth-token-value" not in created.text
        listed = client.get("/api/admin/providers/lovable", headers=_headers("admin")).json()
        assert "secret_ciphertext" not in listed["connections"][0]
        assert listed["connections"][0]["secret_last4"] == "alue"
        run = client.post(
            "/api/v1/pipeline-runs",
            json={"campaign_id": "campana-http", "segment": "cafeterias", "max_results": 2},
            headers={**_headers("operator"), "Idempotency-Key": "http-1"},
        )
        assert run.status_code == 200
        assert run.json()["reused"] is False
        again = client.post(
            "/api/v1/pipeline-runs",
            json={"campaign_id": "campana-http"},
            headers={**_headers("operator"), "Idempotency-Key": "http-1"},
        )
        assert again.json()["id"] == run.json()["id"]
        assert client.post("/api/v1/pipeline-runs", json={"campaign_id": "x"}, headers=_headers("viewer")).status_code == 403


def test_rate_limiter_and_body_limit(prospect_repo, platform_repo):
    limiter = RateLimiter(limit=1, window_seconds=60)
    assert limiter.allow("client") is True
    assert limiter.allow("client") is False
    app = create_app(security=_security(), db=prospect_repo, platform=platform_repo)
    with TestClient(app) as client:
        response = client.post("/api/livez", headers={"content-length": "2000000"})
        assert response.status_code == 413


def test_job_recovers_without_double_claim(platform_repo, clean_db):
    store = platform_repo
    created = store.create_run(
        campaign_id="c1",
        requested_by="operator",
        idempotency_key="same-key",
        config={"places": []},
    )
    again = store.create_run(
        campaign_id="c1",
        requested_by="operator",
        idempotency_key="same-key",
        config={"places": []},
    )
    assert again["reused"] is True
    assert again["id"] == created["id"]
    first = store.claim_step("worker-a", now=2_000_000_000)
    assert first is not None
    results = []

    def second():
        results.append(store.claim_step("worker-b", now=2_000_000_000))

    thread = threading.Thread(target=second)
    thread.start()
    thread.join()
    assert results == [None]
    reopened = PlatformRepository(pool=clean_db)
    assert reopened.recover_expired(now=2_000_000_040, lease_seconds=30) == 1
    reclaimed = reopened.claim_step("worker-c", now=2_000_000_040)
    assert reclaimed["id"] == first["id"]
    assert reclaimed["attempt"] == 2


def test_pause_cancel_and_simulated_run_stays_dry(platform_repo):
    store = platform_repo
    created = store.create_run(
        campaign_id="c2",
        requested_by="operator",
        idempotency_key=None,
        config={
            "places": [
                {
                    "provider": "simulated",
                    "external_id": "sim-1",
                    "display_name": "Cafe Norte",
                    "domain": "https://www.cafenorte.example",
                    "phone": "3001112233",
                },
                {
                    "provider": "simulated",
                    "external_id": "sim-1",
                    "display_name": "Cafe Norte",
                    "domain": "cafenorte.example",
                    "phone": "+57 300 111 2233",
                },
            ]
        },
    )
    store.set_run_status(created["id"], "paused")
    assert store.claim_step("worker", now=2_000_000_000) is None
    store.set_run_status(created["id"], "running")
    assert drain(store, worker_id="worker") == 8
    snapshot = store.get_run(created["id"])
    assert snapshot["run"]["status"] == "incomplete"
    assert store.count_businesses() == 1
    second = store.create_run(
        campaign_id="c3",
        requested_by="operator",
        idempotency_key=None,
        config={"places": [{"provider": "simulated", "external_id": "sim-1", "display_name": "Cafe Norte"}]},
    )
    drain(store)
    assert store.get_run(second["id"])["run"]["status"] == "incomplete"
    assert store.count_businesses() == 1
    dry = store.list_outreach_messages()
    assert dry
    assert all(row["dry_run"] == 1 for row in dry)
    store.set_run_status(second["id"], "cancelled")
    assert store.get_run(second["id"])["run"]["status"] == "cancelled"


def test_identity_phone_and_domain():
    assert canonical_domain("https://www.CafeNorte.example/menu") == "cafenorte.example"
    assert phone_e164("3001112233", "CO") == "+573001112233"
    keys = identity_keys(provider="simulated", external_id="sim-1", domain="cafenorte.example", phone="+573001112233")
    assert ("provider:simulated", "sim-1") in keys
    assert ("domain", "cafenorte.example") in keys


def test_places_client_uses_documented_endpoint():
    seen = {}

    def transport(method, url, json, headers, timeout):
        seen.update(method=method, url=url, headers=headers, json=json, timeout=timeout)
        return httpx.Response(200, json={"places": [{"id": "places/1", "displayName": {"text": "Cafe"}}]})

    places = GooglePlacesClient("test-key", transport=transport).search_text("cafes en medellin", max_results=5)
    assert places[0]["id"] == "places/1"
    assert seen["url"] == "https://places.googleapis.com/v1/places:searchText"
    assert "places.id" in seen["headers"]["X-Goog-FieldMask"]
    with pytest.raises(PlacesError) as raised:
        GooglePlacesClient("").search_text("cafes")
    assert raised.value.code == "missing_api_key"


def test_lovable_oauth_only_and_secret_roundtrip():
    blocked = LovableMcpClient().call_tool("create_project", {"initial_message": "hola"}, token="")
    assert blocked["status"] == "MANUAL_ACTION_REQUIRED"
    assert API_KEY_SUPPORTED is False
    ciphertext = encrypt_secret("oauth-token-value", "master-key-for-tests")
    assert decrypt_secret(ciphertext, "master-key-for-tests") == "oauth-token-value"
    assert "oauth-token-value" not in ciphertext


def test_ssrf_blocks_local_targets(monkeypatch):
    assert is_safe_public_url("http://127.0.0.1/admin") is False
    assert is_safe_public_url("http://169.254.169.254/latest") is False
    monkeypatch.setattr(
        "backend.core.ssrf.socket.getaddrinfo",
        lambda *args, **kwargs: [(None, None, None, None, ("93.184.216.34", 443))],
    )
    assert is_safe_public_url("https://example.com/proyecto") is True


def test_postgres_claim_is_explicit():
    assert "FOR UPDATE OF s SKIP LOCKED" in POSTGRES_CLAIM_SQL


def test_screenshot_path_stays_inside_repo():
    from backend.api.routes.screenshots import SCREENSHOTS_DIR

    assert SCREENSHOTS_DIR.name == "screenshots"
    assert SCREENSHOTS_DIR.parent.name == "data"
