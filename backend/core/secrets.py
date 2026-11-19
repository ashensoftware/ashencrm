"""Cifrado de tokens de proveedor. La clave maestra no se guarda en la base."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken


def _fernet(master_key: str) -> Fernet:
    if not master_key:
        raise RuntimeError("PLATFORM_SECRET_KEY es obligatoria para guardar secretos")
    digest = hashlib.sha256(master_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str, master_key: str) -> str:
    return _fernet(master_key).encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(ciphertext: str, master_key: str) -> str:
    try:
        return _fernet(master_key).decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError("No se pudo descifrar el secreto") from exc


def secret_last4(value: str) -> str:
    cleaned = value.strip()
    if len(cleaned) < 4:
        return "****"
    return cleaned[-4:]
