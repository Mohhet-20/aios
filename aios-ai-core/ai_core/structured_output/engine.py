"""Structured Output Engine: wraps ExecutionEngine.generate() with JSON
schema enforcement, parsing, Pydantic validation, and automatic "response
repair" — if the model's output doesn't parse or doesn't validate, we send
it back the error and ask it to fix it, up to `max_repair_attempts` times,
before giving up. This is what turns "the model usually returns JSON" into
"the caller gets a typed object or a clear error every time."
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from pydantic import BaseModel

from ai_core.execution.execution_engine import ExecutionEngine
from ai_core.schemas.enums import Role
from ai_core.schemas.messages import ChatMessage
from ai_core.schemas.requests import GenerationRequest
from ai_core.schemas.responses import GenerationResponse
from ai_core.structured_output.parser import parse_json_response
from ai_core.structured_output.schema_utils import response_format_for_model
from ai_core.structured_output.validator import validate_against_model
from ai_core.utils.exceptions import StructuredOutputError

T = TypeVar("T", bound=BaseModel)

# Heuristic, not a calibrated probability: confidence starts at 1.0 and
# decays per repair attempt needed. A response that validated on the first
# try is more trustworthy than one that needed the model to be corrected —
# but this is a proxy signal, not a statistically grounded confidence score.
_CONFIDENCE_BY_ATTEMPT = [1.0, 0.7, 0.4, 0.2]


@dataclass
class StructuredOutputResult(Generic[T]):
    instance: T
    raw: dict | list
    confidence: float
    attempts: int
    response: GenerationResponse


class StructuredOutputEngine:
    def __init__(self, engine: ExecutionEngine, *, max_repair_attempts: int = 2):
        self.engine = engine
        self.max_repair_attempts = max_repair_attempts

    async def execute(self, request: GenerationRequest, output_model: type[T]) -> StructuredOutputResult[T]:
        if request.response_format is None:
            request = request.model_copy(update={"response_format": response_format_for_model(output_model)})

        messages = list(request.messages)
        last_error: Exception | None = None

        for attempt in range(self.max_repair_attempts + 1):
            current_request = request.model_copy(update={"messages": messages})
            response = await self.engine.generate(current_request)
            try:
                data = parse_json_response(response.content)
                instance = validate_against_model(data, output_model)
                confidence = _CONFIDENCE_BY_ATTEMPT[min(attempt, len(_CONFIDENCE_BY_ATTEMPT) - 1)]
                return StructuredOutputResult(
                    instance=instance, raw=data, confidence=confidence, attempts=attempt + 1, response=response
                )
            except StructuredOutputError as exc:
                last_error = exc
                if attempt >= self.max_repair_attempts:
                    break
                messages = [
                    *messages,
                    ChatMessage(role=Role.ASSISTANT, content=response.content),
                    ChatMessage(
                        role=Role.USER,
                        content=(
                            f"Your previous response was invalid: {exc}. "
                            f"Return ONLY valid JSON matching the required schema, with no extra commentary."
                        ),
                    ),
                ]

        raise StructuredOutputError(
            f"structured output validation failed after {self.max_repair_attempts + 1} attempt(s): {last_error}"
        )
