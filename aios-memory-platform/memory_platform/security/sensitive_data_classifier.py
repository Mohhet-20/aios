"""Regex-based sensitive-data detection — real, useful, false-positive-
tolerant heuristics (the same category of tool Phase 5's prompt-security
layer used for secret detection), not a trained PII classifier. Flags
content for a `SensitivityLevel` and a list of concrete findings so a
caller (or a human reviewer) can see exactly what triggered it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from memory_platform.domain.enums import SensitivityLevel

_PATTERNS: dict[str, re.Pattern] = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "generic_api_key": re.compile(r"\b(?:api[_-]?key|secret[_-]?key|token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}['\"]?", re.IGNORECASE),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    "private_key_block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----"),
    "phone_number": re.compile(r"\b(?:\+?\d{1,2}[ .-]?)?\(?\d{3}\)?[ .-]?\d{3}[ .-]?\d{4}\b"),
}

_HIGH_SEVERITY_TYPES = {"ssn", "credit_card", "aws_access_key", "generic_api_key", "jwt", "private_key_block"}


@dataclass
class ClassificationFinding:
    finding_type: str
    match_preview: str


@dataclass
class SensitivityClassification:
    level: SensitivityLevel
    findings: list[ClassificationFinding] = field(default_factory=list)


def classify_sensitivity(text: str) -> SensitivityClassification:
    if not text:
        return SensitivityClassification(level=SensitivityLevel.PUBLIC)

    findings: list[ClassificationFinding] = []
    for finding_type, pattern in _PATTERNS.items():
        for match in pattern.finditer(text):
            preview = match.group(0)
            if len(preview) > 12:
                preview = preview[:4] + "…" + preview[-4:]
            findings.append(ClassificationFinding(finding_type=finding_type, match_preview=preview))

    if any(f.finding_type in _HIGH_SEVERITY_TYPES for f in findings):
        level = SensitivityLevel.RESTRICTED
    elif findings:
        level = SensitivityLevel.CONFIDENTIAL
    else:
        level = SensitivityLevel.INTERNAL
    return SensitivityClassification(level=level, findings=findings)
