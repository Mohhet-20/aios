"""Pre-flight request validation and post-flight response validation. Kept
separate from the engine's control flow so the rules are easy to find and
extend without wading through retry/failover logic."""
from __future__ import annotations

from ai_core.config.settings import AICoreSettings
from ai_core.registry.model_metadata import ModelMetadata
from ai_core.schemas.enums import Capability
from ai_core.schemas.requests import GenerationRequest
from ai_core.schemas.responses import GenerationResponse
from ai_core.utils.exceptions import RequestValidationError, ResponseValidationError


def validate_request(request: GenerationRequest, *, settings: AICoreSettings | None = None) -> None:
    if not request.messages:
        raise RequestValidationError("GenerationRequest.messages must not be empty")
    if request.temperature < 0 or request.temperature > 2:
        raise RequestValidationError(f"temperature must be within [0, 2], got {request.temperature}")
    if request.max_tokens is not None and request.max_tokens <= 0:
        raise RequestValidationError("max_tokens must be positive when set")
    if request.tools and request.tool_choice not in ("auto", "none", "required") and request.tool_choice not in {
        t.name for t in request.tools
    }:
        raise RequestValidationError(f"tool_choice {request.tool_choice!r} does not match any provided tool name")

    if settings is not None:
        if request.stream and not settings.enable_streaming:
            raise RequestValidationError("streaming is disabled (AICoreSettings.enable_streaming=False)")
        if request.tools and not settings.enable_tool_calling:
            raise RequestValidationError("tool calling is disabled (AICoreSettings.enable_tool_calling=False)")
        if request.response_format and not settings.enable_structured_output:
            raise RequestValidationError("structured output is disabled (AICoreSettings.enable_structured_output=False)")


def validate_candidate_supports_request(model: ModelMetadata, request: GenerationRequest) -> None:
    if request.stream and Capability.STREAMING not in model.capabilities:
        raise RequestValidationError(f"model {model.key} does not support streaming")
    if request.tools and Capability.TOOL_CALLING not in model.capabilities:
        raise RequestValidationError(f"model {model.key} does not support tool calling")
    if request.response_format and Capability.JSON_OUTPUT not in model.capabilities:
        raise RequestValidationError(f"model {model.key} does not support structured JSON output")


def validate_response(response: GenerationResponse) -> None:
    if not response.content and not response.tool_calls:
        raise ResponseValidationError("provider returned an empty response (no content and no tool_calls)")
