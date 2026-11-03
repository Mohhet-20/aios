from datetime import datetime

from pydantic import BaseModel, Field


class ConversationStartRequest(BaseModel):
    workspace_id: str
    agent_id: str | None = None
    title: str = ""


class ConversationRead(BaseModel):
    id: str
    workspace_id: str
    agent_id: str | None
    user_id: str
    title: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageCreateRequest(BaseModel):
    role: str = Field(pattern="^(user|assistant|system|tool)$")
    content: str


class MessageRead(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    tool_calls: list | None
    created_at: datetime

    model_config = {"from_attributes": True}
