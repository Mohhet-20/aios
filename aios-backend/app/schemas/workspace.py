from pydantic import BaseModel, Field

from app.schemas.common import TimestampedRead


class WorkspaceCreate(BaseModel):
    organization_id: str
    name: str = Field(min_length=1, max_length=255)
    color: str = "chart-1"


class WorkspaceRead(TimestampedRead):
    organization_id: str
    name: str
    color: str


class ProjectCreate(BaseModel):
    workspace_id: str
    name: str = Field(min_length=1, max_length=255)
    description: str = ""


class ProjectRead(TimestampedRead):
    workspace_id: str
    name: str
    description: str
    status: str
    progress: int
