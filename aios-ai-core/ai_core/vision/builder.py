"""Convenience builders for multimodal (vision) messages. These just
construct the canonical ChatMessage/ContentPart shapes — the actual
translation to each provider's wire format happens in the provider
adapters (openai_compatible/anthropic/gemini already handle ImageUrlPart/
ImageBase64Part)."""
from __future__ import annotations

import base64

from ai_core.schemas.enums import Role
from ai_core.schemas.messages import ChatMessage, ImageBase64Part, ImageUrlPart, TextPart


def image_message_from_url(text: str, image_url: str, *, role: Role = Role.USER) -> ChatMessage:
    return ChatMessage(role=role, content=[TextPart(text=text), ImageUrlPart(url=image_url)])


def image_message_from_bytes(text: str, image_bytes: bytes, *, mime_type: str = "image/png", role: Role = Role.USER) -> ChatMessage:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return ChatMessage(role=role, content=[TextPart(text=text), ImageBase64Part(data=encoded, mime_type=mime_type)])


def multi_image_message(text: str, image_urls: list[str], *, role: Role = Role.USER) -> ChatMessage:
    parts = [TextPart(text=text)] + [ImageUrlPart(url=u) for u in image_urls]
    return ChatMessage(role=role, content=parts)
