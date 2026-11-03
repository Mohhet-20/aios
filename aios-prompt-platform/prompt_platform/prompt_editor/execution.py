"""Response Preview / Streaming Preview / Structured Output Preview —
actually executing a rendered draft through the AI Core, without
persisting anything (that's what Testing/Evaluation do). This is the
"press run in Prompt Studio and see what comes back" capability.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from ai_core.bootstrap import AICoreContext
from ai_core.prompts.composer import render_messages
from ai_core.prompts.template import PromptTemplate
from ai_core.schemas.enums import Role
from ai_core.schemas.requests import GenerationRequest
from ai_core.schemas.responses import GenerationResponse, StreamChunk
from ai_core.structured_output.parser import parse_json_response

from prompt_platform.core.exceptions import ValidationError


class StudioExecutionService:
    def __init__(self, ai_core: AICoreContext):
        self.ai_core = ai_core

    def _render(self, *, system_template, developer_template, user_template, variables) -> list:
        templates = []
        if system_template:
            templates.append(PromptTemplate(name="system", role=Role.SYSTEM, template=system_template))
        if developer_template:
            templates.append(PromptTemplate(name="developer", role=Role.DEVELOPER, template=developer_template))
        templates.append(PromptTemplate(name="user", role=Role.USER, template=user_template))
        try:
            return render_messages(templates, variables)
        except Exception as exc:
            raise ValidationError(f"failed to render prompt: {exc}") from exc

    async def run(
        self, *, system_template, developer_template, user_template, variables, parameters
    ) -> GenerationResponse:
        messages = self._render(
            system_template=system_template, developer_template=developer_template, user_template=user_template, variables=variables
        )
        request = GenerationRequest(
            messages=messages,
            model=parameters.get("model"),
            provider=parameters.get("provider"),
            temperature=parameters.get("temperature", 0.7),
            max_tokens=parameters.get("max_tokens"),
            tools=parameters.get("tools"),
            response_format=parameters.get("response_format"),
        )
        return await self.ai_core.execution_engine.generate(request)

    async def run_stream(
        self, *, system_template, developer_template, user_template, variables, parameters
    ) -> AsyncIterator[StreamChunk]:
        messages = self._render(
            system_template=system_template, developer_template=developer_template, user_template=user_template, variables=variables
        )
        request = GenerationRequest(
            messages=messages,
            model=parameters.get("model"),
            provider=parameters.get("provider"),
            temperature=parameters.get("temperature", 0.7),
            max_tokens=parameters.get("max_tokens"),
            stream=True,
        )
        async for chunk in self.ai_core.execution_engine.stream(request):
            yield chunk

    async def run_structured(
        self, *, system_template, developer_template, user_template, variables, parameters, json_schema: dict
    ) -> dict:
        """Structured Output Preview. Unlike ai_core's StructuredOutputEngine
        (which validates against a caller-known Pydantic class), the Studio
        only has a JSON-schema dict typed by the prompt engineer at edit
        time — so this does schema-tagged generation plus tolerant JSON
        parsing, without a Pydantic validation step. Full repair-retry
        structured output belongs to prompt_evaluation/prompt_testing,
        which DO know the target Pydantic shape ahead of time."""
        messages = self._render(
            system_template=system_template, developer_template=developer_template, user_template=user_template, variables=variables
        )
        request = GenerationRequest(
            messages=messages,
            model=parameters.get("model"),
            provider=parameters.get("provider"),
            temperature=parameters.get("temperature", 0.7),
            response_format={"type": "json_schema", "json_schema": {"name": "StudioPreview", "schema": json_schema}},
        )
        response = await self.ai_core.execution_engine.generate(request)
        try:
            parsed = parse_json_response(response.content)
            return {"parsed": parsed, "raw": response.content, "valid_json": True}
        except Exception as exc:  # noqa: BLE001
            return {"parsed": None, "raw": response.content, "valid_json": False, "error": str(exc)}
