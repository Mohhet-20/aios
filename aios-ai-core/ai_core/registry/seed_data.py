"""Illustrative seed data for the Model Registry, covering every supported
provider. Pricing/context-window figures are example values as of this AI
Core's build date — operators should treat this as a starting point and
refresh it from each provider's live pricing page, not a source of truth
frozen in code. Dynamic registration (`ModelRegistry.register`) is exactly
how that refresh happens without a code change.
"""
from __future__ import annotations

from ai_core.registry.model_metadata import ModelMetadata, ModelPricing
from ai_core.registry.model_registry import ModelRegistry
from ai_core.schemas.enums import Capability as C

_CHAT_CAPS = {C.STREAMING, C.TOOL_CALLING, C.JSON_OUTPUT}
_VISION_CAPS = _CHAT_CAPS | {C.VISION}


def build_seeded_registry() -> ModelRegistry:
    registry = ModelRegistry()
    registry.register_many(
        [
            # --- OpenAI -----------------------------------------------------
            ModelMetadata(
                provider="openai", name="gpt-4o", context_window=128_000, max_output_tokens=16_384,
                capabilities=_VISION_CAPS, pricing=ModelPricing(input_cost_per_1m=2.50, output_cost_per_1m=10.00),
                priority=10, tags=["general", "reasoning", "coding"],
            ),
            ModelMetadata(
                provider="openai", name="gpt-4o-mini", context_window=128_000, max_output_tokens=16_384,
                capabilities=_VISION_CAPS, pricing=ModelPricing(input_cost_per_1m=0.15, output_cost_per_1m=0.60),
                priority=20, tags=["general", "fast", "cheap"],
            ),
            ModelMetadata(
                provider="openai", name="o1", context_window=200_000, max_output_tokens=100_000,
                capabilities={C.JSON_OUTPUT, C.REASONING}, pricing=ModelPricing(input_cost_per_1m=15.00, output_cost_per_1m=60.00),
                priority=5, tags=["reasoning", "hard-problems"],
            ),
            ModelMetadata(
                provider="openai", name="text-embedding-3-small", context_window=8191,
                capabilities={C.EMBEDDING}, pricing=ModelPricing(input_cost_per_1m=0.02), priority=10, tags=["embedding"],
            ),
            ModelMetadata(
                provider="openai", name="text-embedding-3-large", context_window=8191,
                capabilities={C.EMBEDDING}, pricing=ModelPricing(input_cost_per_1m=0.13), priority=20, tags=["embedding", "high-quality"],
            ),
            # --- Anthropic ----------------------------------------------------
            ModelMetadata(
                provider="anthropic", name="claude-3-5-sonnet-20241022", context_window=200_000, max_output_tokens=8192,
                capabilities=_VISION_CAPS, pricing=ModelPricing(input_cost_per_1m=3.00, output_cost_per_1m=15.00),
                priority=10, tags=["general", "reasoning", "coding"],
            ),
            ModelMetadata(
                provider="anthropic", name="claude-3-5-haiku-20241022", context_window=200_000, max_output_tokens=8192,
                capabilities=_CHAT_CAPS, pricing=ModelPricing(input_cost_per_1m=0.80, output_cost_per_1m=4.00),
                priority=20, tags=["general", "fast", "cheap"],
            ),
            ModelMetadata(
                provider="anthropic", name="claude-3-opus-20240229", context_window=200_000, max_output_tokens=4096,
                capabilities=_VISION_CAPS, pricing=ModelPricing(input_cost_per_1m=15.00, output_cost_per_1m=75.00),
                priority=15, tags=["reasoning", "hard-problems"],
            ),
            # --- Gemini ---------------------------------------------------
            ModelMetadata(
                provider="gemini", name="gemini-1.5-pro", context_window=2_000_000, max_output_tokens=8192,
                capabilities=_VISION_CAPS | {C.AUDIO_INPUT}, pricing=ModelPricing(input_cost_per_1m=1.25, output_cost_per_1m=5.00),
                priority=15, tags=["general", "long-context"],
            ),
            ModelMetadata(
                provider="gemini", name="gemini-1.5-flash", context_window=1_000_000, max_output_tokens=8192,
                capabilities=_VISION_CAPS, pricing=ModelPricing(input_cost_per_1m=0.075, output_cost_per_1m=0.30),
                priority=25, tags=["general", "fast", "cheap", "long-context"],
            ),
            ModelMetadata(
                provider="gemini", name="text-embedding-004", context_window=2048,
                capabilities={C.EMBEDDING}, pricing=ModelPricing(input_cost_per_1m=0.0), priority=10, tags=["embedding"],
            ),
            # --- Azure OpenAI (deployment name is operator-specific; this
            # is an illustrative default deployment alias) -----------------
            ModelMetadata(
                provider="azure_openai", name="gpt-4o-deployment", context_window=128_000, max_output_tokens=16_384,
                capabilities=_VISION_CAPS, pricing=ModelPricing(input_cost_per_1m=2.50, output_cost_per_1m=10.00),
                priority=10, tags=["general", "enterprise"],
            ),
            # --- HuggingFace Inference --------------------------------------
            ModelMetadata(
                provider="huggingface", name="meta-llama/Llama-3-8b-Instruct", context_window=8192, max_output_tokens=2048,
                capabilities={C.JSON_OUTPUT}, pricing=ModelPricing(), priority=40, tags=["general", "open-weight"],
            ),
            ModelMetadata(
                provider="huggingface", name="sentence-transformers/all-MiniLM-L6-v2", context_window=256,
                capabilities={C.EMBEDDING}, pricing=ModelPricing(), priority=40, tags=["embedding", "open-weight"],
            ),
            # --- Ollama (local) ---------------------------------------------
            ModelMetadata(
                provider="ollama", name="llama3", context_window=8192, max_output_tokens=2048,
                capabilities={C.STREAMING, C.JSON_OUTPUT}, pricing=ModelPricing(), priority=50, tags=["general", "local", "free"],
            ),
            ModelMetadata(
                provider="ollama", name="mistral", context_window=8192, max_output_tokens=2048,
                capabilities={C.STREAMING, C.JSON_OUTPUT}, pricing=ModelPricing(), priority=55, tags=["general", "local", "free"],
            ),
            # --- vLLM (self-hosted) ------------------------------------------
            ModelMetadata(
                provider="vllm", name="mixtral-8x7b-instruct", context_window=32_768, max_output_tokens=4096,
                capabilities={C.STREAMING, C.TOOL_CALLING, C.JSON_OUTPUT}, pricing=ModelPricing(),
                priority=45, tags=["general", "self-hosted", "free"],
            ),
            # --- LM Studio / local Transformers (dev machines) ----------------
            ModelMetadata(
                provider="lmstudio", name="local-model", context_window=8192, max_output_tokens=2048,
                capabilities={C.STREAMING}, pricing=ModelPricing(), priority=90, tags=["local", "dev"],
            ),
            ModelMetadata(
                provider="local_transformers", name="local-model", context_window=4096, max_output_tokens=1024,
                capabilities={C.STREAMING}, pricing=ModelPricing(), priority=90, tags=["local", "dev"],
            ),
        ]
    )
    return registry
