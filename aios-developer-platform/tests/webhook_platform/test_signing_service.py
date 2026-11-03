import pytest

from developer_platform.core.exceptions import WebhookSignatureError
from developer_platform.webhook_platform.signing_service import WebhookSigningService


def test_sign_and_verify_round_trip():
    service = WebhookSigningService()
    payload = {"event": "sdk_call", "id": "evt-1"}
    signature = service.sign_payload(payload, "shh-secret")
    assert signature.startswith("sha256=")
    assert service.verify_signature(payload, signature, "shh-secret") is True


def test_verify_fails_with_wrong_secret():
    service = WebhookSigningService()
    payload = {"a": 1}
    signature = service.sign_payload(payload, "secret-a")
    assert service.verify_signature(payload, signature, "secret-b") is False


def test_signature_is_order_independent_for_dict_keys():
    service = WebhookSigningService()
    sig1 = service.sign_payload({"a": 1, "b": 2}, "secret")
    sig2 = service.sign_payload({"b": 2, "a": 1}, "secret")
    assert sig1 == sig2


def test_unsupported_algorithm_raises():
    from developer_platform.config.settings import Settings

    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", secret_key="x" * 32, webhook_signing_algorithm="md5")
    service = WebhookSigningService(settings=settings)
    with pytest.raises(WebhookSignatureError):
        service.sign_payload({"a": 1}, "secret")
