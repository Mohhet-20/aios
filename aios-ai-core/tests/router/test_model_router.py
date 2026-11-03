import pytest

from ai_core.registry.seed_data import build_seeded_registry
from ai_core.router.model_router import ModelRouter
from ai_core.router.policy import RoutingPolicy
from ai_core.schemas.enums import Role
from ai_core.schemas.messages import ChatMessage
from ai_core.schemas.requests import EmbeddingRequest, GenerationRequest
from ai_core.schemas.tools import ToolDefinition
from ai_core.utils.exceptions import NoAvailableModelError


def _req(**kw) -> GenerationRequest:
    kw.setdefault("messages", [ChatMessage(role=Role.USER, content="hi")])
    return GenerationRequest(**kw)


def test_route_returns_fallback_chain_within_max_candidates():
    router = ModelRouter(build_seeded_registry())
    chain = router.route(_req())
    assert 1 <= len(chain) <= router.policy.max_candidates
    assert all(m.is_usable() for m in chain)


def test_explicit_provider_and_model_bypasses_routing():
    router = ModelRouter(build_seeded_registry())
    chain = router.route(_req(provider="anthropic", model="claude-3-5-haiku-20241022"))
    assert len(chain) == 1
    assert chain[0].key == "anthropic:claude-3-5-haiku-20241022"


def test_tool_calling_requirement_excludes_non_tool_models():
    router = ModelRouter(build_seeded_registry())
    chain = router.route(_req(tools=[ToolDefinition(name="x", description="x")]))
    from ai_core.schemas.enums import Capability

    assert all(Capability.TOOL_CALLING in m.capabilities for m in chain)
    # o1 doesn't support tool calling in the seed data — must never appear.
    assert all(m.key != "openai:o1" for m in chain)


def test_unsatisfiable_requirement_raises_no_available_model():
    router = ModelRouter(build_seeded_registry())
    with pytest.raises(NoAvailableModelError):
        router.route(_req(model="does-not-exist-anywhere"))


def test_cost_optimized_policy_prefers_cheap_models_first():
    router = ModelRouter(build_seeded_registry(), policy=RoutingPolicy.cost_optimized())
    chain = router.route(_req())
    assert chain[0].pricing.input_cost_per_1m <= chain[-1].pricing.input_cost_per_1m


def test_route_embedding_returns_only_embedding_capable_models():
    router = ModelRouter(build_seeded_registry())
    chain = router.route_embedding(EmbeddingRequest(input="hello world"))
    from ai_core.schemas.enums import Capability

    assert all(Capability.EMBEDDING in m.capabilities for m in chain)
