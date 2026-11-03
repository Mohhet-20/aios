"""ORM <-> domain-aggregate bridge for `Session`."""
from __future__ import annotations

from identity_platform.domain.entities import Session
from identity_platform.domain.enums import SessionStatus
from identity_platform.models.session import SessionModel


def session_to_domain(model: SessionModel) -> Session:
    return Session(
        id=model.id, user_id=model.user_id, status=SessionStatus(model.status),
        revoked_reason=model.revoked_reason,
    )


def apply_session_domain_to_model(entity: Session, model: SessionModel) -> None:
    model.status = entity.status.value
    model.revoked_reason = entity.revoked_reason
    model.revoked_at = entity.revoked_at
