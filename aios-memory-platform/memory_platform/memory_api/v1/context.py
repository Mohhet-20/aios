"""Context Assembly Engine: the API a caller building a prompt hits to
get a token-budgeted, deduplicated, conflict-resolved, cited context
block assembled from memory + knowledge in one call."""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from memory_platform.context_engine.context_assembly_service import ContextAssemblyService
from memory_platform.memory_api.dependencies import get_context_assembly_service, get_current_actor_id

router = APIRouter(prefix="/workspaces/{workspace_id}/context", tags=["context-assembly"])


class AssembleContextRequest(BaseModel):
    query: str
    scope_type: str | None = None
    scope_id: str | None = None
    memory_type: str | None = None
    candidate_pool_size: int = 20
    token_budget: int | None = None
    use_query_expansion: bool = False
    allow_llm_summarization: bool = True


@router.post("/assemble")
async def assemble_context(workspace_id: str, body: AssembleContextRequest, actor_id: str = Depends(get_current_actor_id), svc: ContextAssemblyService = Depends(get_context_assembly_service)):
    result = await svc.assemble_context(
        workspace_id, body.query, scope_type=body.scope_type, scope_id=body.scope_id, memory_type=body.memory_type,
        candidate_pool_size=body.candidate_pool_size, token_budget=body.token_budget, use_query_expansion=body.use_query_expansion,
        allow_llm_summarization=body.allow_llm_summarization, requested_by=actor_id,
    )
    return asdict(result)
