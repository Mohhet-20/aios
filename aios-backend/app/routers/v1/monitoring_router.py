from fastapi import APIRouter, Depends, Query

from app.dependencies.service_dependencies import get_monitoring_service
from app.schemas.monitoring import JobRead
from app.services.monitoring_service import MonitoringService

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


@router.get("/jobs", response_model=list[JobRead])
async def list_jobs(
    limit: int = Query(default=50, le=200), service: MonitoringService = Depends(get_monitoring_service)
):
    return service.list_jobs(limit)


@router.get("/jobs/{job_id}", response_model=JobRead)
async def get_job(job_id: str, service: MonitoringService = Depends(get_monitoring_service)):
    from app.core.exceptions import NotFoundError

    job = service.get_job(job_id)
    if job is None:
        raise NotFoundError(f"Job '{job_id}' not found")
    return job
