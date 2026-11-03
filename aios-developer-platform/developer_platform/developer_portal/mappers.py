"""ORM <-> domain-aggregate bridge for `SandboxEnvironment`."""
from __future__ import annotations

from developer_platform.domain.entities import SandboxEnvironment
from developer_platform.domain.enums import SandboxStatus
from developer_platform.models.portal import SandboxEnvironmentModel


def sandbox_to_domain(model: SandboxEnvironmentModel) -> SandboxEnvironment:
    return SandboxEnvironment(id=model.id, status=SandboxStatus(model.status), terminated_at=model.terminated_at)


def apply_sandbox_domain_to_model(entity: SandboxEnvironment, model: SandboxEnvironmentModel) -> None:
    model.status = entity.status.value
    model.terminated_at = entity.terminated_at
