"""Prompt Security: injection-resistance scanning, secret detection and
redaction, variable/template validation, input sanitization, output
validation, and role-restriction enforcement. Complements
prompt_governance (which handles RBAC/access-grant resolution) — this
module is about the *content* flowing through a prompt (templates,
variables, model output), not who is allowed to touch it.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from prompt_platform.core.exceptions import SecurityViolationError, ValidationError
from prompt_platform.domain.enums import Role
from prompt_platform.prompt_security.injection_patterns import (
    INJECTION_PATTERNS,
    find_injection_matches,
    find_secret_matches,
    redact,
)

# Ascending order of privilege — used only for the coarse "does this role
# meet a minimum bar" check; fine-grained access still goes through
# prompt_governance's permission-grant resolution.
_ROLE_ORDER = [Role.VIEWER, Role.REVIEWER, Role.EDITOR, Role.ADMIN, Role.OWNER]

# A variable value longer than this is treated as a possible payload-
# stuffing attempt (trying to bury an injection deep in a huge blob) and
# gets truncated before it's rendered into a template.
MAX_VARIABLE_VALUE_CHARS = 10_000


@dataclass
class SecurityScanReport:
    injection_matches: list[str] = field(default_factory=list)
    secret_matches: list[str] = field(default_factory=list)  # secret TYPES only, never raw values
    is_safe: bool = True

    @property
    def has_secrets(self) -> bool:
        return bool(self.secret_matches)

    @property
    def has_injection_risk(self) -> bool:
        return bool(self.injection_matches)


def scan_text(text: str | None) -> SecurityScanReport:
    if not text:
        return SecurityScanReport()
    injection = find_injection_matches(text)
    secrets = [name for name, _ in find_secret_matches(text)]
    return SecurityScanReport(injection_matches=injection, secret_matches=secrets, is_safe=not secrets)


def scan_prompt_version(version) -> SecurityScanReport:
    """Scans every template field on a version (system/developer/user)
    and merges the findings into one report."""
    combined = SecurityScanReport()
    for text in (version.system_template, version.developer_template, version.user_template):
        report = scan_text(text)
        combined.injection_matches.extend(m for m in report.injection_matches if m not in combined.injection_matches)
        combined.secret_matches.extend(m for m in report.secret_matches if m not in combined.secret_matches)
    combined.is_safe = not combined.secret_matches
    return combined


class SecurityService:
    def __init__(self, *, max_variable_value_chars: int = MAX_VARIABLE_VALUE_CHARS, injection_scan_enabled: bool = True):
        self.max_variable_value_chars = max_variable_value_chars
        self.injection_scan_enabled = injection_scan_enabled

    # -- template validation (pre-save) -------------------------------------------

    def scan_version_or_raise(self, version) -> SecurityScanReport:
        """Hard-fails on hardcoded secrets — a template should never ship
        with a literal API key/password/private key baked in; those
        belong in DeploymentEnvironmentConfigModel, not template text.
        Injection-pattern matches are returned as warnings, not raised,
        since they have real false-positive potential (a prompt *about*
        prompt injection will legitimately contain these phrases)."""
        report = scan_prompt_version(version)
        if report.has_secrets:
            raise SecurityViolationError(
                f"Template contains what looks like hardcoded secret(s): {', '.join(report.secret_matches)}. "
                "Move secrets to environment config instead of embedding them in template text."
            )
        return report

    # -- input sanitization ---------------------------------------------------------

    def sanitize_variables(self, variables: dict) -> dict:
        """Truncates oversized values and strips known injection phrases
        out of user-supplied variable values before they're interpolated
        into a rendered prompt. Non-string values pass through untouched."""
        sanitized: dict = {}
        for key, value in (variables or {}).items():
            if isinstance(value, str):
                truncated = value[: self.max_variable_value_chars]
                if self.injection_scan_enabled:
                    for pattern in INJECTION_PATTERNS.values():
                        truncated = pattern.sub("[filtered]", truncated)
                sanitized[key] = truncated
            else:
                sanitized[key] = value
        return sanitized

    # -- output validation ------------------------------------------------------------

    def validate_output(self, response_text: str) -> SecurityScanReport:
        """Post-execution safety net: flags a model response that appears
        to have leaked a secret (e.g. echoed something from context that
        looked like an API key) so callers can redact before storing/
        displaying it. Does not raise — callers decide whether to block,
        redact, or just log a warning for a given surface."""
        return scan_text(response_text)

    def redact_for_storage(self, text: str) -> str:
        return redact(text)

    # -- role restrictions ---------------------------------------------------------

    def enforce_minimum_role(self, actor_role: Role | None, minimum_role: Role) -> None:
        if actor_role is None or _ROLE_ORDER.index(actor_role) < _ROLE_ORDER.index(minimum_role):
            raise ValidationError(f"Action requires at least role '{minimum_role.value}', actor has '{actor_role.value if actor_role else None}'")

