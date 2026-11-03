from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampedRead(ORMBase):
    id: str
    created_at: datetime
    updated_at: datetime


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict = {}
    request_id: str = ""
    correlation_id: str = ""


class ErrorResponse(BaseModel):
    error: ErrorDetail
