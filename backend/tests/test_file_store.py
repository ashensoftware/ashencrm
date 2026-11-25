"""Almacén de archivos (D2): claves seguras, local, GCS con un cliente falso y rutas de cotización."""

import pytest
from fastapi.testclient import TestClient

from backend.api.app_factory import RuntimeSecurity, create_app
from backend.core.auth import issue_local_token
from backend.infrastructure.storage import GcsFileStore, LocalFileStore, validate_key

SECRET = "test-local-secret"
PDF = b"%PDF-1.4\n% cotizacion de prueba\n%%EOF\n"


@pytest.mark.parametrize(
    "key",
    [
        "",
        "quote.pdf",
        "/quotes/1/quote.pdf",
        "quotes/../db/prospects.db",
        "quotes/./x.pdf",
        "quotes\\1\\quote.pdf",
        "C:\\data\\client_uploads\\1\\quote.pdf",
        "other/1/quote.pdf",
        "quotes/",
        "quotes//x.pdf",
    ],
)
def test_validate_key_rejects_paths_and_unknown_prefixes(key):
    with pytest.raises(ValueError):
        validate_key(key)


def test_validate_key_accepts_known_prefixes():
    assert validate_key("quotes/12/quote.pdf") == "quotes/12/quote.pdf"
    assert validate_key("photos/ChIJabc-_.1/0.jpg") == "photos/ChIJabc-_.1/0.jpg"


def test_local_store_roundtrip(tmp_path):
    store = LocalFileStore(tmp_path)
    assert store.get("quotes/1/quote.pdf") is None
    store.put("quotes/1/quote.pdf", PDF, "application/pdf")
    assert store.get("quotes/1/quote.pdf") == PDF
    assert (tmp_path / "quotes" / "1" / "quote.pdf").read_bytes() == PDF
    store.delete("quotes/1/quote.pdf")
    store.delete("quotes/1/quote.pdf")  # idempotente
    assert store.get("quotes/1/quote.pdf") is None


class _FakeBlob:
    def __init__(self, objects: dict, name: str):
        self._objects, self.name = objects, name

    def upload_from_string(self, data, content_type=None):
        self._objects[self.name] = (bytes(data), content_type)

    def download_as_bytes(self):
        from google.api_core.exceptions import NotFound

        if self.name not in self._objects:
            raise NotFound(self.name)
        return self._objects[self.name][0]

    def delete(self):
        from google.api_core.exceptions import NotFound

        if self._objects.pop(self.name, None) is None:
            raise NotFound(self.name)


class _FakeClient:
    def __init__(self):
        self.objects: dict = {}
        self.buckets: list[str] = []

    def bucket(self, name):
        self.buckets.append(name)
        objects = self.objects

        class _Bucket:
            def blob(self, key):
                return _FakeBlob(objects, key)

        return _Bucket()


def test_gcs_store_uses_bucket_and_maps_not_found_to_none():
    pytest.importorskip("google.cloud.storage")
    client = _FakeClient()
    store = GcsFileStore("ashencrm-files", client=client)
    assert store.get("quotes/1/quote.pdf") is None
    store.put("quotes/1/quote.pdf", PDF, "application/pdf")
    assert client.objects["quotes/1/quote.pdf"] == (PDF, "application/pdf")
    assert store.get("quotes/1/quote.pdf") == PDF
    store.delete("quotes/1/quote.pdf")
    store.delete("quotes/1/quote.pdf")
    assert store.get("quotes/1/quote.pdf") is None
    assert client.buckets == ["ashencrm-files"]
    with pytest.raises(ValueError):
        store.put("../escape", PDF, "application/pdf")


def _app(repo):
    security = RuntimeSecurity(
        app_env="development",
        allowed_origins=("http://localhost:5173",),
        sql_console_enabled=False,
        outreach_enabled=False,
        auth_mode="local",
        auth_local_secret=SECRET,
    )
    return create_app(security=security, db=repo)


def _admin() -> dict[str, str]:
    token = issue_local_token(SECRET, "admin", subject="user-admin", ttl_seconds=600)
    return {"Authorization": f"Bearer {token}"}


def test_quote_pdf_goes_through_the_file_store(prospect_repo, file_store):
    with TestClient(_app(prospect_repo)) as client:
        created = client.post("/api/clients", json={"display_name": "Cliente PDF"}, headers=_admin())
        assert created.status_code == 200, created.text
        cid = created.json()["id"]
        key = f"quotes/{cid}/quote.pdf"

        assert client.get(f"/api/clients/{cid}/quote-pdf", headers=_admin()).status_code == 404

        uploaded = client.post(
            f"/api/clients/{cid}/quote",
            files={"file": ("cotizacion.pdf", PDF, "application/pdf")},
            data={"quote_amount": "1500000", "quote_currency": "COP"},
            headers=_admin(),
        )
        assert uploaded.status_code == 200, uploaded.text
        assert uploaded.json()["quote_pdf_path"] == key
        assert file_store.get(key) == PDF

        downloaded = client.get(f"/api/clients/{cid}/quote-pdf", headers=_admin())
        assert downloaded.status_code == 200
        assert downloaded.content == PDF
        assert downloaded.headers["content-type"] == "application/pdf"
        assert "cotizacion.pdf" in downloaded.headers["content-disposition"]

        assert client.delete(f"/api/clients/{cid}", headers=_admin()).status_code == 200
        assert file_store.get(key) is None


def test_quote_rejects_non_pdf_and_legacy_disk_paths(prospect_repo, file_store):
    with TestClient(_app(prospect_repo)) as client:
        cid = client.post("/api/clients", json={"display_name": "Cliente viejo"}, headers=_admin()).json()["id"]
        bad = client.post(
            f"/api/clients/{cid}/quote",
            files={"file": ("notas.txt", b"hola", "text/plain")},
            headers=_admin(),
        )
        assert bad.status_code == 400
        # Antes de D2 se guardaba una ruta del disco del VM: ya no se sirve.
        prospect_repo.update_client(cid, {"quote_pdf_path": "/opt/ashencrm/repo/data/client_uploads/1/quote.pdf"})
        assert client.get(f"/api/clients/{cid}/quote-pdf", headers=_admin()).status_code == 404
