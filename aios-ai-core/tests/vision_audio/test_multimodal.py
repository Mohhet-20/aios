import pytest

from ai_core.audio.builder import audio_message_from_bytes
from ai_core.registry.model_metadata import ModelMetadata
from ai_core.registry.model_registry import ModelRegistry
from ai_core.router.model_router import ModelRouter
from ai_core.router.policy import RoutingPolicy
from ai_core.schemas.enums import Capability
from ai_core.schemas.requests import GenerationRequest
from ai_core.utils.exceptions import NoAvailableModelError
from ai_core.vision.builder import image_message_from_bytes, image_message_from_url, multi_image_message


def test_image_message_from_url_has_text_and_image_parts():
    msg = image_message_from_url("what is this?", "https://example.com/cat.png")
    assert msg.is_multimodal()
    assert msg.text() == "what is this?"


def test_image_message_from_bytes_encodes_base64():
    msg = image_message_from_bytes("describe", b"fake-png-bytes", mime_type="image/jpeg")
    image_part = [p for p in msg.content if p.type == "image_base64"][0]
    assert image_part.mime_type == "image/jpeg"
    assert image_part.data


def test_multi_image_message_includes_all_images():
    msg = multi_image_message("compare these", ["https://a/1.png", "https://a/2.png"])
    assert len([p for p in msg.content if p.type == "image_url"]) == 2


def test_audio_message_from_bytes():
    msg = audio_message_from_bytes("transcribe this", b"fake-wav-bytes")
    audio_part = [p for p in msg.content if p.type == "audio"][0]
    assert audio_part.data


def test_router_auto_requires_vision_capability_for_image_messages():
    registry = ModelRegistry()
    registry.register(ModelMetadata(provider="test", name="no-vision", priority=1, capabilities=set()))
    registry.register(ModelMetadata(provider="test", name="vision-model", priority=2, capabilities={Capability.VISION}))
    router = ModelRouter(registry, policy=RoutingPolicy(name="t", strategies=[], max_candidates=5))

    request = GenerationRequest(messages=[image_message_from_url("what is this", "https://example.com/x.png")])
    chain = router.route(request)
    assert all(Capability.VISION in m.capabilities for m in chain)
    assert all(m.name != "no-vision" for m in chain)


def test_router_raises_when_no_vision_model_available():
    registry = ModelRegistry()
    registry.register(ModelMetadata(provider="test", name="no-vision", priority=1, capabilities=set()))
    router = ModelRouter(registry, policy=RoutingPolicy(name="t", strategies=[], max_candidates=5))
    request = GenerationRequest(messages=[image_message_from_url("what is this", "https://example.com/x.png")])
    with pytest.raises(NoAvailableModelError):
        router.route(request)
