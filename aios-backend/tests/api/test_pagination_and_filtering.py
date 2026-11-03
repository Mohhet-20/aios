import pytest


@pytest.mark.asyncio
async def test_workspace_filter_by_organization(client, auth_headers):
    await client.post(
        "/api/v1/workspaces", json={"organization_id": "filter-org-1", "name": "A"}, headers=auth_headers
    )
    await client.post(
        "/api/v1/workspaces", json={"organization_id": "filter-org-1", "name": "B"}, headers=auth_headers
    )
    await client.post(
        "/api/v1/workspaces", json={"organization_id": "filter-org-2", "name": "C"}, headers=auth_headers
    )

    r = await client.get(
        "/api/v1/workspaces", params={"organization_id": "filter-org-1"}, headers=auth_headers
    )
    assert r.status_code == 200
    names = {w["name"] for w in r.json()}
    assert names == {"A", "B"}
