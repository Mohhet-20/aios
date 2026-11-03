"""Shared "render a persisted PromptVersion + execute it through the AI
Core" helper. Used by prompt_testing, prompt_evaluation, and
prompt_experiments (all operate on saved/effective versions); Prompt
Studio has its own variant in prompt_editor/ because it renders unsaved
draft text, not a persisted row.

Optionally logs every call to Prompt Observability (prompt_observability.
ObservabilityService) — pass `observability` + `prompt_id`/`version_id`
and every render+execute, success or failure, becomes a queryable
PromptExecutionLogModel row. This is the single choke point all three
callers share, so wiring logging here means testing, evaluation, and
experiment runs are observable without each service reimplementing it.
"""
from __future__ import annotations

from typing import Any

from ai_core.bootstrap import AICoreContext
from ai_core.prompts.composer import render_messages
from ai_core.prompts.template import PromptTemplate
from ai_core.schemas.enums import Role
from ai_core.schemas.requests import GenerationRequest
from ai_core.schemas.responses import GenerationResponse


async def render_and_execute(
    ai_core: AICoreContext, version, variables: dict, *,
    observability: Any = None, prompt_id: str | None = None, version_id: str | None = None,
    source: str = "unknown", environment: str | None = None, triggered_by: str | None = None,
    correlation_id: str | None = None,
) -> tuple[str, GenerationResponse]:
    templates = []
    if version.system_template:
        templates.append(PromptTemplate(name="system", role=Role.SYSTEM, template=version.system_template))
    if version.developer_template:
        templates.append(PromptTemplate(name="developer", role=Role.DEVELOPER, template=version.developer_template))
    templates.append(PromptTemplate(name="user", role=Role.USER, template=version.user_template))
    messages = render_messages(templates, variables)

    params = version.parameters or {}
    request = GenerationRequest(
        messages=messages, model=params.get("model"), provider=params.get("provider"),
        temperature=params.get("temperature", 0.7), max_tokens=params.get("max_tokens"),
    )
    rendered_text = "\n".join(m.text() for m in messages)

    should_log = observability is not None and prompt_id is not None and version_id is not None
    try:
        response = await ai_core.execution_engine.generate(request)
    except Exception as exc:
        if should_log:
            await observability.record_execution(
                prompt_id=prompt_id, version_id=version_id, source=source, exception=exc,
                environment=environment, triggered_by=triggered_by, correlation_id=correlation_id,
            )
        raise

    if should_log:
        await observability.record_execution(
            prompt_id=prompt_id, version_id=version_id, source=source, response=response,
            environment=environment, triggered_by=triggered_by, correlation_id=correlation_id,
        )
    return rendered_text, response
