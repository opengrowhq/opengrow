"""API-key generation + hashing.

Keys are high-entropy random tokens, so a fast SHA-256 hash is used for O(1)
lookup on every request (bcrypt would be too slow per-request). Format:
`ogk_<url-safe-random>`; the first 12 chars are the non-secret `prefix`.
"""

from __future__ import annotations

import hashlib
import secrets

KEY_PREFIX = "ogk_"
PREFIX_LEN = 12


def generate_key() -> tuple[str, str, str]:
    """Return (plaintext, prefix, key_hash). Plaintext is shown to the user once."""
    token = f"{KEY_PREFIX}{secrets.token_urlsafe(32)}"
    return token, token[:PREFIX_LEN], hash_key(token)


def hash_key(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
