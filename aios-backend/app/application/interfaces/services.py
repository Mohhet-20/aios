"""Service-level Protocols: the "clear interfaces" the prompt asks each
business service to expose. Concrete implementations live in `app.services`.
Only methods that carry real business meaning are listed explicitly — CRUD
(`get`/`list`/`create`/`update`/`delete`) is inherited from `BaseCRUDService`
and intentionally omitted here to keep each interface focused on what makes
that service distinct.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class IAuthService(Protocol):
    async def register(self, email: str, password: str, full_name: str) -> object: ...
    async def authenticate(self, email: str, password: str) -> object: ...
    async def refresh(self, refresh_token: str) -> tuple[str, str]: ...
    async def revoke_refresh_token(self, jti: str) -> None: ...


@runtime_checkable
class IAgentService(Protocol):
    async def list_by_workspace(self, workspace_id: str) -> list: ...
    async def record_run(self, agent_id: str, success: bool) -> object: ...


@runtime_checkable
class IPromptService(Protocol):
    async def create_version(self, prompt_id: str, content: str, author_id: str) -> object: ...
    async def promote_version(
        self, prompt_id: str, version: int, target_status: str, actor_id: str
    ) -> object: ...
    async def render(self, prompt_id: str, variables: dict) -> str: ...


@runtime_checkable
class IWorkflowService(Protocol):
    async def execute(self, workflow_id: str, input_payload: dict, triggered_by: str) -> object: ...
    async def get_execution(self, execution_id: str) -> object: ...


@runtime_checkable
class IInferenceService(Protocol):
    async def generate(self, model_id: str, messages: list[dict]) -> object: ...
    async def stream(self, model_id: str, messages: list[dict]): ...


@runtime_checkable
class IEvaluationService(Protocol):
    async def run_suite(
        self, workspace_id: str, suite_name: str, target_type: str, target_id: str, dataset_id: str
    ) -> object: ...


@runtime_checkable
class IMemoryService(Protocol):
    async def write(self, workspace_id: str, memory_type: str, scope: str, content: str) -> object: ...
    async def query(
        self, workspace_id: str, query_text: str, memory_type: str | None, top_k: int
    ) -> list: ...


@runtime_checkable
class IEmbeddingService(Protocol):
    async def embed_texts(self, model_id: str, texts: list[str]) -> list[list[float]]: ...


@runtime_checkable
class IVectorService(Protocol):
    async def upsert(self, id: str, vector: list[float], metadata: dict) -> None: ...
    async def search(self, vector: list[float], top_k: int, filters: dict | None) -> list: ...


@runtime_checkable
class INotificationService(Protocol):
    async def notify(
        self, recipient_user_id: str, title: str, description: str, notification_type: str
    ) -> object: ...
    async def mark_all_read(self, user_id: str) -> None: ...


@runtime_checkable
class IAuditService(Protocol):
    async def record(
        self, organization_id: str, actor: str, action: str, resource: str, status: str
    ) -> object: ...


@runtime_checkable
class IPluginService(Protocol):
    async def install(self, organization_id: str, plugin_manifest_id: str) -> object: ...
    async def toggle(self, plugin_id: str, enabled: bool) -> object: ...


@runtime_checkable
class ISearchService(Protocol):
    async def search(self, workspace_id: str, query: str) -> dict: ...


@runtime_checkable
class IConfigurationService(Protocol):
    async def get(self, organization_id: str, key: str, default=None): ...
    async def set(self, organization_id: str, key: str, value) -> object: ...
