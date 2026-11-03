"""Lightweight bot and threat detection: real (if deliberately simple)
heuristics rather than a stub -- a known-bot user-agent substring
list, a request-rate threshold for bot suspicion, and a small
signature list for common injection patterns (SQL injection, XSS)
scanned against request payload text. This is the same disclosed
boundary this platform draws elsewhere (e.g. `SchemaValidationService`'s
JSON-Schema subset): genuinely functioning detection for the cases
listed, not a full WAF or ML-based classifier."""
from __future__ import annotations

import re

from gateway_platform.core.exceptions import ThreatDetectedError

_BOT_USER_AGENT_MARKERS = (
    "bot", "crawler", "spider", "scraper", "curl", "wget", "python-requests", "headlesschrome",
)

_INJECTION_PATTERNS = (
    re.compile(r"(?i)\bunion\b.+\bselect\b"),
    re.compile(r"(?i)\bor\b\s+['\"]?1['\"]?\s*=\s*['\"]?1['\"]?"),
    re.compile(r"(?i)<script[\s>]"),
    re.compile(r"(?i)javascript\s*:"),
    re.compile(r"(?i);\s*drop\s+table\b"),
)


class ThreatDetectionService:
    def is_bot(self, user_agent: str | None, *, request_rate_per_minute: float = 0.0, rate_threshold: float = 300.0) -> bool:
        if user_agent:
            lowered = user_agent.lower()
            if any(marker in lowered for marker in _BOT_USER_AGENT_MARKERS):
                return True
        return request_rate_per_minute >= rate_threshold

    def scan_for_threats(self, text: str) -> list[str]:
        """Returns the list of matched pattern descriptions; empty if clean."""
        matches = []
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(text):
                matches.append(pattern.pattern)
        return matches

    def assert_safe(self, text: str) -> None:
        matches = self.scan_for_threats(text)
        if matches:
            raise ThreatDetectedError(f"potential threat detected in payload (matched {len(matches)} signature(s))")
