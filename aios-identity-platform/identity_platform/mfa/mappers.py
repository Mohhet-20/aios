"""ORM <-> domain-aggregate bridge for `MfaFactor`."""
from __future__ import annotations

from identity_platform.domain.entities import MfaFactor, _aware
from identity_platform.domain.enums import MfaFactorStatus
from identity_platform.models.mfa import MfaFactorModel


def mfa_factor_to_domain(model: MfaFactorModel) -> MfaFactor:
    return MfaFactor(
        id=model.id, user_id=model.user_id, status=MfaFactorStatus(model.status), verified_at=_aware(model.verified_at),
    )


def apply_mfa_factor_domain_to_model(entity: MfaFactor, model: MfaFactorModel) -> None:
    model.status = entity.status.value
    model.verified_at = entity.verified_at
