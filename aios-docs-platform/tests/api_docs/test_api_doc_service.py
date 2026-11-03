import pytest

from docs_platform.api_docs.api_doc_service import ApiDocService
from docs_platform.core.exceptions import UnsupportedApiProtocolError

pytestmark = pytest.mark.asyncio


async def test_create_entry_rejects_unsupported_protocol(repos):
    svc = ApiDocService(repos)
    with pytest.raises(UnsupportedApiProtocolError):
        await svc.create_entry("t1", protocol_type="not-a-protocol", path="/v1/x")


async def test_create_and_fetch_entry(repos):
    svc = ApiDocService(repos)
    entry = await svc.create_entry(
        "t1", protocol_type="rest", path="/v1/workflows", method="POST",
        summary="Create a workflow", request_example={"name": "demo"}, response_example={"id": "wf_1"},
    )
    assert entry.protocol_type == "rest"
    fetched = await svc.get_by_path("t1", "rest", "/v1/workflows", method="POST")
    assert fetched is not None
    assert fetched.id == entry.id


async def test_list_entries_filters_by_protocol(repos):
    svc = ApiDocService(repos)
    await svc.create_entry("t1", protocol_type="graphql", path="/graphql")
    await svc.create_entry("t1", protocol_type="websocket", path="/ws")
    graphql_only = await svc.list_entries("t1", protocol_type="graphql")
    assert len(graphql_only) == 1
