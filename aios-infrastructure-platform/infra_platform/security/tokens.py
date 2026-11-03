"""Opaque token primitives — used for build/run correlation ids shown
once, and generic secret-like values this platform needs to reference
without persisting the raw value."""
from __future__ import annotations

import hashlib
import secrets


def generate_raw_token(*, num_bytes: int = 32) -> str:
    return secrets.token_urlsafe(num_bytes)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
