from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import TimestampedRead


class AgentCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    workspace_id: str
    name: str = Field(min_length=1, max_length=255)
    role: str
    description: str = ""
    model_id: str
    allowed_tool_ids: list[str] = []


class AgentRead(TimestampedRead):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    workspace_id: str
    name: str
    role: str
    description: str
    model_id: str
    status: str
    runs_today: int
    success_rate: float
