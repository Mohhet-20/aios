from pydantic import BaseModel, Field

from app.schemas.common import TimestampedRead


class EvaluationRunCreate(BaseModel):
    workspace_id: str
    suite_name: str
    target_type: str = Field(pattern="^(prompt_version|agent|model)$")
    target_id: str
    dataset_id: str


class EvaluationRunRead(TimestampedRead):
    workspace_id: str
    suite_name: str
    target_type: str
    target_id: str
    dataset_id: str
    status: str
    total: int
    passed: int
    failed: int
    score: float | None
    previous_score: float | None
