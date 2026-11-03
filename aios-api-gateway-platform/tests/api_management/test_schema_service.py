from __future__ import annotations

import pytest

from gateway_platform.api_management.schema_service import SchemaValidationService
from gateway_platform.core.exceptions import SchemaValidationError, ValidationError

TENANT = "am-schema-tenant"
ROUTE = "route-1"


@pytest.mark.asyncio
async def test_register_and_validate_valid_payload(repos):
    service = SchemaValidationService(repos)
    schema = {
        "type": "object",
        "required": ["name"],
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
    }
    await service.register_schema(TENANT, ROUTE, schema_kind="request", json_schema=schema)
    await service.validate_payload(TENANT, ROUTE, schema_kind="request", payload={"name": "widget", "age": 3})


@pytest.mark.asyncio
async def test_validate_missing_required_field_raises(repos):
    service = SchemaValidationService(repos)
    schema = {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}}
    await service.register_schema(TENANT, ROUTE, schema_kind="request", json_schema=schema)
    with pytest.raises(SchemaValidationError):
        await service.validate_payload(TENANT, ROUTE, schema_kind="request", payload={})


@pytest.mark.asyncio
async def test_validate_wrong_type_raises(repos):
    service = SchemaValidationService(repos)
    schema = {"type": "object", "properties": {"age": {"type": "integer"}}}
    await service.register_schema(TENANT, ROUTE, schema_kind="response", json_schema=schema)
    with pytest.raises(SchemaValidationError):
        await service.validate_payload(TENANT, ROUTE, schema_kind="response", payload={"age": "not-a-number"})


@pytest.mark.asyncio
async def test_validate_with_no_registered_schema_is_noop(repos):
    service = SchemaValidationService(repos)
    await service.validate_payload(TENANT, "no-such-route", schema_kind="request", payload={"anything": 1})


@pytest.mark.asyncio
async def test_invalid_schema_kind_rejected(repos):
    service = SchemaValidationService(repos)
    with pytest.raises(ValidationError):
        await service.register_schema(TENANT, ROUTE, schema_kind="bogus", json_schema={})


@pytest.mark.asyncio
async def test_array_and_enum_validation(repos):
    service = SchemaValidationService(repos)
    schema = {
        "type": "object",
        "properties": {
            "tags": {"type": "array", "items": {"type": "string"}},
            "status": {"type": "string", "enum": ["draft", "active"]},
        },
    }
    await service.register_schema(TENANT, "route-2", schema_kind="request", json_schema=schema)
    await service.validate_payload(TENANT, "route-2", schema_kind="request", payload={"tags": ["a", "b"], "status": "draft"})
    with pytest.raises(SchemaValidationError):
        await service.validate_payload(TENANT, "route-2", schema_kind="request", payload={"status": "unknown"})
