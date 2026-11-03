"""Doc page CRUD and editorial lifecycle: create_page() seeds a page
in draft with its own version-1 snapshot, update_content() only
accepts edits while a page is still a draft (a published page is
version-protected — see `docs_platform.security.governance_service`
for the explicit protection check other callers should use before
attempting an edit), and every status transition is driven through the
guarded `DocPage` domain entity."""
from __future__ import annotations


from docs_platform.config.settings import get_settings
from docs_platform.core.exceptions import DocPageNotFoundError, InvalidTransitionError, UnsupportedDocTypeError, ValidationError
from docs_platform.documentation.doc_space_service import DocSpaceService
from docs_platform.domain.entities import DocPage
from docs_platform.domain.enums import DocPageStatus
from docs_platform.models.documentation import DocPageModel
from docs_platform.models.versioning import DocVersionModel
from docs_platform.repositories.registry import RepositoryRegistry
from docs_platform.clock import utc_now


class DocPageService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()
        self.spaces = DocSpaceService(repos)

    async def get_or_404(self, tenant_id: str, page_id: str) -> DocPageModel:
        page = await self.repos.doc_pages.get_or_404(page_id)
        if page.tenant_id != tenant_id:
            raise DocPageNotFoundError(f"Doc page '{page_id}' not found for tenant '{tenant_id}'")
        return page

    async def create_page(
        self, tenant_id: str, space_id: str, *, title: str, slug: str, doc_type: str,
        content: str = "", owner_id: str | None = None, visibility: str | None = None,
    ) -> DocPageModel:
        if doc_type not in self.settings.doc_types:
            raise UnsupportedDocTypeError(f"Unsupported doc type '{doc_type}'")
        await self.spaces.get_or_404(tenant_id, space_id)
        page = DocPageModel(
            tenant_id=tenant_id, space_id=space_id, title=title, slug=slug, doc_type=doc_type,
            content=content, owner_id=owner_id, visibility=visibility or self.settings.doc_page_default_visibility,
            status=DocPageStatus.DRAFT.value, current_version=1,
        )
        page = await self.repos.doc_pages.add(page)
        await self.repos.doc_versions.add(
            DocVersionModel(tenant_id=tenant_id, page_id=page.id, version_number=1, content_snapshot=content, created_by=owner_id)
        )
        return page

    async def update_content(self, tenant_id: str, page_id: str, *, content: str, actor_id: str | None = None) -> DocPageModel:
        page = await self.get_or_404(tenant_id, page_id)
        if page.status != DocPageStatus.DRAFT.value:
            raise ValidationError(f"Doc page '{page_id}' is '{page.status}' — only draft pages accept direct content edits")
        page.content = content
        page.current_version += 1
        page = await self.repos.doc_pages.update(page)
        await self.repos.doc_versions.add(
            DocVersionModel(tenant_id=tenant_id, page_id=page_id, version_number=page.current_version, content_snapshot=content, created_by=actor_id)
        )
        return page

    async def _apply_transition(self, tenant_id: str, page_id: str, transition_name: str) -> DocPageModel:
        page = await self.get_or_404(tenant_id, page_id)
        entity = DocPage(id=page.id, status=DocPageStatus(page.status))
        try:
            getattr(entity, transition_name)()
        except InvalidTransitionError:
            raise
        page.status = entity.status.value
        return page

    async def submit_for_review(self, tenant_id: str, page_id: str) -> DocPageModel:
        page = await self._apply_transition(tenant_id, page_id, "submit_for_review")
        return await self.repos.doc_pages.update(page)

    async def publish(self, tenant_id: str, page_id: str) -> DocPageModel:
        page = await self._apply_transition(tenant_id, page_id, "publish")
        page.last_reviewed_at = utc_now()
        return await self.repos.doc_pages.update(page)

    async def reject(self, tenant_id: str, page_id: str) -> DocPageModel:
        page = await self._apply_transition(tenant_id, page_id, "reject")
        return await self.repos.doc_pages.update(page)

    async def archive(self, tenant_id: str, page_id: str) -> DocPageModel:
        page = await self._apply_transition(tenant_id, page_id, "archive")
        return await self.repos.doc_pages.update(page)

    async def deprecate(self, tenant_id: str, page_id: str) -> DocPageModel:
        page = await self._apply_transition(tenant_id, page_id, "deprecate")
        return await self.repos.doc_pages.update(page)

    async def list_pages(self, tenant_id: str, *, doc_type: str | None = None, status: str | None = None) -> list[DocPageModel]:
        return await self.repos.doc_pages.list_for_tenant(tenant_id, doc_type=doc_type, status=status)

    async def list_for_space(self, tenant_id: str, space_id: str, *, status: str | None = None) -> list[DocPageModel]:
        await self.spaces.get_or_404(tenant_id, space_id)
        return await self.repos.doc_pages.list_for_space(tenant_id, space_id, status=status)
