from __future__ import annotations

from gateway_platform.webhooks.signing_service import WebhookSigningService

SECRET = "top-secret-value"


def test_sign_and_verify_round_trip():
    service = WebhookSigningService()
    payload = {"event": "order.created", "id": 42}
    signature = service.sign_payload(payload, SECRET)
    assert service.verify_signature(payload, signature, SECRET) is True


def test_tampered_payload_fails_verification():
    service = WebhookSigningService()
    payload = {"event": "order.created", "id": 42}
    signature = service.sign_payload(payload, SECRET)
    tampered = {"event": "order.created", "id": 43}
    assert service.verify_signature(tampered, signature, SECRET) is False


def test_wrong_secret_fails_verification():
    service = WebhookSigningService()
    payload = {"event": "order.created"}
    signature = service.sign_payload(payload, SECRET)
    assert service.verify_signature(payload, signature, "wrong-secret") is False


def test_signature_is_prefixed_with_algorithm():
    service = WebhookSigningService()
    signature = service.sign_payload({"a": 1}, SECRET)
    assert signature.startswith("sha256=")
