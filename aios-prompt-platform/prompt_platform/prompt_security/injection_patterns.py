"""Regex-based signal libraries for prompt-injection detection and secret
scanning. Deliberately heuristic (not a classifier) — false positives are
acceptable (they surface as warnings, not hard failures, for injection
patterns) but false negatives on hardcoded secrets are not, which is why
secret detection is treated as a hard-fail elsewhere in security_service.
"""
from __future__ import annotations

import re

# Phrases commonly used to try to override a system prompt or exfiltrate
# instructions. Matched case-insensitively against prompt template text
# AND model output (a template containing these is a red flag it was
# copy-pasted from a jailbreak writeup; a *response* containing these
# suggests the model complied with an injected instruction).
INJECTION_PATTERNS: dict[str, re.Pattern] = {
    "ignore_previous_instructions": re.compile(r"ignore (all |any )?(previous|prior|above) instructions", re.IGNORECASE),
    "disregard_instructions": re.compile(r"disregard (all |any )?(previous|prior|above|the) (instructions|rules|prompt)", re.IGNORECASE),
    "reveal_system_prompt": re.compile(r"(reveal|print|show|repeat|output) (your |the )?(system prompt|instructions|hidden prompt)", re.IGNORECASE),
    "role_override": re.compile(r"you are now (a|an)\b", re.IGNORECASE),
    "developer_mode": re.compile(r"\b(dan mode|developer mode|jailbreak)\b", re.IGNORECASE),
    "pretend_no_restrictions": re.compile(r"pretend (you have |there are )?no (restrictions|rules|guidelines)", re.IGNORECASE),
}

# Secret-shaped substrings. Every entry captures the FULL matched secret in
# group 0 so it can be redacted; callers should never persist or log the
# raw match, only its type and a truncated preview.
SECRET_PATTERNS: dict[str, re.Pattern] = {
    "openai_api_key": re.compile(r"sk-[A-Za-z0-9]{20,}"),
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "generic_bearer_token": re.compile(r"Bearer [A-Za-z0-9\-_.]{20,}"),
    "jwt": re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
    "private_key_block": re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "hardcoded_password_assignment": re.compile(r"\bpassword\s*[:=]\s*['\"]?[^\s'\"]{6,}", re.IGNORECASE),
}


def find_injection_matches(text: str) -> list[str]:
    if not text:
        return []
    return [name for name, pattern in INJECTION_PATTERNS.items() if pattern.search(text)]


def find_secret_matches(text: str) -> list[tuple[str, str]]:
    """Returns (secret_type, matched_text) pairs. Callers must redact
    `matched_text` before it touches a log line, error message, or
    anything else that might persist or display it."""
    if not text:
        return []
    matches = []
    for name, pattern in SECRET_PATTERNS.items():
        for m in pattern.finditer(text):
            matches.append((name, m.group(0)))
    return matches


def redact(text: str) -> str:
    """Replaces every detected secret substring with a type-tagged
    placeholder, leaving the rest of the text intact."""
    if not text:
        return text
    redacted = text
    for name, pattern in SECRET_PATTERNS.items():
        redacted = pattern.sub(f"[REDACTED:{name}]", redacted)
    return redacted
