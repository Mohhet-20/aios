import pytest


@pytest.mark.asyncio
async def test_write_and_query_semantic_memory(client, auth_headers):
    r = await client.post(
        "/api/v1/memory",
        json={
            "workspace_id": "ws-mem",
            "memory_type": "semantic",
            "scope": "kb",
            "content": "Refund policy is 30 days.",
        },
        headers=auth_headers,
    )
    assert r.status_code == 200

    r = await client.post(
        "/api/v1/memory/query",
        json={"workspace_id": "ws-mem", "query": "refund policy", "memory_type": "semantic", "top_k": 3},
        headers=auth_headers,
    )
    assert r.status_code == 200
    results = r.json()
    assert len(results) >= 1
    assert results[0]["relevance"] is not None
