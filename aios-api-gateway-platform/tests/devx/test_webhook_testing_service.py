from __future__ import annotations

from gateway_platform.devx.webhook_testing_service import WebhookTestingService
from gateway_platform.webhooks.signing_service import WebhookSigningService

SECRET = "test-secret"


def _ok_sender(url, payload, signature):
    return True, None


def _fail_sender(url, payload, signature):
    return False, "connection refused"


def test_send_test_event_success_and_signature_is_verifiable():
    service = WebhookTestingService()
    result = service.send_test_event(
        "https://example.com/hook", SECRET, event_type="ping", payload={"hello": "world"}, sender=_ok_sender,
    )
    assert result.success is True
    assert result.error is None

    signer = WebhookSigningService()
    envelope = {"event_type": "ping", "payload": {"hello": "world"}, "test": True}
    assert signer.verify_signature(envelope, result.signature, SECRET) is True


def test_send_test_event_failure_reports_error():
    service = WebhookTestingService()
    result = service.send_test_event(
        "https://example.com/hook", SECRET, event_type="ping", payload={}, sender=_fail_sender,
    )
    assert result.success is False
    assert result.error == "connection refused"
