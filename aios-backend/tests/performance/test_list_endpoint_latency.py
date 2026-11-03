"""Lightweight performance smoke test (not a substitute for a real load
test with Locust/k6 against a running deployment): asserts a paginated list
endpoint stays under a generous latency budget with a moderate number of
rows, catching an accidental N+1 query before it reaches production.
"""

import time

import pytest


@pytest.mark.asyncio
async def test_list_agents_latency_is_reasonable(client, auth_headers):
    workspace_id = "perf-ws"
    for i in range(25):
        await client.post(
            "/api/v1/agents",
            json={"workspace_id": workspace_id, "name": f"Agent {i}", "role": "Classifier", "model_id": "m1"},
            headers=auth_headers,
        )

    start = time.perf_counter()
    r = await client.get("/api/v1/agents", params={"workspace_id": workspace_id}, headers=auth_headers)
    duration = time.perf_counter() - start

    assert r.status_code == 200
    assert len(r.json()) == 25
    assert duration < 2.0, f"Listing 25 agents took {duration:.2f}s — investigate for N+1 queries"
