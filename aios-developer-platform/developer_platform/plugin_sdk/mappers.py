"""ORM <-> domain-aggregate bridge for `PluginVersion`."""
from __future__ import annotations

from developer_platform.domain.entities import PluginVersion
from developer_platform.domain.enums import PluginVersionStatus
from developer_platform.models.plugins import PluginVersionModel


def plugin_version_to_domain(model: PluginVersionModel) -> PluginVersion:
    return PluginVersion(id=model.id, status=PluginVersionStatus(model.status))


def apply_plugin_version_domain_to_model(entity: PluginVersion, model: PluginVersionModel) -> None:
    model.status = entity.status.value
