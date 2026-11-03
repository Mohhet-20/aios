"""Reports: aggregates evaluation/monitoring/audit data into a single
document-shaped response, mirroring what the frontend's Reports page
renders (weekly summaries, cost & usage, regression reports, audits)."""

from fastapi import APIRouter, Depends

from app.dependencies.service_dependencies import get_evaluation_service, get_monitoring_service
from app.services.evaluation_service import EvaluationService
from app.services.monitoring_service import MonitoringService

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/summary")
async def report_summary(
    workspace_id: str,
    evaluation_service: EvaluationService = Depends(get_evaluation_service),
    monitoring_service: MonitoringService = Depends(get_monitoring_service),
):
    evaluations = await evaluation_service.repository.list(workspace_id=workspace_id)
    jobs = monitoring_service.list_jobs(limit=20)
    return {
        "workspace_id": workspace_id,
        "evaluation_count": len(evaluations),
        "average_score": round(sum(e.score or 0 for e in evaluations) / len(evaluations), 2)
        if evaluations
        else None,
        "recent_jobs": [{"id": j.id, "name": j.name, "status": j.status.value} for j in jobs],
    }
