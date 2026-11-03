from __future__ import annotations

import pytest

from gateway_platform.core.exceptions import TranslationConfigNotFoundError, UnsupportedTranslationPairError
from gateway_platform.protocols.config_service import ProtocolTranslationConfigService

TENANT = "proto-tenant"


@pytest.mark.asyncio
async def test_register_config_idempotent_by_route_and_pair(repos):
    service = ProtocolTranslationConfigService(repos)
    a = await service.register_config(TENANT, "route-1", translation_pair="rest_graphql")
    b = await service.register_config(TENANT, "route-1", translation_pair="rest_graphql")
    assert a.id == b.id


@pytest.mark.asyncio
async def test_unsupported_translation_pair_rejected(repos):
    service = ProtocolTranslationConfigService(repos)
    with pytest.raises(UnsupportedTranslationPairError):
        await service.register_config(TENANT, "route-2", translation_pair="rest_soap")


@pytest.mark.asyncio
async def test_activate_deactivate_and_get_active_for_pair(repos):
    service = ProtocolTranslationConfigService(repos)
    config = await service.register_config(TENANT, "route-3", translation_pair="rest_websocket")
    assert config.status == "active"

    active = await service.get_active_for_pair(TENANT, "route-3", "rest_websocket")
    assert active.id == config.id

    await service.deactivate_config(TENANT, config.id)
    with pytest.raises(TranslationConfigNotFoundError):
        await service.get_active_for_pair(TENANT, "route-3", "rest_websocket")

    reactivated = await service.activate_config(TENANT, config.id)
    assert reactivated.status == "active"


@pytest.mark.asyncio
async def test_list_for_route(repos):
    service = ProtocolTranslationConfigService(repos)
    await service.register_config(TENANT, "route-4", translation_pair="rest_event_stream")
    configs = await service.list_for_route(TENANT, "route-4")
    assert len(configs) == 1
