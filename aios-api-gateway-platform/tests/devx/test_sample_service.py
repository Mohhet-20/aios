from __future__ import annotations

from gateway_platform.config.settings import Settings
from gateway_platform.devx.sample_service import SampleRequestService


def test_generate_samples_with_no_schema_returns_single_empty_example():
    service = SampleRequestService()
    assert service.generate_samples(None) == [{}]


def test_generate_samples_covers_property_types():
    settings = Settings(devx_sample_request_max_examples=2)
    service = SampleRequestService(settings=settings)
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "active": {"type": "boolean"},
        },
    }
    examples = service.generate_samples(schema)
    assert len(examples) == 2
    for example in examples:
        assert set(example.keys()) == {"name", "age", "active"}


def test_generate_samples_cycles_through_enum_values():
    settings = Settings(devx_sample_request_max_examples=3)
    service = SampleRequestService(settings=settings)
    schema = {"type": "object", "properties": {"status": {"enum": ["a", "b"]}}}
    examples = service.generate_samples(schema)
    assert len(examples) == 3
    assert [e["status"] for e in examples] == ["a", "b", "a"]
