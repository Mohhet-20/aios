"""PII detection via well-established regex patterns. Honestly scoped:
EMAIL, PHONE, SSN, CREDIT_CARD, and IP_ADDRESS have reliable regex
signatures and are detected here. NAME, ADDRESS, PASSPORT,
BANK_ACCOUNT, and MEDICAL_RECORD do not have reliable regex
signatures — accurately finding a name or address in free text needs a
trained NER model, which is out of scope for this heuristic layer.
Those entity types remain first-class in `PiiEntityType` (for manual
tagging and classification workflows) but are not auto-detected here.
This mirrors the disclosed-gap pattern used for guardrail detectors:
a real, working first line of defense, not a claim of ML-grade
coverage."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from security_platform.domain.enums import PiiEntityType

_PATTERNS: dict[PiiEntityType, re.Pattern] = {
    PiiEntityType.EMAIL: re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    PiiEntityType.PHONE: re.compile(r"(?<!\d)(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}(?!\d)"),
    PiiEntityType.SSN: re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)"),
    PiiEntityType.CREDIT_CARD: re.compile(r"(?<!\d)(?:\d[ -]?){13,16}(?!\d)"),
    PiiEntityType.IP_ADDRESS: re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"),
}

# Rough severity/sensitivity ranking for detected entity types — used by
# the DLP engine to decide which policies a finding should trigger.
ENTITY_SENSITIVITY: dict[PiiEntityType, str] = {
    PiiEntityType.EMAIL: "internal",
    PiiEntityType.PHONE: "internal",
    PiiEntityType.IP_ADDRESS: "internal",
    PiiEntityType.DATE_OF_BIRTH: "confidential",
    PiiEntityType.NAME: "internal",
    PiiEntityType.ADDRESS: "internal",
    PiiEntityType.SSN: "restricted",
    PiiEntityType.CREDIT_CARD: "restricted",
    PiiEntityType.PASSPORT: "restricted",
    PiiEntityType.BANK_ACCOUNT: "restricted",
    PiiEntityType.MEDICAL_RECORD: "restricted",
    PiiEntityType.CUSTOM: "confidential",
}


def _luhn_valid(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


@dataclass
class PiiMatch:
    entity_type: PiiEntityType
    value: str
    start: int
    end: int


def hash_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def mask_value(value: str, entity_type: PiiEntityType) -> str:
    """Partial masking: keep a short recognizable suffix for
    card/account-like numbers (common UX pattern — "ends in 1234"),
    full redaction otherwise."""
    digits_only = re.sub(r"\D", "", value)
    if entity_type in (PiiEntityType.CREDIT_CARD, PiiEntityType.SSN, PiiEntityType.BANK_ACCOUNT) and len(digits_only) >= 4:
        return f"***{digits_only[-4:]}"
    if entity_type == PiiEntityType.EMAIL and "@" in value:
        local, _, domain = value.partition("@")
        return f"{local[:1]}***@{domain}"
    return "***"


def detect_pii(text: str) -> list[PiiMatch]:
    matches: list[PiiMatch] = []
    for entity_type, pattern in _PATTERNS.items():
        for m in pattern.finditer(text):
            value = m.group(0)
            if entity_type == PiiEntityType.CREDIT_CARD:
                digits = re.sub(r"[ -]", "", value)
                if not (13 <= len(digits) <= 16) or not _luhn_valid(digits):
                    continue
            matches.append(PiiMatch(entity_type=entity_type, value=value, start=m.start(), end=m.end()))
    matches.sort(key=lambda m: m.start)
    return matches


def redact_pii(text: str, matches: list[PiiMatch] | None = None) -> str:
    matches = matches if matches is not None else detect_pii(text)
    if not matches:
        return text
    out = []
    cursor = 0
    for m in sorted(matches, key=lambda m: m.start):
        if m.start < cursor:
            continue  # overlapping match already covered
        out.append(text[cursor:m.start])
        out.append(f"[{m.entity_type.value.upper()}]")
        cursor = m.end
    out.append(text[cursor:])
    return "".join(out)
