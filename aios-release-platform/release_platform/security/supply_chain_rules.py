"""Pure supply-chain integrity helpers — no DB or service imports.
Checksum verification is a straightforward hash-and-compare; kept
here (rather than inline in a service) so it's independently
unit-testable and reusable by any future caller (e.g. an installer
verifying a downloaded artifact offline, matching this platform's
offline-license-validation precedent)."""
from __future__ import annotations

import hashlib


def compute_checksum(data: bytes, *, algorithm: str = "sha256") -> str:
    hasher = hashlib.new(algorithm)
    hasher.update(data)
    return hasher.hexdigest()


def verify_checksum(data: bytes, *, expected: str, algorithm: str = "sha256") -> bool:
    return compute_checksum(data, algorithm=algorithm) == expected
