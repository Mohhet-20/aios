"""Developer Portal content: getting-started guides, docs, tutorials,
quickstarts, release notes, and migration guides all share one model
(`content_type` discriminator) with a guarded draft -> published <->
archived lifecycle and a version counter that increments on every body
edit — a published page's history is inspectable even though this
platform doesn't keep a full diff log, since `version` alone tells a
reader "this is edit #4"."""
from __future__ import annotations

from developer_platform.core.exceptions import NotFoundError, PortalError, ValidationError
from developer_platform.domain.enums import PortalContentStatus, PortalContentType
from developer_platform.models.portal import PortalContentModel
from developer_platform.repositories.registry import RepositoryRegistry

_TRANSITIONS: dict[PortalContentStatus, set[PortalContentStatus]] = {
    PortalContentStatus.DRAFT: {PortalContentStatus.PUBLISHED},
    PortalContentStatus.PUBLISHED: {PortalContentStatus.ARCHIVED},
    PortalContentStatus.ARCHIVED: {PortalContentStatus.PUBLISHED},
}


def _transition(content: PortalContentModel, target: PortalContentStatus) -> None:
    current = PortalContentStatus(content.status)
    if target not in _TRANSITIONS.get(current, set()):
        raise PortalError(f"Portal content '{content.id}' cannot move from {current.value} to {target.value}")
    content.status = target.value


class PortalContentService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    def _assert_valid_type(self, content_type: str) -> None:
        if content_type not in {c.value for c in PortalContentType}:
            raise ValidationError(f"'{content_type}' is not a recognized portal content type")

    async def create_content(
        self, tenant_id: str, *, content_type: str, slug: str, title: str, body: str = "",
    ) -> PortalContentModel:
        self._assert_valid_type(content_type)
        existing = await self.repos.portal_content.get_by_slug(tenant_id, content_type, slug)
        if existing is not None:
            raise ValidationError(f"content with slug '{slug}' already exists under '{content_type}'")
        content = PortalContentModel(
            tenant_id=tenant_id, content_type=content_type, slug=slug, title=title, body=body,
            status=PortalContentStatus.DRAFT.value, version=1,
        )
        return await self.repos.portal_content.add(content)

    async def update_content(self, content_id: str, *, title: str | None = None, body: str | None = None) -> PortalContentModel:
        content = await self._get_or_404(content_id)
        if title is not None:
            content.title = title
        if body is not None and body != content.body:
            content.body = body
            content.version += 1
        return await self.repos.portal_content.update(content)

    async def publish(self, content_id: str) -> PortalContentModel:
        content = await self._get_or_404(content_id)
        _transition(content, PortalContentStatus.PUBLISHED)
        return await self.repos.portal_content.update(content)

    async def archive(self, content_id: str) -> PortalContentModel:
        content = await self._get_or_404(content_id)
        _transition(content, PortalContentStatus.ARCHIVED)
        return await self.repos.portal_content.update(content)

    async def get_by_slug(self, tenant_id: str, content_type: str, slug: str) -> PortalContentModel:
        content = await self.repos.portal_content.get_by_slug(tenant_id, content_type, slug)
        if content is None:
            raise NotFoundError(f"no '{content_type}' content found for slug '{slug}'")
        return content

    async def list_by_type(self, tenant_id: str, content_type: str) -> list[PortalContentModel]:
        self._assert_valid_type(content_type)
        return await self.repos.portal_content.list_by_type(tenant_id, content_type)

    async def list_published(self, tenant_id: str) -> list[PortalContentModel]:
        return await self.repos.portal_content.list_published(tenant_id)

    async def _get_or_404(self, content_id: str) -> PortalContentModel:
        try:
            return await self.repos.portal_content.get_or_404(content_id)
        except NotFoundError as exc:
            raise PortalError(f"Portal content '{content_id}' not found") from exc
