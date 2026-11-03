import httpx
import pytest

from ai_core.providers.base import ModelProviderAdapter
from ai_core.schemas.enums import FinishReason
from ai_core.schemas.responses import ExecutionMetadata, GenerationResponse
from ai_core.schemas.usage import TokenUsage


def make_response(request_id: str, provider: str, model: str, content: str = "ok") -> GenerationResponse:
    return GenerationResponse(
        content=content,
        finish_reason=FinishReason.STOP,
        usage=TokenUsage(input_tokens=10, output_tokens=5),
        execution=ExecutionMetadata(request_id=request_id, provider=provider, model=model, latency_ms=1.0),
    )


class ScriptedProvider(ModelProviderAdapter):
    """Test double: pops one scripted action per call. An action is either
    an Exception to raise, a GenerationResponse to return, or (for stream)
    a list of StreamChunk to yield."""

    def __init__(self, provider_name: str, script: list):
        super().__init__(http_client=httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200))))
        self.provider_name = provider_name
        self._script = list(script)
        self.calls = 0

    async def generate(self, request, *, model):
        self.calls += 1
        action = self._script.pop(0)
        if isinstance(action, BaseException):
            raise action
        return action

    async def stream(self, request, *, model):
        self.calls += 1
        action = self._script.pop(0)
        if isinstance(action, BaseException):
            raise action
        for chunk in action:
            yield chunk

    async def embed(self, request, *, model):
        self.calls += 1
        action = self._script.pop(0)
        if isinstance(action, BaseException):
            raise action
        return action


@pytest.fixture
def scripted_provider():
    return ScriptedProvider
