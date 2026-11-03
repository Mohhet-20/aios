"""Opaque token primitives, reused wherever this platform needs a
raw-secret-shown-once flow (e.g. a scoped ingestion API key)."""
from __future__ import annotations

import hashlib
import secrets


def generate_raw_token(*, num_bytes: int = 32) -> str:
    return secrets.token_urlsafe(num_bytes)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
