import pytest
from pydantic import ValidationError

from ai_core.schemas.enums import Role
from ai_core.schemas.messages import ChatMessage, TextPart, ImageUrlPart
from ai_core.schemas.requests import GenerationRequest
from ai_core.tokenizer.counter import count_message_tokens, count_tokens


def test_chat_message_text_extraction_plain_string():
    msg = ChatMessage(role=Role.USER, content="hello")
    assert msg.text() == "hello"
    assert not msg.is_multimodal()


def test_chat_message_text_extraction_multimodal():
    msg = ChatMessage(role=Role.USER, content=[TextPart(text="describe this"), ImageUrlPart(url="https://x/y.png")])
    assert msg.text() == "describe this"
    assert msg.is_multimodal()


def test_tool_message_requires_tool_call_id():
    with pytest.raises(ValidationError):
        ChatMessage(role=Role.TOOL, content="result")


def test_generation_request_defaults():
    req = GenerationRequest(messages=[ChatMessage(role=Role.USER, content="hi")])
    assert req.temperature == 0.7
    assert req.tool_choice == "auto"
    assert req.request_id


def test_token_counting_nonzero_and_monotonic():
    short = count_tokens("hi")
    longer = count_tokens("hi " * 50)
    assert short > 0
    assert longer > short


def test_message_token_counting_includes_overhead():
    msgs = [ChatMessage(role=Role.SYSTEM, content="sys"), ChatMessage(role=Role.USER, content="hello")]
    total = count_message_tokens(msgs)
    assert total > count_tokens("sys") + count_tokens("hello")
