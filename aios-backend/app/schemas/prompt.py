from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import TimestampedRead


class PromptCreate(BaseModel):
    workspace_id: str
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    target_model: str
    tags: list[str] = []


class PromptRead(TimestampedRead):
    workspace_id: str
    name: str
    description: str
    target_model: str
    tags: str


class PromptVersionCreate(BaseModel):
    content: str = Field(min_length=1)


class PromptVersionRead(BaseModel):
    id: str
    prompt_id: str
    version: int
    content: str
    status: str
    author_id: str
    eval_score: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PromptPromoteRequest(BaseModel):
    target_status: str = Field(pattern="^(draft|staged|production|archived)$")


class PromptRenderRequest(BaseModel):
    variables: dict[str, str] = {}
