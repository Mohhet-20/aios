from fastapi import APIRouter, Response

from app.monitoring.metrics import render_metrics

router = APIRouter(tags=["Metrics"])


@router.get("/metrics")
async def metrics():
    body, content_type = render_metrics()
    return Response(content=body, media_type=content_type)
