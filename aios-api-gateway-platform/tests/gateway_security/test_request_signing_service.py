from __future__ import annotations

import pytest

from gateway_platform.core.exceptions import RequestSignatureInvalidError
from gateway_platform.gateway_security.request_signing_service import RequestSigningService

SECRET = "gw-secret"


def test_sign_and_verify_round_trip():
    service = RequestSigningService()
    payload = b'{"path": "/orders", "method": "POST"}'
    signature = service.sign(payload, SECRET)
    service.verify(payload, signature, SECRET)  # should not raise


def test_verify_raises_on_mismatch():
    service = RequestSigningService()
    payload = b'{"path": "/orders"}'
    signature = service.sign(payload, SECRET)
    with pytest.raises(RequestSignatureInvalidError):
        service.verify(b'{"path": "/tampered"}', signature, SECRET)
