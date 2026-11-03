"""Sensitive-field masking for logs and structured payloads.

This is a deliberately simple, honestly-scoped implementation: it masks
by *key name* (case-insensitive substring match against
`settings.sensitive_field_names`) applied recursively through nested
dicts/lists. It does NOT attempt free-text PII detection inside log
*messages* (e.g. spotting a credit card number typed into a plain
string) — that needs a real NLP/regex PII-detection engine, which is
out of scope here the same way semantic search was an honestly-disclosed
gap in the Collaboration Platform. `mask_sensitive` is the single choke
point every log-ingestion path routes through, so swapping in a real
PII scanner later is a one-function change."""
from __future__ import annotations

from typing import Any

from observability_platform.config.settings import get_settings

MASK_VALUE = "***REDACTED***"


def _is_sensitive_key(key: str, sensitive_names: list[str]) -> bool:
    lowered = key.lower()
    return any(name in lowered for name in sensitive_names)


def mask_sensitive(payload: Any, *, sensitive_names: list[str] | None = None) -> Any:
    names = [n.lower() for n in (sensitive_names or get_settings().sensitive_field_names)]
    return _mask(payload, names)


def _mask(value: Any, names: list[str]) -> Any:
    if isinstance(value, dict):
        return {
            k: (MASK_VALUE if _is_sensitive_key(str(k), names) else _mask(v, names))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_mask(v, names) for v in value]
    return value
