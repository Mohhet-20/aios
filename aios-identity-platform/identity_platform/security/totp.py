"""RFC 6238 TOTP (built directly on RFC 4226 HOTP), implemented from
scratch with stdlib `hmac`/`hashlib`/`base64` only — no third-party
TOTP/authenticator library, consistent with this platform's "genuinely
computed, no fabrication" approach to crypto primitives (mirrors
`security/hashing.py`'s stdlib PBKDF2 choice). Compatible with any
standard authenticator app (Google Authenticator, Authy, 1Password,
etc.) since it follows the RFC byte-for-byte: HMAC-SHA1, 30-second
step, 6 digits, base32 secret."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote


def generate_totp_secret(*, num_bytes: int = 20) -> str:
    """Base32-encoded, no padding — the form authenticator apps expect."""
    return base64.b32encode(secrets.token_bytes(num_bytes)).decode("utf-8").rstrip("=")


def _hotp(secret_b32: str, counter: int, *, digits: int) -> str:
    # base32 requires padding to a multiple of 8 chars to decode.
    padded = secret_b32 + "=" * (-len(secret_b32) % 8)
    key = base64.b32decode(padded.upper())
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    truncated = digest[offset:offset + 4]
    code_int = struct.unpack(">I", truncated)[0] & 0x7FFFFFFF
    return str(code_int % (10**digits)).zfill(digits)


def generate_totp(secret_b32: str, *, timestamp: float | None = None, period: int = 30, digits: int = 6) -> str:
    moment = timestamp if timestamp is not None else time.time()
    counter = int(moment // period)
    return _hotp(secret_b32, counter, digits=digits)


def verify_totp(
    secret_b32: str, candidate_code: str, *, timestamp: float | None = None, period: int = 30,
    digits: int = 6, valid_window: int = 1,
) -> bool:
    """Accepts codes from `valid_window` steps before/after the current
    step, to absorb ordinary clock drift between server and device."""
    moment = timestamp if timestamp is not None else time.time()
    counter = int(moment // period)
    candidate_code = candidate_code.strip()
    for offset in range(-valid_window, valid_window + 1):
        expected = _hotp(secret_b32, counter + offset, digits=digits)
        if hmac.compare_digest(expected, candidate_code):
            return True
    return False


def provisioning_uri(secret_b32: str, *, account_name: str, issuer: str, digits: int = 6, period: int = 30) -> str:
    """`otpauth://` URI an authenticator app can render as a QR code."""
    label = quote(f"{issuer}:{account_name}")
    params = f"secret={secret_b32}&issuer={quote(issuer)}&digits={digits}&period={period}&algorithm=SHA1"
    return f"otpauth://totp/{label}?{params}"
