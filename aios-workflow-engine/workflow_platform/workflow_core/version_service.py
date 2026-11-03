"""WorkflowVersionService: manages the actual graph (nodes + edges) for
one workflow, versioned. Editing always creates or updates a DRAFT
version — a PUBLISHED version is immutable, so an in-flight `Execution`
that captured `workflow_version_id` at start time keeps running against
the exact graph it started with even if a newer version gets published
mid-flight. `publish_version` is the one place graph correctness
(exactly one START, at least one END, no dangling edges, no illegal
cycles, full reachability from START) gets enforced."""
from __future__ import annotations

from workflow_platform.core.exceptions import ValidationError
from workflow_platform.models.node import WorkflowEdgeModel, WorkflowNodeModel
from workflow_platform.models.workflow import WorkflowVersionModel
from workflow_platform.repositories.registry import RepositoryRegistry
from workflow_platform.workflow_core.graph_validator import GraphEdge, GraphNode, validate_graph
from workflow_platform.workflow_core.workflow_service import WorkflowService


class WorkflowVersionService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.workflows = WorkflowService(repos)

    async def get_or_create_draft(self, workflow_id: str, *, created_by: str) -> WorkflowVersionModel:
        """Returns the existing draft version for this workflow, or creates
        a new one seeded from the current published version's graph (or
        empty, if this is the workflow's first version ever)."""
        draft = await self.repos.workflow_versions.get_draft_version(workflow_id)
        if draft is not None:
            return draft

        next_number = await self.repos.workflow_versions.get_latest_version_number(workflow_id) + 1
        new_version = await self.repos.workflow_versions.add(WorkflowVersionModel(
            workflow_id=workflow_id, version_number=next_number, status="draft", created_by=created_by,
        ))

        workflow = await self.repos.workflows.get_or_404(workflow_id)
        if workflow.current_version_id:
            source_nodes = await self.repos.workflow_nodes.list_for_version(workflow.current_version_id)
            source_edges = await self.repos.workflow_edges.list_for_version(workflow.current_version_id)
            for n in source_nodes:
                await self.repos.workflow_nodes.add(WorkflowNodeModel(
                    workflow_version_id=new_version.id, node_key=n.node_key, node_type=n.node_type, name=n.name,
                    config=dict(n.config), position=dict(n.position), timeout_seconds=n.timeout_seconds, max_retries=n.max_retries,
                ))
            for e in source_edges:
                await self.repos.workflow_edges.add(WorkflowEdgeModel(
                    workflow_version_id=new_version.id, source_node_key=e.source_node_key, target_node_key=e.target_node_key,
                    condition=e.condition, edge_metadata=dict(e.edge_metadata),
                ))
        return new_version

    async def list_versions(self, workflow_id: str) -> list[WorkflowVersionModel]:
        return await self.repos.workflow_versions.list_for_workflow(workflow_id)

    async def get_version(self, version_id: str) -> WorkflowVersionModel:
        return await self.repos.workflow_versions.get_or_404(version_id)

    async def get_graph(self, version_id: str) -> tuple[list[WorkflowNodeModel], list[WorkflowEdgeModel]]:
        nodes = await self.repos.workflow_nodes.list_for_version(version_id)
        edges = await self.repos.workflow_edges.list_for_version(version_id)
        return nodes, edges

    # -- graph mutation (only legal against a DRAFT version) -------------------

    async def _require_draft(self, version_id: str) -> WorkflowVersionModel:
        version = await self.repos.workflow_versions.get_or_404(version_id)
        if version.status != "draft":
            raise ValidationError(f"workflow version '{version_id}' is {version.status}, not draft — cannot edit")
        return version

    async def add_node(
        self, version_id: str, *, node_key: str, node_type: str, name: str, config: dict | None = None,
        position: dict | None = None, timeout_seconds: int | None = None, max_retries: int | None = None,
    ) -> WorkflowNodeModel:
        await self._require_draft(version_id)
        existing = await self.repos.workflow_nodes.get_by_key(version_id, node_key)
        if existing is not None:
            raise ValidationError(f"node key '{node_key}' already exists in version '{version_id}'")
        return await self.repos.workflow_nodes.add(WorkflowNodeModel(
            workflow_version_id=version_id, node_key=node_key, node_type=node_type, name=name,
            config=config or {}, position=position or {}, timeout_seconds=timeout_seconds, max_retries=max_retries,
        ))

    async def remove_node(self, version_id: str, node_key: str) -> None:
        await self._require_draft(version_id)
        node = await self.repos.workflow_nodes.get_by_key(version_id, node_key)
        if node is None:
            raise ValidationError(f"node key '{node_key}' not found in version '{version_id}'")
        edges = await self.repos.workflow_edges.list_for_version(version_id)
        for e in edges:
            if e.source_node_key == node_key or e.target_node_key == node_key:
                await self.repos.workflow_edges.delete(e, hard=True)
        await self.repos.workflow_nodes.delete(node, hard=True)

    async def add_edge(
        self, version_id: str, *, source_node_key: str, target_node_key: str, condition: dict | None = None,
        edge_metadata: dict | None = None,
    ) -> WorkflowEdgeModel:
        await self._require_draft(version_id)
        return await self.repos.workflow_edges.add(WorkflowEdgeModel(
            workflow_version_id=version_id, source_node_key=source_node_key, target_node_key=target_node_key,
            condition=condition, edge_metadata=edge_metadata or {},
        ))

    async def remove_edge(self, edge_id: str) -> None:
        edge = await self.repos.workflow_edges.get_or_404(edge_id)
        await self._require_draft(edge.workflow_version_id)
        await self.repos.workflow_edges.delete(edge, hard=True)

    async def replace_graph(self, version_id: str, *, nodes: list[dict], edges: list[dict]) -> None:
        """Bulk-replace the entire graph for a draft version — used by the
        Workflow Builder frontend's save action and by template instantiation."""
        await self._require_draft(version_id)
        for n in await self.repos.workflow_nodes.list_for_version(version_id):
            await self.repos.workflow_nodes.delete(n, hard=True)
        for e in await self.repos.workflow_edges.list_for_version(version_id):
            await self.repos.workflow_edges.delete(e, hard=True)
        for n in nodes:
            await self.repos.workflow_nodes.add(WorkflowNodeModel(workflow_version_id=version_id, **n))
        for e in edges:
            await self.repos.workflow_edges.add(WorkflowEdgeModel(workflow_version_id=version_id, **e))

    # -- publishing --------------------------------------------------------------

    async def publish_version(self, version_id: str, *, activate_workflow: bool = True) -> WorkflowVersionModel:
        version = await self._require_draft(version_id)
        nodes, edges = await self.get_graph(version_id)

        validate_graph(
            [GraphNode(n.node_key, n.node_type) for n in nodes],
            [GraphEdge(e.source_node_key, e.target_node_key) for e in edges],
        )

        version.status = "published"
        version = await self.repos.workflow_versions.update(version)

        if activate_workflow:
            await self.workflows.publish(version.workflow_id, version.id)

        return version

    async def deprecate_version(self, version_id: str) -> WorkflowVersionModel:
        version = await self.repos.workflow_versions.get_or_404(version_id)
        if version.status != "published":
            raise ValidationError(f"only a published version can be deprecated (status: {version.status})")
        version.status = "deprecated"
        return await self.repos.workflow_versions.update(version)
