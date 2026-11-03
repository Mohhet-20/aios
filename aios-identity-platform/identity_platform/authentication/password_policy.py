"""Password strength validation, driven entirely by `Settings` fields
(`password_min_length`/`password_require_*`) so tightening the policy
never requires a code change."""
from __future__ import annotations

from identity_platform.config.settings import Settings
from identity_platform.core.exceptions import PasswordPolicyError


def validate_password_strength(raw_password: str, *, settings: Settings) -> None:
    problems: list[str] = []
    if len(raw_password) < settings.password_min_length:
        problems.append(f"must be at least {settings.password_min_length} characters")
    if settings.password_require_uppercase and not any(c.isupper() for c in raw_password):
        problems.append("must contain an uppercase letter")
    if settings.password_require_lowercase and not any(c.islower() for c in raw_password):
        problems.append("must contain a lowercase letter")
    if settings.password_require_digit and not any(c.isdigit() for c in raw_password):
        problems.append("must contain a digit")
    if settings.password_require_symbol and not any(not c.isalnum() for c in raw_password):
        problems.append("must contain a symbol")
    if problems:
        raise PasswordPolicyError("Password does not meet policy: " + "; ".join(problems))
