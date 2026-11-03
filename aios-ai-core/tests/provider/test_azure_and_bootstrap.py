
import httpx
import pytest

from ai_core.config.settings import AICoreSettings, ProviderSettings
from ai_core.providers.azure_openai import AzureOpenAIProvider
from ai_core.providers.registry_bootstrap import build_default_providers
from ai_core.schemas.enums import Role
from ai_core.schemas.messages import ChatMessage
from ai_core.schemas.requests import GenerationRequest


@pytest.mark.asyncio
async def test_azure_builds_deployment_scoped_url_and_api_key_header():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "/openai/deployments/my-gpt4-deployment/chat/completions" in str(request.url)
        assert "api-version=2024-06-01" in str(request.url)
        assert request.headers["api-key"] == "azure-secret"
        return httpx.Response(200, json={"choices": [{"message": {"content": "hi from azure"}, "finish_reason": "stop"}], "usage": {}})

    provider = AzureOpenAIProvider(
        api_key="azure-secret",
        endpoint="https://my-resource.openai.azure.com",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    req = GenerationRequest(messages=[ChatMessage(role=Role.USER, content="hi")])
    resp = await provider.generate(req, model="my-gpt4-deployment")
    assert resp.content == "hi from azure"


def test_build_default_providers_registers_all_nine():
    settings = AICoreSettings(providers=ProviderSettings())
    providers = build_default_providers(settings)
    assert set(providers.keys()) == {
        "openai", "azure_openai", "anthropic", "gemini", "huggingface", "ollama", "vllm", "lmstudio", "local_transformers",
    }
    for name, adapter in providers.items():
        assert adapter.provider_name == name
