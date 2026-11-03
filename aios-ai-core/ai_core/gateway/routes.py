"""HTTP surface for the AI Core / LLM Gateway. Every route is a thin
wrapper over the same engines a Python caller would use directly —
`ExecutionEngine`, `EmbeddingEngine`, `ModelRegistry`, `UsageTracker` — so
the gateway can't drift from in-process behavior. This is the boundary
non-Python services (or Python services that prefer a network hop over an
in-process import) use instead of ever talking to a provider directly.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from ai_core.bootstrap import AICoreContext
from ai_core.gateway.dependencies import get_context
from ai_core.schemas.requests import EmbeddingRequest, GenerationRequest
from ai_core.schemas.responses import EmbeddingResponse, GenerationResponse
from ai_core.utils.exceptions import ModelNotFoundError

router = APIRouter()


@router.post("/generate", response_model=GenerationResponse)
async def generate(request: GenerationRequest, ctx: AICoreContext = Depends(get_context)) -> GenerationResponse:
    return await ctx.execution_engine.generate(request)


@router.post("/generate/stream")
async def generate_stream(request: GenerationRequest, ctx: AICoreContext = Depends(get_context)) -> EventSourceResponse:
    request = request.model_copy(update={"stream": True})

    async def _event_source():
        async for chunk in ctx.execution_engine.stream(request):
            yield {"event": "chunk", "data": chunk.model_dump_json()}
        yield {"event": "done", "data": "{}"}

    return EventSourceResponse(_event_source())


@router.post("/embeddings", response_model=EmbeddingResponse)
async def embeddings(request: EmbeddingRequest, ctx: AICoreContext = Depends(get_context)) -> EmbeddingResponse:
    return await ctx.embedding_engine.embed(request)


@router.get("/models")
async def list_models(ctx: AICoreContext = Depends(get_context)) -> list[dict]:
    return [json.loads(m.model_dump_json()) for m in ctx.registry.all()]


@router.get("/models/{provider}/{name}")
async def get_model(provider: str, name: str, ctx: AICoreContext = Depends(get_context)) -> dict:
    try:
        model = ctx.registry.get(provider, name)
    except ModelNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return json.loads(model.model_dump_json())


@router.post("/models/{provider}/{name}/health")
async def check_model_health(provider: str, name: str, ctx: AICoreContext = Depends(get_context)) -> dict:
    if provider not in ctx.execution_engine.providers:
        raise HTTPException(status_code=404, detail=f"no provider adapter registered for '{provider}'")
    healthy = await ctx.execution_engine.providers[provider].health_check()
    return {"provider": provider, "healthy": healthy}


@router.get("/tools")
async def list_tools(ctx: AICoreContext = Depends(get_context)) -> list[dict]:
    return [json.loads(t.model_dump_json()) for t in ctx.tool_registry.definitions()]


@router.get("/usage")
async def get_usage(
    scope: str = "global", period: str = "day", ctx: AICoreContext = Depends(get_context)
) -> dict:
    summary = ctx.usage_tracker.get_usage(scope=scope, period=period)
    if summary is None:
        return {"scope": scope, "period": period, "request_count": 0, "input_tokens": 0, "output_tokens": 0, "total_cost_usd": 0.0}
    return {
        "scope": summary.scope, "period": summary.period, "period_key": summary.period_key,
        "input_tokens": summary.input_tokens, "output_tokens": summary.output_tokens,
        "cached_tokens": summary.cached_tokens, "total_cost_usd": summary.total_cost_usd,
        "request_count": summary.request_count,
    }
