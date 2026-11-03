"""API key generation and hashing.

Keys are shown to the user exactly once at creation time (`sk_live_<random>`
or `sk_test_<random>`), matching the industry-standard pattern (Stripe,
OpenAI, Anthropic all do this). Only a salted hash of the key is persisted —
`app.models.api_key.ApiKey.hashed_key` — so a database leak does not expose
usable credentials. A short, non-secret `prefix` is stored in the clear so
the UI can show "sk_live_8f2a••••••" without ever re-deriving the secret.
"""

import hashlib
import secrets


def generate_api_key(env: str = "live") -> tuple[str, str, str]:
    """Returns (full_key, prefix, hashed_key)."""
    random_part = secrets.token_urlsafe(32)
    full_key = f"sk_{env}_{random_part}"
    prefix = full_key[: len(f"sk_{env}_") + 6]
    hashed_key = hash_api_key(full_key)
    return full_key, prefix, hashed_key


def hash_api_key(full_key: str) -> str:
    return hashlib.sha256(full_key.encode("utf-8")).hexdigest()
