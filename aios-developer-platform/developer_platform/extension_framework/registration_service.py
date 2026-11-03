"""Extension registration lifecycle: registered -> active <-> disabled.
A simple field-based transition guarded directly here rather than
through a dedicated domain entity — the same "simpler status fields
guarded in-service" precedent used for CLI sessions and (in the prior
Infrastructure Platform) node pools and deployment gates. Config
validation against the extension point's `contract_schema` happens at
registration time so a broken registration is never persisted."""
from __future__ import annotations

from developer_platform.core.exceptions import ExtensionRegistrationError
from developer_platform.domain.enums import ExtensionRegistrationStatus
from developer_platform.models.extensions import ExtensionRegistrationModel
from developer_platform.repositories.registry import RepositoryRegistry

_TRANSITIONS: dict[ExtensionRegistrationStatus, set[ExtensionRegistrationStatus]] = {
    ExtensionRegistrationStatus.REGISTERED: {ExtensionRegistrationStatus.ACTIVE, ExtensionRegistrationStatus.DISABLED},
    ExtensionRegistrationStatus.ACTIVE: {ExtensionRegistrationStatus.DISABLED},
    ExtensionRegistrationStatus.DISABLED: {ExtensionRegistrationStatus.ACTIVE},
}


def _transition(registration: ExtensionRegistrationModel, target: ExtensionRegistrationStatus) -> None:
    current = ExtensionRegistrationStatus(registration.status)
    if target not in _TRANSITIONS.get(current, set()):
        raise ExtensionRegistrationError(
            f"Extension registration '{registration.id}' cannot move from {current.value} to {target.value}"
        )
    registration.status = target.value


def _validate_config(contract_schema: dict, config: dict) -> None:
    required = contract_schema.get("required", [])
    missing = [key for key in required if key not in config]
    if missing:
        raise ExtensionRegistrationError(f"registration config is missing required key(s): {missing}")


class ExtensionRegistrationService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def register(
        self, tenant_id: str, *, extension_point_id: str, name: str, plugin_id: str | None = None,
        config: dict | None = None,
    ) -> ExtensionRegistrationModel:
        point = await self.repos.extension_points.get_or_404(extension_point_id)
        config = config or {}
        _validate_config(point.contract_schema or {}, config)

        registration = ExtensionRegistrationModel(
            tenant_id=tenant_id, extension_point_id=extension_point_id, plugin_id=plugin_id, name=name,
            status=ExtensionRegistrationStatus.REGISTERED.value, config=config,
        )
        return await self.repos.extension_registrations.add(registration)

    async def activate(self, registration_id: str) -> ExtensionRegistrationModel:
        registration = await self.repos.extension_registrations.get_or_404(registration_id)
        _transition(registration, ExtensionRegistrationStatus.ACTIVE)
        return await self.repos.extension_registrations.update(registration)

    async def disable(self, registration_id: str) -> ExtensionRegistrationModel:
        registration = await self.repos.extension_registrations.get_or_404(registration_id)
        _transition(registration, ExtensionRegistrationStatus.DISABLED)
        return await self.repos.extension_registrations.update(registration)

    async def list_for_point(self, tenant_id: str, extension_point_id: str) -> list[ExtensionRegistrationModel]:
        return await self.repos.extension_registrations.list_for_point(tenant_id, extension_point_id)

    async def list_for_plugin(self, tenant_id: str, plugin_id: str) -> list[ExtensionRegistrationModel]:
        return await self.repos.extension_registrations.list_for_plugin(tenant_id, plugin_id)
