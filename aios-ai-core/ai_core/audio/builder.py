"""Convenience builders for audio-input messages. Audio *output* (TTS) is
a provider-side generation concern, not a message-construction one, so it
isn't modeled here — a future AudioService would call a provider's TTS
endpoint directly and isn't part of the chat-message contract."""
from __future__ import annotations

import base64

from ai_core.schemas.enums import Role
from ai_core.schemas.messages import AudioPart, ChatMessage, TextPart


def audio_message_from_bytes(text: str, audio_bytes: bytes, *, mime_type: str = "audio/wav", role: Role = Role.USER) -> ChatMessage:
    encoded = base64.b64encode(audio_bytes).decode("ascii")
    return ChatMessage(role=role, content=[TextPart(text=text), AudioPart(data=encoded, mime_type=mime_type)])
