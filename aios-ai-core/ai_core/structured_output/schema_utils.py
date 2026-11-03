"""Builds the `response_format` payload sent to providers from a Pydantic
output model, and the reverse: turning a provider's JSON-schema-shaped
tool into a `response_format` dict. Kept separate from the parser/validator
so provider-facing wire format concerns don't leak into validation logic.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


def response_format_for_model(output_model: type[BaseModel]) -> dict[str, Any]:
    schema = output_model.model_json_schema()
    return {
        "type": "json_schema",
        "json_schema": {"name": output_model.__name__, "schema": schema, "strict": True},
    }
