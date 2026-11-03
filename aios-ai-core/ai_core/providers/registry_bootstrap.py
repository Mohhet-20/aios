"""Wires concrete provider adapters from settings. This is the one place
that needs to change when a new provider is added — everything else
(execution engine, router, registry) only ever depends on
`ModelProviderAdapter`.
"""
from __future__ import annotations

from ai_core.config.settings import AICoreSettings
from ai_core.providers.anthropic import AnthropicProvider
from ai_core.providers.azure_openai import AzureOpenAIProvider
from ai_core.providers.base import ModelProviderAdapter
from ai_core.providers.gemini import GeminiProvider
from ai_core.providers.huggingface import HuggingFaceProvider
from ai_core.providers.openai_compatible import (
    LMStudioProvider,
    LocalTransformersProvider,
    OllamaProvider,
    OpenAIProvider,
    VLLMProvider,
)


def build_default_providers(settings: AICoreSettings) -> dict[str, ModelProviderAdapter]:
    p = settings.providers
    return {
        "openai": OpenAIProvider(api_key=p.openai_api_key, base_url=p.openai_base_url),
        "azure_openai": AzureOpenAIProvider(
            api_key=p.azure_openai_api_key, endpoint=p.azure_openai_endpoint, api_version=p.azure_openai_api_version
        ),
        "anthropic": AnthropicProvider(api_key=p.anthropic_api_key, base_url=p.anthropic_base_url),
        "gemini": GeminiProvider(api_key=p.gemini_api_key, base_url=p.gemini_base_url),
        "huggingface": HuggingFaceProvider(api_key=p.huggingface_api_key, base_url=p.huggingface_base_url),
        "ollama": OllamaProvider(base_url=p.ollama_base_url),
        "vllm": VLLMProvider(base_url=p.vllm_base_url),
        "lmstudio": LMStudioProvider(base_url=p.lmstudio_base_url),
        "local_transformers": LocalTransformersProvider(base_url=p.local_transformers_base_url),
    }
