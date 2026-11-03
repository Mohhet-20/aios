"""WorkflowService: identity/ownership/lifecycle CRUD for the top-level
`WorkflowModel` record. Editing the actual graph (nodes/edges) lives in
`version_service.py` — this service only ever touches identity fields
and drives the `Workflow` domain entity's lifecycle transitions."""
from __future__ import annotations

from slugify import slugify

from workflow_platform.core.exceptions import ValidationError
from workflow_platform.core.pagination import Page, PaginationParams
from workflow_platform.models.workflow import WorkflowModel
from workflow_platform.repositories.registry import RepositoryRegistry
from workflow_platform.workflow_core.mappers import apply_workflow_domain_to_model, workflow_to_domain


class WorkflowService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_workflow(
        self, workspace_id: str, *, name: str, owner_id: str, category: str, slug: str | None = None,
        description: str | None = None, tags: list[str] | None = None, priority: str = "normal",
        variables: dict | None = None, workflow_metadata: dict | None = None,
    ) -> WorkflowModel:
        resolved_slug = slug or slugify(name)
        existing = await self.repos.workflows.get_by_slug(workspace_id, resolved_slug)
        if existing is not None:
            raise ValidationError(f"a workflow with slug '{resolved_slug}' already exists in this workspace")

        return await self.repos.workflows.add(WorkflowModel(
            workspace_id=workspace_id, name=name, slug=resolved_slug, description=description, owner_id=owner_id,
            category=category, tags=tags or [], priority=priority, variables=variables or {},
            workflow_metadata=workflow_metadata or {},
        ))

    async def get_workflow(self, workflow_id: str) -> WorkflowModel:
        return await self.repos.workflows.get_or_404(workflow_id)

    async def list_workflows(
        self, workspace_id: str, params: PaginationParams, *, status: str | None = None, category: str | None = None
    ) -> Page[WorkflowModel]:
        filters: dict = {"workspace_id": workspace_id}
        if status:
            filters["status"] = status
        if category:
            filters["category"] = category
        return await self.repos.workflows.paginated_list(params, filters=filters)

    async def search_workflows(self, workspace_id: str, query: str) -> list[WorkflowModel]:
        return await self.repos.workflows.search(workspace_id, query)

    async def update_workflow(self, workflow_id: str, **fields) -> WorkflowModel:
        workflow = await self.repos.workflows.get_or_404(workflow_id)
        allowed = {"name", "description", "tags", "priority", "variables", "workflow_metadata", "category"}
        unknown = set(fields) - allowed
        if unknown:
            raise ValidationError(f"cannot update fields: {sorted(unknown)}")
        for key, value in fields.items():
            setattr(workflow, key, value)
        return await self.repos.workflows.update(workflow)

    async def delete_workflow(self, workflow_id: str) -> None:
        workflow = await self.repos.workflows.get_or_404(workflow_id)
        await self.repos.workflows.delete(workflow)

    # -- lifecycle ------------------------------------------------------------

    async def publish(self, workflow_id: str, version_id: str) -> WorkflowModel:
        model = await self.repos.workflows.get_or_404(workflow_id)
        entity = workflow_to_domain(model)
        entity.publish(version_id)
        apply_workflow_domain_to_model(entity, model)
        return await self.repos.workflows.update(model)

    async def pause(self, workflow_id: str) -> WorkflowModel:
        return await self._apply_transition(workflow_id, "pause")

    async def resume(self, workflow_id: str) -> WorkflowModel:
        return await self._apply_transition(workflow_id, "resume")

    async def deprecate(self, workflow_id: str) -> WorkflowModel:
        return await self._apply_transition(workflow_id, "deprecate")

    async def archive(self, workflow_id: str) -> WorkflowModel:
        return await self._apply_transition(workflow_id, "archive")

    async def _apply_transition(self, workflow_id: str, transition: str) -> WorkflowModel:
        model = await self.repos.workflows.get_or_404(workflow_id)
        entity = workflow_to_domain(model)
        getattr(entity, transition)()
        apply_workflow_domain_to_model(entity, model)
        return await self.repos.workflows.update(model)
