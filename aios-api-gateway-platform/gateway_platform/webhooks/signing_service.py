"""Webhook payload signing: a stateless HMAC over the canonical JSON
payload, exactly the `X-Hub-Signature`-style contract every major
webhook provider uses so a receiver can verify authenticity without a
round trip back to this platform. Deliberately takes the raw secret
as a parameter on every call rather than storing or caching it
anywhere — `WebhookSubscriptionModel.secret_ref` only ever holds an
opaque `vault://...` pointer; this service never persists the value
itself."""
from __future__ import annotations

import hashlib
import hmac
import json

from gateway_platform.config.settings import Settings, get_settings

_ALGORITHMS = {"sha256": hashlib.sha256, "sha1": hashlib.sha1}


def _canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


class WebhookSigningService:
    def __init__(self, *, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def sign_payload(self, payload: dict, secret: str) -> str:
        algorithm = _ALGORITHMS[self.settings.webhook_signing_algorithm]
        digest = hmac.new(secret.encode(), _canonical(payload), algorithm).hexdigest()
        return f"{self.settings.webhook_signing_algorithm}={digest}"

    def verify_signature(self, payload: dict, signature: str, secret: str) -> bool:
        return hmac.compare_digest(self.sign_payload(payload, secret), signature)
