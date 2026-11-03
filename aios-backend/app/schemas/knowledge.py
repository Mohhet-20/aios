from pydantic import BaseModel, Field

from app.schemas.common import TimestampedRead


class KnowledgeCollectionCreate(BaseModel):
    workspace_id: str
    name: str = Field(min_length=1, max_length=255)


class KnowledgeCollectionRead(TimestampedRead):
    workspace_id: str
    name: str
    document_count: int


class DocumentUploadRequest(BaseModel):
    workspace_id: str
    name: str
    size_bytes: int = 0
    collection_id: str | None = None


class DocumentRead(TimestampedRead):
    workspace_id: str
    collection_id: str | None
    name: str
    size_bytes: int
    status: str
