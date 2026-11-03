"""Extension point registry: the fixed set of 11 places the AI
Operating System lets third-party code attach — agents, prompts,
workflows, memory, tools, models, evaluation, dashboards,
authentication, notifications, and custom UI components. Each point
carries an optional `contract_schema` describing what a registration's
`config` must provide; registration itself is handled by
`registration_service.py`."""
from __future__ import annotations

from developer_platform.config.settings import Settings, get_settings
from developer_platform.core.exceptions import ExtensionPointNotFoundError, ValidationError
from developer_platform.domain.enums import ExtensionCategory
from developer_platform.models.extensions import ExtensionPointModel
from developer_platform.repositories.registry import RepositoryRegistry


class ExtensionPointService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    def _assert_valid_category(self, category: str) -> None:
        if category not in self.settings.extension_point_categories:
            raise ValidationError(
                f"'{category}' is not a registered extension category; valid categories: "
                f"{sorted(self.settings.extension_point_categories)}"
            )

    async def register_point(
        self, tenant_id: str, *, category: str, name: str, description: str | None = None,
        contract_schema: dict | None = None,
    ) -> ExtensionPointModel:
        self._assert_valid_category(category)
        existing = await self.repos.extension_points.get_by_name(tenant_id, category, name)
        if existing is not None:
            return existing
        point = ExtensionPointModel(
            tenant_id=tenant_id, category=category, name=name, description=description,
            contract_schema=contract_schema or {},
        )
        return await self.repos.extension_points.add(point)

    async def get_point(self, tenant_id: str, *, category: str, name: str) -> ExtensionPointModel:
        point = await self.repos.extension_points.get_by_name(tenant_id, category, name)
        if point is None:
            raise ExtensionPointNotFoundError(f"No extension point '{name}' registered under category '{category}'")
        return point

    async def list_by_category(self, tenant_id: str, category: str) -> list[ExtensionPointModel]:
        self._assert_valid_category(category)
        return await self.repos.extension_points.list_by_category(tenant_id, category)

    async def list_all(self, tenant_id: str) -> list[ExtensionPointModel]:
        points: list[ExtensionPointModel] = []
        for category in ExtensionCategory:
            points.extend(await self.repos.extension_points.list_by_category(tenant_id, category.value))
        return points
