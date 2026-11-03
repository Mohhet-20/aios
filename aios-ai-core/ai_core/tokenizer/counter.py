"""Token counting. Uses tiktoken for OpenAI-family models (accurate) and
falls back to a documented approximate counter for every other provider
(Anthropic/Gemini/HF/local models don't ship a redistributable Python
tokenizer we can bundle here) — good enough for cost estimation and context
window budgeting, not byte-exact. Swap in each provider's real tokenizer
behind `count_tokens()` as they become available without touching callers.
"""
from __future__ import annotations

import functools

from ai_core.schemas.messages import ChatMessage

_APPROX_CHARS_PER_TOKEN = 4.0


@functools.lru_cache(maxsize=8)
def _tiktoken_encoding(model_hint: str):
    import tiktoken

    try:
        return tiktoken.encoding_for_model(model_hint)
    except KeyError:
        return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str, *, provider: str = "openai", model: str = "gpt-4o") -> int:
    if not text:
        return 0
    if provider in ("openai", "azure_openai", "ollama", "vllm", "lmstudio", "local_transformers"):
        try:
            enc = _tiktoken_encoding(model)
            return len(enc.encode(text))
        except Exception:  # noqa: BLE001 — fall through to approximation
            pass
    # Approximate counter: whitespace-aware so it's closer than a pure
    # char/4 heuristic for code and structured text.
    words = text.split()
    if not words:
        return max(1, int(len(text) / _APPROX_CHARS_PER_TOKEN))
    return max(len(words), int(len(text) / _APPROX_CHARS_PER_TOKEN))


def count_message_tokens(messages: list[ChatMessage], *, provider: str = "openai", model: str = "gpt-4o") -> int:
    """Approximates the OpenAI chat-format overhead (~4 tokens/message for
    role/name/separators) on top of content tokens. Close enough for
    pre-flight budgeting; the authoritative count is always what the
    provider reports back in `usage`."""
    total = 0
    for msg in messages:
        total += 4
        total += count_tokens(msg.text(), provider=provider, model=model)
        if msg.name:
            total += count_tokens(msg.name, provider=provider, model=model)
    total += 2
    return total
