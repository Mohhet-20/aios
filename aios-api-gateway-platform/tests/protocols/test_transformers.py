from __future__ import annotations

import pytest

from gateway_platform.core.exceptions import ProtocolTranslationError
from gateway_platform.protocols.transformers import (
    event_to_rest,
    graphql_to_rest,
    rest_to_event,
    rest_to_graphql,
    rest_to_websocket_frame,
    translate_auth,
    translate_version,
    websocket_frame_to_rest,
)


def test_rest_to_graphql_and_back():
    config = {"operation_name": "GetOrder", "field_map": {"order_id": "orderId"}}
    gql = rest_to_graphql({"order_id": "123"}, config)
    assert gql["operationName"] == "GetOrder"
    assert gql["variables"] == {"orderId": "123"}

    rest = graphql_to_rest({"data": {"orderId": "123", "status": "shipped"}}, config)
    assert rest == {"order_id": "123", "status": "shipped"}


def test_graphql_to_rest_raises_on_errors():
    with pytest.raises(ProtocolTranslationError):
        graphql_to_rest({"errors": [{"message": "boom"}]}, {})


def test_rest_to_websocket_round_trip():
    config = {"frame_type": "order.event"}
    frame = rest_to_websocket_frame({"id": 1}, config)
    assert frame == {"type": "order.event", "data": {"id": 1}}
    rest = websocket_frame_to_rest(frame, config)
    assert rest == {"id": 1}


def test_websocket_frame_to_rest_rejects_wrong_type():
    with pytest.raises(ProtocolTranslationError):
        websocket_frame_to_rest({"type": "other", "data": {}}, {"frame_type": "order.event"})


def test_rest_to_event_round_trip():
    config = {"event_type": "order.created"}
    event = rest_to_event({"id": 7}, config)
    assert event == {"event_type": "order.created", "payload": {"id": 7}}
    rest = event_to_rest(event, config)
    assert rest == {"id": 7}


def test_event_to_rest_rejects_wrong_type():
    with pytest.raises(ProtocolTranslationError):
        event_to_rest({"event_type": "other", "payload": {}}, {"event_type": "order.created"})


def test_translate_version_renames_and_removes():
    config = {"field_renames": {"user_id": "userId"}, "field_removals": ["legacy_flag"]}
    result = translate_version({"user_id": "u1", "legacy_flag": True, "name": "Ann"}, config)
    assert result == {"userId": "u1", "name": "Ann"}


def test_translate_auth_bearer_to_apikey():
    headers = {"Authorization": "Bearer abc123"}
    result = translate_auth(headers, {"auth_mode": "bearer_to_apikey", "api_key_header": "X-API-Key"})
    assert result == {"X-API-Key": "abc123"}


def test_translate_auth_apikey_to_bearer():
    headers = {"X-API-Key": "abc123"}
    result = translate_auth(headers, {"auth_mode": "apikey_to_bearer", "api_key_header": "X-API-Key"})
    assert result == {"Authorization": "Bearer abc123"}
