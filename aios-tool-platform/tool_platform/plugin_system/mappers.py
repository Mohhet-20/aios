"""ORM <-> domain-aggregate bridge for PluginInstallation."""
from __future__ import annotations

from tool_platform.domain.entities import PluginInstallation
from tool_platform.domain.enums import PluginInstallationStatus
from tool_platform.models.plugin import PluginInstallationModel


def installation_to_domain(model: PluginInstallationModel) -> PluginInstallation:
    return PluginInstallation(
        id=model.id, plugin_id=model.plugin_id, workspace_id=model.workspace_id,
        installed_version=model.installed_version, installed_by=model.installed_by,
        status=PluginInstallationStatus(model.status), configuration=dict(model.configuration or {}),
    )


def apply_installation_domain_to_model(entity: PluginInstallation, model: PluginInstallationModel) -> None:
    model.status = entity.status.value
    model.installed_version = entity.installed_version
    model.configuration = entity.configuration
