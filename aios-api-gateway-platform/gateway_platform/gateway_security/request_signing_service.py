"""Request signature verification at the gateway edge: reuses the
platform-wide `sign_payload` HMAC primitive from `security.tokens`
(the same helper webhook delivery signs with) rather than
reimplementing HMAC here. This service's job is the verify-and-raise
contract callers need at the gateway boundary, not the signing
primitive itself."""
from __future__ import annotations

from gateway_platform.config.settings import Settings, get_settings
from gateway_platform.core.exceptions import RequestSignatureInvalidError
from gateway_platform.security.tokens import sign_payload


class RequestSigningService:
    def __init__(self, *, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def sign(self, payload: bytes, secret: str) -> str:
        algorithm = self.settings.security_request_signing_algorithm.replace("hmac-", "")
        return sign_payload(payload, secret, algorithm=algorithm)

    def verify(self, payload: bytes, signature: str, secret: str) -> None:
        expected = self.sign(payload, secret)
        if expected != signature:
            raise RequestSignatureInvalidError("request signature does not match expected value")
