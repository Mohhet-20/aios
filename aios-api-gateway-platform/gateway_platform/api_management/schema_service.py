"""Request/response schema registry and validation. `validate_payload`
is a deliberately scoped subset of JSON Schema — `type`, `required`,
`properties`, `items`, and `enum` — the same honest-gap posture the
Security Platform's structured-output validator drew: no `$ref`,
`oneOf`/`anyOf`/`allOf`, `pattern`, or `format` support. A payload that
needs those needs a real JSON Schema library, not this gateway's
inline request-shape guard."""
from __future__ import annotations

from gateway_platform.core.exceptions import SchemaValidationError, ValidationError
from gateway_platform.domain.enums import SchemaKind
from gateway_platform.models.api_management import ApiSchemaModel
from gateway_platform.repositories.registry import RepositoryRegistry

_TYPE_MAP = {
    "object": dict,
    "array": list,
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
    "null": type(None),
}


def _validate_node(value: object, schema: dict, *, path: str = "$") -> list[str]:
    errors: list[str] = []
    expected_type = schema.get("type")
    if expected_type is not None:
        py_type = _TYPE_MAP.get(expected_type)
        if py_type is not None and not isinstance(value, py_type):
            errors.append(f"{path}: expected type '{expected_type}', got '{type(value).__name__}'")
            return errors

    if expected_type == "object" and isinstance(value, dict):
        for field in schema.get("required", []):
            if field not in value:
                errors.append(f"{path}: missing required field '{field}'")
        for field, field_schema in (schema.get("properties") or {}).items():
            if field in value:
                errors.extend(_validate_node(value[field], field_schema, path=f"{path}.{field}"))

    if expected_type == "array" and isinstance(value, list):
        item_schema = schema.get("items")
        if item_schema:
            for i, item in enumerate(value):
                errors.extend(_validate_node(item, item_schema, path=f"{path}[{i}]"))

    enum_values = schema.get("enum")
    if enum_values is not None and value not in enum_values:
        errors.append(f"{path}: value '{value}' is not one of {enum_values}")

    return errors


class SchemaValidationService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    def _assert_valid_kind(self, schema_kind: str) -> None:
        if schema_kind not in {k.value for k in SchemaKind}:
            raise ValidationError(f"'{schema_kind}' is not a recognized schema kind")

    async def register_schema(
        self, tenant_id: str, route_id: str, *, schema_kind: str, json_schema: dict,
    ) -> ApiSchemaModel:
        self._assert_valid_kind(schema_kind)
        existing = await self.repos.api_schemas.get_for_route(tenant_id, route_id, schema_kind)
        if existing is not None:
            existing.json_schema = json_schema
            return await self.repos.api_schemas.update(existing)
        record = ApiSchemaModel(tenant_id=tenant_id, route_id=route_id, schema_kind=schema_kind, json_schema=json_schema)
        return await self.repos.api_schemas.add(record)

    async def validate_payload(self, tenant_id: str, route_id: str, *, schema_kind: str, payload: object) -> None:
        schema = await self.repos.api_schemas.get_for_route(tenant_id, route_id, schema_kind)
        if schema is None:
            return  # no registered schema — nothing to validate against
        errors = _validate_node(payload, schema.json_schema)
        if errors:
            raise SchemaValidationError(f"{schema_kind} payload failed schema validation: {'; '.join(errors)}")

    async def list_for_route(self, tenant_id: str, route_id: str) -> list[ApiSchemaModel]:
        return await self.repos.api_schemas.list_for_route(tenant_id, route_id)
