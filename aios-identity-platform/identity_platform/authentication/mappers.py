"""ORM <-> domain-aggregate bridge for `User` — same pattern as every
other AIOS platform's per-module mapper (e.g. tool_platform's
`credentials/mappers.py`)."""
from __future__ import annotations

from identity_platform.domain.entities import User, _aware
from identity_platform.domain.enums import UserStatus
from identity_platform.models.user import UserModel


def user_to_domain(model: UserModel) -> User:
    return User(
        id=model.id,
        email=model.email,
        status=UserStatus(model.status),
        failed_login_count=model.failed_login_count,
        locked_until=_aware(model.locked_until),
        email_verified_at=_aware(model.email_verified_at),
    )


def apply_user_domain_to_model(entity: User, model: UserModel) -> None:
    model.status = entity.status.value
    model.failed_login_count = entity.failed_login_count
    model.locked_until = entity.locked_until
    model.email_verified_at = entity.email_verified_at
