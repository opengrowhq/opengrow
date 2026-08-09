from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


class CredentialCryptoError(Exception):
    pass


def _fernet() -> Fernet:
    """Derive a stable app-local encryption key from JWT_SECRET.

    This keeps the first implementation dependency-free from extra key-management
    config. Hosted/prod already sources JWT_SECRET from Infisical; lite sources it
    from env. Rotating JWT_SECRET will invalidate stored connector credentials.
    """
    if not settings.JWT_SECRET:
        raise CredentialCryptoError("JWT_SECRET is required to encrypt credentials")
    digest = hashlib.sha256(settings.JWT_SECRET.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str) -> str:
    if not value:
        raise CredentialCryptoError("Cannot encrypt an empty credential")
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise CredentialCryptoError("Credential could not be decrypted") from exc
