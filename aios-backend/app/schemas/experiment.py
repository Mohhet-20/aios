from pydantic import BaseModel, Field

from app.schemas.common import TimestampedRead


class ExperimentCreate(BaseModel):
    workspace_id: str
    name: str = Field(min_length=1, max_length=255)
    hypothesis: str = ""
    variant: str = ""


class ExperimentRead(TimestampedRead):
    workspace_id: str
    name: str
    hypothesis: str
    variant: str
    result_metric: str
    status: str
