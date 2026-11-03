from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import TimestampedRead


class WorkflowCreate(BaseModel):
    workspace_id: str
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    definition: dict = {"nodes": [], "edges": []}


class WorkflowRead(TimestampedRead):
    workspace_id: str
    name: str
    description: str
    status: str
    definition: dict
    success_rate: float


class WorkflowExecuteRequest(BaseModel):
    input_payload: dict = {}


class WorkflowExecutionRead(BaseModel):
    id: str
    workflow_id: str
    status: str
    triggered_by: str
    input_payload: dict
    steps: list
    started_at: datetime
    completed_at: datetime | None
    error: str | None

    model_config = {"from_attributes": True}
