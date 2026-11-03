"""Webhook testing: a dry-run send that signs and fires a synthetic
event at a target URL through an injectable sender, without touching
a real subscription's delivery history -- lets a developer confirm
their endpoint handles the signature and payload shape correctly
before wiring up a live subscription. Deliberately does not persist
anything; it reuses `WebhookSigningService` but is otherwise a pure
function of its inputs."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from gateway_platform.webhooks.signing_service import WebhookSigningService

TestSenderResult = tuple[bool, str | None]
TestSender = Callable[[str, dict, str], TestSenderResult]


def _default_test_sender(url: str, payload: dict, signature: str) -> TestSenderResult:
    import httpx

    try:
        response = httpx.post(url, json=payload, headers={"X-AIOS-Signature": signature}, timeout=10.0)
        if response.status_code < 400:
            return True, None
        return False, f"HTTP {response.status_code}"
    except httpx.HTTPError as exc:
        return False, str(exc)


@dataclass
class WebhookTestResult:
    success: bool
    signature: str
    error: str | None = None


class WebhookTestingService:
    def __init__(self, *, signer: WebhookSigningService | None = None):
        self.signer = signer or WebhookSigningService()

    def send_test_event(
        self, target_url: str, secret: str, *, event_type: str, payload: dict, sender: TestSender | None = None,
    ) -> WebhookTestResult:
        sender = sender or _default_test_sender
        envelope = {"event_type": event_type, "payload": payload, "test": True}
        signature = self.signer.sign_payload(envelope, secret)
        success, error = sender(target_url, envelope, signature)
        return WebhookTestResult(success=success, signature=signature, error=error)
