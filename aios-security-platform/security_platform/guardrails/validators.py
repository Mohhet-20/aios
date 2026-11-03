"""Structured output validation. Deliberately a *subset* of JSON
Schema — type checking (object/array/string/number/integer/boolean/
null) plus `required` fields and recursive `properties`/`items` —
without `$ref`, `oneOf`/`anyOf`/`allOf`, `pattern`, or `format`
validation. This covers the overwhelming majority of "does this AI
output match the shape my downstream code expects" checks without
pulling in a full JSON Schema implementation; a caller who genuinely
needs full-spec validation can layer the `jsonschema` package in front
of this without this platform needing to depend on it."""
from __future__ import annotations

from dataclasses import dataclass, field

_TYPE_MAP = {
    "object": dict,
    "array": list,
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
    "null": type(None),
}


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)


def _validate(value, schema: dict, path: str, errors: list[str]) -> None:
    expected_type = schema.get("type")
    if expected_type:
        py_type = _TYPE_MAP.get(expected_type)
        if py_type is not None and not isinstance(value, py_type):
            errors.append(f"{path}: expected type '{expected_type}', got '{type(value).__name__}'")
            return

    if expected_type == "object" and isinstance(value, dict):
        for required_field in schema.get("required", []):
            if required_field not in value:
                errors.append(f"{path}: missing required field '{required_field}'")
        properties = schema.get("properties", {})
        for key, sub_schema in properties.items():
            if key in value:
                _validate(value[key], sub_schema, f"{path}.{key}", errors)

    if expected_type == "array" and isinstance(value, list):
        item_schema = schema.get("items")
        if item_schema:
            for i, item in enumerate(value):
                _validate(item, item_schema, f"{path}[{i}]", errors)


def validate_structured_output(data, schema: dict) -> ValidationResult:
    errors: list[str] = []
    _validate(data, schema, "$", errors)
    return ValidationResult(is_valid=not errors, errors=errors)
