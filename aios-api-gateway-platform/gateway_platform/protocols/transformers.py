"""Real payload/schema/auth transformation functions for each
supported translation pair. Deliberately plain, stateless functions
(not classes) -- each takes the payload/headers plus the config JSON
blob attached to a `ProtocolTranslationConfigModel` row and returns a
new, transformed dict. Kept small and dependency-free rather than
reaching for a real GraphQL/WebSocket/event-stream library, matching
this platform's disclosed boundary elsewhere (e.g. `SchemaValidationService`
in api_management): field-mapping-and-envelope transformation, not a
full protocol implementation."""
from __future__ import annotations

from typing import Any

from gateway_platform.core.exceptions import ProtocolTranslationError


def _apply_field_map(payload: dict[str, Any], field_map: dict[str, str]) -> dict[str, Any]:
    """Rename keys per `field_map` (old_name -> new_name); keys not
    mentioned pass through unchanged."""
    result = dict(payload)
    for old_name, new_name in field_map.items():
        if old_name in result:
            result[new_name] = result.pop(old_name)
    return result


# -- REST <-> GraphQL --------------------------------------------------------------------------

def rest_to_graphql(payload: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    operation = config.get("operation_name", "GatewayOperation")
    field_map = config.get("field_map", {})
    variables = _apply_field_map(payload, field_map)
    return {"operationName": operation, "query": config.get("query", f"query {operation} {{ }}"), "variables": variables}


def graphql_to_rest(response: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    if "errors" in response and response["errors"]:
        raise ProtocolTranslationError(f"GraphQL response contained errors: {response['errors']}")
    data = response.get("data", {})
    reverse_map = {v: k for k, v in config.get("field_map", {}).items()}
    return _apply_field_map(data, reverse_map)


# -- REST <-> WebSocket -------------------------------------------------------------------------

def rest_to_websocket_frame(payload: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    frame_type = config.get("frame_type", "message")
    return {"type": frame_type, "data": payload}


def websocket_frame_to_rest(frame: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    expected_type = config.get("frame_type", "message")
    if frame.get("type") != expected_type:
        raise ProtocolTranslationError(f"expected websocket frame type '{expected_type}', got '{frame.get('type')}'")
    return dict(frame.get("data", {}))


# -- REST <-> Event Stream ----------------------------------------------------------------------

def rest_to_event(payload: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    event_type = config.get("event_type", "gateway.request")
    return {"event_type": event_type, "payload": payload}


def event_to_rest(event: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    expected_type = config.get("event_type", "gateway.request")
    if event.get("event_type") != expected_type:
        raise ProtocolTranslationError(f"expected event type '{expected_type}', got '{event.get('event_type')}'")
    return dict(event.get("payload", {}))


# -- API version translation ---------------------------------------------------------------------

def translate_version(payload: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Applies `field_renames` (old -> new) then drops any key listed
    in `field_removals` -- a deliberately simple schema-shift model,
    enough to carry a payload across a documented breaking change
    without needing a general schema-migration DSL."""
    result = _apply_field_map(payload, config.get("field_renames", {}))
    for removed_field in config.get("field_removals", []):
        result.pop(removed_field, None)
    return result


# -- Authentication transformation ---------------------------------------------------------------

def translate_auth(headers: dict[str, str], config: dict[str, Any]) -> dict[str, str]:
    """Converts between a bearer-token header and an API-key header,
    per `auth_mode` in config: "bearer_to_apikey" or "apikey_to_bearer".
    Not a token exchange -- it carries the same credential value across
    header conventions, it does not mint a new credential."""
    auth_mode = config.get("auth_mode")
    api_key_header = config.get("api_key_header", "X-API-Key")
    result = dict(headers)

    if auth_mode == "bearer_to_apikey":
        auth_header = result.pop("Authorization", None)
        if auth_header and auth_header.startswith("Bearer "):
            result[api_key_header] = auth_header[len("Bearer "):]
    elif auth_mode == "apikey_to_bearer":
        api_key = result.pop(api_key_header, None)
        if api_key:
            result["Authorization"] = f"Bearer {api_key}"
    return result


REQUEST_TRANSFORMERS = {
    "rest_graphql": rest_to_graphql,
    "rest_websocket": rest_to_websocket_frame,
    "rest_event_stream": rest_to_event,
}

RESPONSE_TRANSFORMERS = {
    "rest_graphql": graphql_to_rest,
    "rest_websocket": websocket_frame_to_rest,
    "rest_event_stream": event_to_rest,
}
