from pydantic import BaseModel, Field

from app.schemas.common import TimestampedRead


class ModelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    provider: str
    context_window: int
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    modality: str = "text"
    status: str = "available"


class ModelRead(TimestampedRead):
    name: str
    provider: str
    context_window: int
    cost_per_1k_input: float
    cost_per_1k_output: float
    modality: str
    status: str
    is_enabled: bool
