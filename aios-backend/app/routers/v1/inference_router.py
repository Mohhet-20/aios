"""Inference endpoints: a synchronous call, an SSE streaming call, and a
WebSocket for bidirectional streaming — the "Streaming Responses" and
"WebSockets" platform requirements, both wired to the same
`InferenceService` so there is exactly one orchestration path regardless of
transport.
"""

import json

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from app.dependencies.auth_dependencies import require_permission
from app.dependencies.service_dependencies import get_inference_service
from app.schemas.inference import InferenceRequest, InferenceResponse
from app.security.permissions import Permission
from app.services.inference_service import InferenceService

router = APIRouter(prefix="/inference", tags=["Inference"])


@router.post("", response_model=InferenceResponse)
async def generate(
    payload: InferenceRequest,
    service: InferenceService = Depends(get_inference_service),
    _principal=Depends(require_permission(Permission.INFERENCE_RUN)),
):
    messages = [m.model_dump() for m in payload.messages]
    response = await service.generate(payload.model_id, messages, payload.temperature)
    return InferenceResponse(
        content=response.content,
        model_id=response.model_id,
        prompt_tokens=response.prompt_tokens,
        completion_tokens=response.completion_tokens,
        latency_ms=response.latency_ms,
    )


@router.post("/stream")
async def generate_stream(
    payload: InferenceRequest,
    service: InferenceService = Depends(get_inference_service),
    _principal=Depends(require_permission(Permission.INFERENCE_RUN)),
):
    messages = [m.model_dump() for m in payload.messages]

    async def event_generator():
        async for chunk in service.stream(payload.model_id, messages, payload.temperature):
            yield f"data: {json.dumps({'delta': chunk.delta, 'is_final': chunk.is_final})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.websocket("/ws")
async def generate_ws(websocket: WebSocket, service: InferenceService = Depends(get_inference_service)):
    """WebSocket variant of streaming inference for clients that want a
    persistent bidirectional connection (e.g. to send a cancel signal
    mid-stream) rather than one-shot SSE."""
    await websocket.accept()
    try:
        while True:
            payload = await websocket.receive_json()
            model_id = payload.get("model_id", "claude-haiku-4.5")
            messages = payload.get("messages", [])
            async for chunk in service.stream(model_id, messages):
                await websocket.send_json({"delta": chunk.delta, "is_final": chunk.is_final})
    except WebSocketDisconnect:
        pass
