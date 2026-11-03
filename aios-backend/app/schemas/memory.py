from pydantic import BaseModel, Field

from app.schemas.common import TimestampedRead


class MemoryWriteRequest(BaseModel):
    workspace_id: str
    memory_type: str = Field(pattern="^(session|semantic|episodic)$")
    scope: str
    content: str = Field(min_length=1)


class MemoryQueryRequest(BaseModel):
    workspace_id: str
    query: str
    memory_type: str | None = None
    top_k: int = Field(default=5, ge=1, le=50)


class MemoryItemRead(TimestampedRead):
    workspace_id: str
    memory_type: str
    scope: str
    content: str
    relevance: float | None
