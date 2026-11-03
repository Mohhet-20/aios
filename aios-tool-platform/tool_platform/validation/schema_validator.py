"""Standalone JSON Schema validation the AI Tool Planning module (and
anything else that wants a pre-flight check before actually dispatching
a call) can use without going through the Execution Engine — the engine
has its own copy of this exact check inline (`_validate_schema` in
`tool_execution/engine.py`) since duplicating four lines there avoided
an import-order dependency; this is the shared, reusable version for
every other caller."""
from __future__ import annotations

from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate as jsonschema_validate


def validate_against_schema(schema: dict, data: dict, *, label: str = "data") -> str | None:
    """Returns None if valid, or a human-readable error message if not."""
    if not schema:
        return None
    try:
        jsonschema_validate(instance=data, schema=schema)
        return None
    except JsonSchemaValidationError as exc:
        return f"{label} failed schema validation: {exc.message}"


def is_valid(schema: dict, data: dict) -> bool:
    return validate_against_schema(schema, data) is None
