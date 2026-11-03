"""AI Documentation Assistant: retrieval-and-extract question
answering over published pages/KB articles, related-doc suggestions,
troubleshooting lookup, summarization, outdated-page detection, and
templated code-example generation. Deliberately NOT LLM-backed — see
AssistantService's docstring for the disclosed scope boundary; ranked
tuple results are serialized as {"ref": ..., "score": ...} since they
aren't ORM rows."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from docs_platform.assistant.assistant_service import AssistantService
from docs_platform.dependencies.dependencies import get_assistant_service, get_current_tenant_id
from docs_platform.doc_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/assistant", tags=["assistant"])


def _ranked_to_dicts(ranked: list[tuple[str, float]]) -> list[dict]:
    return [{"ref": ref, "score": score} for ref, score in ranked]


class AskRequest(BaseModel):
    question: str
    user_id: str | None = None


@router.post("/ask", status_code=201)
async def ask(
    body: AskRequest, tenant_id: str = Depends(get_current_tenant_id), service: AssistantService = Depends(get_assistant_service),
):
    return to_dict(await service.ask(tenant_id, body.question, user_id=body.user_id))


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str, tenant_id: str = Depends(get_current_tenant_id), service: AssistantService = Depends(get_assistant_service),
):
    return to_dict(await service.get_or_404(tenant_id, session_id))


@router.get("/sessions")
async def list_sessions(
    user_id: str | None = None, limit: int = 50,
    tenant_id: str = Depends(get_current_tenant_id), service: AssistantService = Depends(get_assistant_service),
):
    return to_dict_list(await service.list_sessions(tenant_id, user_id=user_id, limit=limit))


@router.get("/related/{doc_ref:path}")
async def suggest_related(
    doc_ref: str, limit: int = 5, tenant_id: str = Depends(get_current_tenant_id), service: AssistantService = Depends(get_assistant_service),
):
    return _ranked_to_dicts(await service.suggest_related(tenant_id, doc_ref, limit=limit))


@router.get("/troubleshooting")
async def find_troubleshooting(
    query: str, limit: int = 5, tenant_id: str = Depends(get_current_tenant_id), service: AssistantService = Depends(get_assistant_service),
):
    return _ranked_to_dicts(await service.find_troubleshooting(tenant_id, query, limit=limit))


@router.get("/outdated-pages")
async def detect_outdated_pages(
    tenant_id: str = Depends(get_current_tenant_id), service: AssistantService = Depends(get_assistant_service),
):
    return to_dict_list(await service.detect_outdated_pages(tenant_id))


class SummarizeRequest(BaseModel):
    text: str
    max_sentences: int = 3


@router.post("/summarize")
async def summarize(body: SummarizeRequest, service: AssistantService = Depends(get_assistant_service)):
    return {"summary": service.summarize(body.text, max_sentences=body.max_sentences)}


@router.get("/code-example")
async def generate_code_example(sdk_language: str, operation_ref: str, service: AssistantService = Depends(get_assistant_service)):
    return {"code": service.generate_code_example(sdk_language, operation_ref)}
