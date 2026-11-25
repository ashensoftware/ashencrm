"""Archivos de negocio fuera del disco del VM (data-platform D2).

Claves con prefijo por tipo: `quotes/<client_id>/quote.pdf`, `photos/...`. La
base guarda la clave, nunca una URL ni una ruta del disco.

- `LocalFileStore`: carpeta local `data/files/` (desarrollo y pruebas, gitignored).
- `GcsFileStore`: bucket privado `ashencrm-files` (producción). Credenciales por
  ADC: la cuenta de servicio del VM, o `gcloud auth application-default login`
  en un PC. La API sirve los archivos detrás del login; el bucket nunca es público.
"""

from __future__ import annotations

import re
import threading
from pathlib import Path
from typing import Any, Protocol

_PREFIXES = ("quotes", "photos")
_KEY_RE = re.compile(r"^(?:%s)(?:/[A-Za-z0-9._-]+)+$" % "|".join(_PREFIXES))


def validate_key(key: str) -> str:
    """Acepta solo `<prefijo>/<segmentos seguros>`: nada de rutas absolutas ni `..`."""
    if (
        not isinstance(key, str)
        or not _KEY_RE.match(key)
        or any(part in {".", ".."} for part in key.split("/"))
    ):
        raise ValueError(f"Clave de archivo inválida: {key!r}")
    return key


class FileStore(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> None: ...

    def get(self, key: str) -> bytes | None:
        """Contenido del archivo, o None si no existe."""

    def delete(self, key: str) -> None:
        """Borra el archivo; no falla si ya no existe."""


class LocalFileStore:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        return self.root.joinpath(*validate_key(key).split("/"))

    def put(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(path)

    def get(self, key: str) -> bytes | None:
        try:
            return self._path(key).read_bytes()
        except FileNotFoundError:
            return None

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)


class GcsFileStore:
    def __init__(self, bucket: str, client: Any = None):
        if not bucket:
            raise ValueError("FILES_BUCKET está vacío")
        self.bucket_name = bucket
        self._client = client
        self._bucket: Any = None
        self._lock = threading.Lock()

    def _get_bucket(self) -> Any:
        with self._lock:
            if self._bucket is None:
                if self._client is None:
                    from google.cloud import storage

                    self._client = storage.Client()
                self._bucket = self._client.bucket(self.bucket_name)
            return self._bucket

    def put(self, key: str, data: bytes, content_type: str) -> None:
        blob = self._get_bucket().blob(validate_key(key))
        blob.upload_from_string(data, content_type=content_type)

    def get(self, key: str) -> bytes | None:
        from google.api_core.exceptions import NotFound

        blob = self._get_bucket().blob(validate_key(key))
        try:
            return blob.download_as_bytes()
        except NotFound:
            return None

    def delete(self, key: str) -> None:
        from google.api_core.exceptions import NotFound

        try:
            self._get_bucket().blob(validate_key(key)).delete()
        except NotFound:
            pass


_store: FileStore | None = None
_store_lock = threading.Lock()


def get_file_store() -> FileStore:
    """El bucket si FILES_BUCKET está definido; si no, la carpeta local. Uno por proceso."""
    global _store
    with _store_lock:
        if _store is None:
            from backend.config.settings import settings

            if settings.files_bucket:
                _store = GcsFileStore(settings.files_bucket)
            else:
                _store = LocalFileStore(settings.files_dir)
        return _store


def set_file_store(store: FileStore | None) -> None:
    """Pruebas: reemplaza el almacén por defecto (None vuelve a resolverlo)."""
    global _store
    with _store_lock:
        _store = store
