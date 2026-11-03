from datetime import datetime, timedelta, timezone

from release_platform.licensing.license_rules import is_expired, sign_license_payload, verify_offline_license


def test_is_expired_none_is_never_expired():
    assert is_expired(None) is False


def test_is_expired_past_date():
    assert is_expired(datetime.now(timezone.utc) - timedelta(days=1)) is True


def test_is_expired_future_date():
    assert is_expired(datetime.now(timezone.utc) + timedelta(days=1)) is False


def test_is_expired_handles_naive_datetime():
    naive_past = (datetime.now(timezone.utc) - timedelta(days=1)).replace(tzinfo=None)
    assert is_expired(naive_past) is True


def test_offline_license_round_trip():
    payload = {"org": "acme", "seats": 50}
    signature = sign_license_payload(payload, secret="top-secret")
    assert verify_offline_license(payload, signature=signature, secret="top-secret") is True


def test_offline_license_rejects_wrong_secret():
    payload = {"org": "acme", "seats": 50}
    signature = sign_license_payload(payload, secret="top-secret")
    assert verify_offline_license(payload, signature=signature, secret="wrong-secret") is False


def test_offline_license_rejects_tampered_payload():
    payload = {"org": "acme", "seats": 50}
    signature = sign_license_payload(payload, secret="top-secret")
    tampered = {"org": "acme", "seats": 5000}
    assert verify_offline_license(tampered, signature=signature, secret="top-secret") is False
