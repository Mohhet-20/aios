"""Shared JSON-Schema -> target-language type mapping used by every
generator, so Python and TypeScript output stay consistent when a new
JSON-Schema type needs handling."""
from __future__ import annotations

_PYTHON_TYPES = {
    "string": "str", "integer": "int", "number": "float", "boolean": "bool",
    "array": "list", "object": "dict",
}
_TYPESCRIPT_TYPES = {
    "string": "string", "integer": "number", "number": "number", "boolean": "boolean",
    "array": "any[]", "object": "Record<string, any>",
}


def python_type_for(schema_type: str | None) -> str:
    return _PYTHON_TYPES.get(schema_type or "", "Any")


def typescript_type_for(schema_type: str | None) -> str:
    return _TYPESCRIPT_TYPES.get(schema_type or "", "any")


def operation_method_name(operation_id: str) -> str:
    return operation_id.replace("-", "_")
