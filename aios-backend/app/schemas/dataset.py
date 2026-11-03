from pydantic import BaseModel, Field

from app.schemas.common import TimestampedRead


class DatasetCreate(BaseModel):
    workspace_id: str
    name: str = Field(min_length=1, max_length=255)
    dataset_type: str = "reference"
    row_count: int = 0
    used_by: str = ""


class DatasetRead(TimestampedRead):
    workspace_id: str
    name: str
    dataset_type: str
    row_count: int
    used_by: str
