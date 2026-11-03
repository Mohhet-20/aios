"""Canonical, provider-agnostic message schema. Every provider adapter's job
is to translate ChatMessage/ContentPart <-> its own wire format — nothing
above the provider layer ever sees a provider-specific shape.
"""
from __future__ import annotations

from typing import Any, Literal, Union

from pydantic import BaseModel, Field, model_validator

from ai_core.schemas.enums import ContentType, Role


class TextPart(BaseModel):
    type: Literal[ContentType.TEXT] = ContentType.TEXT
    text: str


class ImageUrlPart(BaseModel):
    type: Literal[ContentType.IMAGE_URL] = ContentType.IMAGE_URL
    url: str
    detail: str | None = None


class ImageBase64Part(BaseModel):
    type: Literal[ContentType.IMAGE_BASE64] = ContentType.IMAGE_BASE64
    data: str
    mime_type: str = "image/png"


class DocumentPart(BaseModel):
    type: Literal[ContentType.DOCUMENT] = ContentType.DOCUMENT
    data: str
    mime_type: str = "application/pdf"
    filename: str | None = None


class AudioPart(BaseModel):
    type: Literal[ContentType.AUDIO] = ContentType.AUDIO
    data: str
    mime_type: str = "audio/wav"


ContentPart = Union[TextPart, ImageUrlPart, ImageBase64Part, DocumentPart, AudioPart]


class ChatMessage(BaseModel):
    """A single turn. `content` is either a plain string (the common case)
    or a list of typed content parts for multimodal/mixed-input messages."""

    role: Role
    content: str | list[ContentPart] = ""
    name: str | None = None
    tool_call_id: str | None = Field(
        default=None, description="Set when role=TOOL: which tool_call this message answers."
    )
    tool_calls: list[dict[str, Any]] | None = Field(
        default=None, description="Set on assistant messages that requested tool calls."
    )

    @model_validator(mode="after")
    def _validate_tool_fields(self) -> "ChatMessage":
        if self.role == Role.TOOL and not self.tool_call_id:
            raise ValueError("ChatMessage with role=tool must set tool_call_id")
        return self

    def text(self) -> str:
        """Best-effort plain-text extraction, used by tokenizers/logging
        that don't care about multimodal structure."""
        if isinstance(self.content, str):
            return self.content
        parts = [p.text for p in self.content if isinstance(p, TextPart)]
        return "\n".join(parts)

    def is_multimodal(self) -> bool:
        return isinstance(self.content, list) and any(not isinstance(p, TextPart) for p in self.content)
