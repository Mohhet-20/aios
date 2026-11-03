from datetime import datetime

from pydantic import BaseModel


class ComponentHealthRead(BaseModel):
    name: str
    healthy: bool
    latency_ms: float | None
    detail: str | None


class HealthResponse(BaseModel):
    healthy: bool
    components: list[ComponentHealthRead] = []


class JobRead(BaseModel):
    id: str
    name: str
    status: str
    attempts: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error: str | None
