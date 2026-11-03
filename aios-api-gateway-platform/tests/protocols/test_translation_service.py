from __future__ import annotations

import pytest

from gateway_platform.protocols.config_service import ProtocolTranslationConfigService
from gateway_platform.protocols.translation_service import ProtocolTranslationService

TENANT = "proto-svc-tenant"


@pytest.mark.asyncio
async def test_translate_request_and_response_dispatch_by_pair(repos):
    configs = ProtocolTranslationConfigService(repos)
    await configs.register_config(
        TENANT, "route-a", translation_pair="rest_graphql",
        config={"operation_name": "GetUser", "field_map": {"user_id": "userId"}},
    )
    service = ProtocolTranslationService(repos, config_service=configs)

    request = await service.translate_request(
        TENANT, "route-a", translation_pair="rest_graphql", payload={"user_id": "42"},
    )
    assert request["operationName"] == "GetUser"
    assert request["variables"] == {"userId": "42"}

    response = await service.translate_response(
        TENANT, "route-a", translation_pair="rest_graphql", payload={"data": {"userId": "42", "name": "Ann"}},
    )
    assert response == {"user_id": "42", "name": "Ann"}


@pytest.mark.asyncio
async def test_translate_version_static_helper():
    result = ProtocolTranslationService.translate_version(
        {"old_field": "x", "drop_me": True}, field_renames={"old_field": "new_field"}, field_removals=["drop_me"],
    )
    assert result == {"new_field": "x"}


@pytest.mark.asyncio
async def test_translate_auth_static_helper():
    result = ProtocolTranslationService.translate_auth(
        {"Authorization": "Bearer secret"}, auth_mode="bearer_to_apikey",
    )
    assert result == {"X-API-Key": "secret"}
