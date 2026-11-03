import pytest

from ai_core.registry.model_metadata import ModelMetadata
from ai_core.registry.model_registry import ModelRegistry
from ai_core.registry.seed_data import build_seeded_registry
from ai_core.schemas.enums import Capability, ModelStatus
from ai_core.utils.exceptions import ModelNotFoundError


def test_register_and_get():
    registry = ModelRegistry()
    registry.register(ModelMetadata(provider="openai", name="gpt-4o"))
    model = registry.get("openai", "gpt-4o")
    assert model.key == "openai:gpt-4o"


def test_get_missing_raises():
    registry = ModelRegistry()
    with pytest.raises(ModelNotFoundError):
        registry.get("openai", "does-not-exist")


def test_dynamic_registration_of_new_model():
    registry = ModelRegistry()
    registry.register(ModelMetadata(provider="openai", name="gpt-5-preview", capabilities={Capability.REASONING}))
    assert registry.get("openai", "gpt-5-preview").supports(Capability.REASONING)


def test_update_status_marks_unavailable():
    registry = build_seeded_registry()
    registry.update_status("openai", "gpt-4o", ModelStatus.UNAVAILABLE)
    assert registry.get("openai", "gpt-4o").status == ModelStatus.UNAVAILABLE
    assert registry.get("openai", "gpt-4o") not in registry.list_by_capability(Capability.VISION)


def test_latency_ema_updates_smoothly():
    registry = build_seeded_registry()
    registry.update_latency("openai", "gpt-4o", 100.0)
    assert registry.get("openai", "gpt-4o").average_latency_ms == 100.0
    registry.update_latency("openai", "gpt-4o", 300.0, alpha=0.5)
    assert registry.get("openai", "gpt-4o").average_latency_ms == 200.0


def test_seed_registry_covers_all_nine_providers():
    registry = build_seeded_registry()
    providers = {m.provider for m in registry.all()}
    assert providers == {
        "openai", "azure_openai", "anthropic", "gemini", "huggingface", "ollama", "vllm", "lmstudio", "local_transformers",
    }
