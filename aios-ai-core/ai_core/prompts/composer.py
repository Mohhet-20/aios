"""Prompt composition: turns an ordered list of PromptTemplates + a shared
variable dict into the ChatMessage list a GenerationRequest expects. This
is what "system prompt + few-shot examples + user turn, all with variable
substitution" collapses into — one call, not hand-built message lists
scattered across callers.
"""
from __future__ import annotations

from ai_core.prompts.template import PromptTemplate
from ai_core.schemas.enums import Role
from ai_core.schemas.messages import ChatMessage


def render_messages(templates: list[PromptTemplate], variables: dict | None = None) -> list[ChatMessage]:
    variables = variables or {}
    return [ChatMessage(role=t.role, content=t.render(variables)) for t in templates]


def compose(
    *,
    system: PromptTemplate | str | None = None,
    developer: PromptTemplate | str | None = None,
    examples: list[tuple[str, str]] | None = None,
    user: PromptTemplate | str,
    variables: dict | None = None,
) -> list[ChatMessage]:
    """Convenience composer for the common shape: optional system prompt,
    optional developer prompt, optional few-shot (user, assistant) example
    pairs, then the real user turn. Strings are treated as pre-rendered
    text (no variable substitution); pass a PromptTemplate for anything
    that needs `{{variable}}` substitution.
    """
    variables = variables or {}
    messages: list[ChatMessage] = []

    def _resolve(role: Role, part: PromptTemplate | str) -> ChatMessage:
        text = part.render(variables) if isinstance(part, PromptTemplate) else part
        return ChatMessage(role=role, content=text)

    if system is not None:
        messages.append(_resolve(Role.SYSTEM, system))
    if developer is not None:
        messages.append(_resolve(Role.DEVELOPER, developer))
    for user_ex, assistant_ex in examples or []:
        messages.append(ChatMessage(role=Role.USER, content=user_ex))
        messages.append(ChatMessage(role=Role.ASSISTANT, content=assistant_ex))
    messages.append(_resolve(Role.USER, user))
    return messages
