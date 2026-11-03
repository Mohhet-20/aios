from __future__ import annotations

import pytest

from gateway_platform.core.exceptions import ThreatDetectedError
from gateway_platform.gateway_security.threat_detection_service import ThreatDetectionService


def test_is_bot_detects_known_bot_user_agent():
    service = ThreatDetectionService()
    assert service.is_bot("Googlebot/2.1") is True
    assert service.is_bot("Mozilla/5.0 (Windows NT 10.0; Win64; x64)") is False


def test_is_bot_detects_high_request_rate():
    service = ThreatDetectionService()
    assert service.is_bot("Mozilla/5.0", request_rate_per_minute=500, rate_threshold=300) is True


def test_scan_for_threats_detects_sql_injection():
    service = ThreatDetectionService()
    matches = service.scan_for_threats("id=1 UNION SELECT password FROM users")
    assert matches


def test_scan_for_threats_detects_xss():
    service = ThreatDetectionService()
    matches = service.scan_for_threats("<script>alert(1)</script>")
    assert matches


def test_scan_for_threats_clean_payload_returns_empty():
    service = ThreatDetectionService()
    assert service.scan_for_threats("normal search query about widgets") == []


def test_assert_safe_raises_on_threat():
    service = ThreatDetectionService()
    with pytest.raises(ThreatDetectedError):
        service.assert_safe("'; DROP TABLE users; --")
