"""Sample request/response generation: derives example payloads from
the same deliberately-scoped JSON-Schema subset `SchemaValidationService`
validates against (type/properties/enum/items) -- one example value per
property type, capped at `devx_sample_request_max_examples` variations
per field so a schema with several enum choices doesn't explode
combinatorially."""
from __future__ import annotations

from typing import Any

from gateway_platform.config.settings import Settings, get_settings

_TYPE_EXAMPLES: dict[str, Any] = {
    "string": "string",
    "integer": 0,
    "number": 0.0,
    "boolean": False,
    "array": [],
    "object": {},
}


class SampleRequestService:
    def __init__(self, *, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def _example_for_property(self, prop_schema: dict) -> list[Any]:
        if "enum" in prop_schema:
            return list(prop_schema["enum"])[: self.settings.devx_sample_request_max_examples]
        prop_type = prop_schema.get("type", "string")
        return [_TYPE_EXAMPLES.get(prop_type, "string")]

    def generate_samples(self, schema: dict | None) -> list[dict[str, Any]]:
        """Returns up to `devx_sample_request_max_examples` example
        payloads for the given JSON-Schema-subset object schema. A
        schema with no properties (or none provided) yields a single
        empty example."""
        if not schema or schema.get("type") != "object" or not schema.get("properties"):
            return [{}]

        properties: dict[str, dict] = schema["properties"]
        max_examples = self.settings.devx_sample_request_max_examples
        examples: list[dict[str, Any]] = [{} for _ in range(max_examples)]

        for prop_name, prop_schema in properties.items():
            choices = self._example_for_property(prop_schema)
            for index, example in enumerate(examples):
                example[prop_name] = choices[index % len(choices)]

        return examples
