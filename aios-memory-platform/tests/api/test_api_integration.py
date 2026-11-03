import pytest


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
@pytest.mark.asyncio
async def test_health_liveness_probe(client):
    resp = await client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "alive"}


@pytest.mark.asyncio
async def test_health_readiness_probe(client):
    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["components"][0]["name"] == "database"
    assert body["components"][0]["healthy"] is True



@pytest.mark.asyncio
async def test_workspace_crud(client):
    resp = await client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme", "organization_id": "org-1"})
    assert resp.status_code == 201
    ws = resp.json()
    assert ws["name"] == "Acme"

    resp = await client.get("/api/v1/workspaces", params={"organization_id": "org-1"})
    assert resp.status_code == 200
    assert any(w["id"] == ws["id"] for w in resp.json())

    resp = await client.get(f"/api/v1/workspaces/{ws['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == ws["id"]


@pytest.mark.asyncio
async def test_workspace_not_found_returns_404(client):
    resp = await client.get("/api/v1/workspaces/does-not-exist")
    assert resp.status_code == 404
    assert resp.json()["error"] == "NotFoundError"


@pytest.mark.asyncio
async def test_memory_lifecycle_end_to_end(client, repos):
    from memory_platform.memory_registry.seed_types import seed_builtin_memory_types
    await seed_builtin_memory_types(repos)
    ws = (await client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme", "organization_id": "org-1"})).json()
    ws_id = ws["id"]

    resp = await client.post(f"/api/v1/workspaces/{ws_id}/memory", json={
        "memory_type": "semantic", "scope_type": "user", "scope_id": "u-1", "content": "Paris is the capital of France.",
    })
    assert resp.status_code == 201
    entry = resp.json()
    assert entry["status"] == "active"

    resp = await client.get(f"/api/v1/workspaces/{ws_id}/memory/{entry['id']}")
    assert resp.status_code == 200
    assert resp.json()["access_count"] == 1

    resp = await client.get(f"/api/v1/workspaces/{ws_id}/memory", params={"scope_type": "user", "scope_id": "u-1"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.get(f"/api/v1/workspaces/{ws_id}/memory/search", params={"query": "Paris"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.put(f"/api/v1/workspaces/{ws_id}/memory/{entry['id']}/content", json={"content": "Paris is France's capital, pop. 2.1M."})
    assert resp.status_code == 200
    assert resp.json()["version"] == 2

    resp = await client.post(f"/api/v1/workspaces/{ws_id}/memory/{entry['id']}/archive")
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"

    resp = await client.post(f"/api/v1/workspaces/{ws_id}/memory/{entry['id']}/restore")
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"

    resp = await client.post(f"/api/v1/workspaces/{ws_id}/memory/{entry['id']}/supersede", json={"content": "Updated fact."})
    assert resp.status_code == 201
    new_entry = resp.json()
    assert new_entry["id"] != entry["id"]

    resp = await client.get(f"/api/v1/workspaces/{ws_id}/memory/{entry['id']}/audit-history")
    assert resp.status_code == 200
    actions = {a["action"] for a in resp.json()}
    assert "memory.create" in actions
    assert "memory.supersede" in actions

    resp = await client.delete(f"/api/v1/workspaces/{ws_id}/memory/{new_entry['id']}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_conversation_episodic_working_memory_endpoints(client, repos):
    from memory_platform.memory_registry.seed_types import seed_builtin_memory_types
    await seed_builtin_memory_types(repos)
    ws_id = (await client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme", "organization_id": "org-1"})).json()["id"]

    resp = await client.post(f"/api/v1/workspaces/{ws_id}/memory/conversations/turns", json={
        "conversation_id": "conv-1", "scope_type": "user", "scope_id": "u-1", "role": "user", "content": "Hi there",
    })
    assert resp.status_code == 201
    resp = await client.get(f"/api/v1/workspaces/{ws_id}/memory/conversations/conv-1/transcript")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.post(f"/api/v1/workspaces/{ws_id}/memory/episodes", json={
        "scope_type": "agent", "scope_id": "agent-1", "description": "deployed v1",
    })
    assert resp.status_code == 201
    import datetime as dt
    now = dt.datetime.now(dt.timezone.utc)
    resp = await client.get(f"/api/v1/workspaces/{ws_id}/memory/episodes", params={
        "scope_type": "agent", "scope_id": "agent-1",
        "start": (now - dt.timedelta(hours=1)).isoformat(), "end": (now + dt.timedelta(hours=1)).isoformat(),
    })
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.put(f"/api/v1/workspaces/{ws_id}/memory/working-memory/focus", json={"session_id": "sess-1", "content": "current task"})
    assert resp.status_code == 200
    resp = await client.get(f"/api/v1/workspaces/{ws_id}/memory/working-memory/focus", params={"session_id": "sess-1"})
    assert resp.status_code == 200
    assert resp.json()["content"] == "current task"
    resp = await client.delete(f"/api/v1/workspaces/{ws_id}/memory/working-memory/focus", params={"session_id": "sess-1"})
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_knowledge_workflow_end_to_end(client):
    ws_id = (await client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme", "organization_id": "org-1"})).json()["id"]

    resp = await client.post(f"/api/v1/workspaces/{ws_id}/knowledge/bases", json={"name": "Product KB", "slug": "product-kb"})
    assert resp.status_code == 201
    kb = resp.json()

    resp = await client.post(f"/api/v1/workspaces/{ws_id}/knowledge/items", json={"knowledge_base_id": kb["id"], "title": "Setup Guide", "content": "Step 1..."})
    assert resp.status_code == 201
    item = resp.json()
    assert item["status"] == "draft"

    resp = await client.get(f"/api/v1/workspaces/{ws_id}/knowledge/items/search", params={"query": "setup"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.post(f"/api/v1/workspaces/{ws_id}/knowledge/items/{item['id']}/submit-for-review")
    assert resp.status_code == 200
    resp = await client.post(f"/api/v1/workspaces/{ws_id}/knowledge/items/{item['id']}/publish")
    assert resp.status_code == 200
    assert resp.json()["status"] == "published"

    resp = await client.get(f"/api/v1/workspaces/{ws_id}/knowledge/items/{item['id']}/versions")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    item2 = (await client.post(f"/api/v1/workspaces/{ws_id}/knowledge/items", json={"knowledge_base_id": kb["id"], "title": "Related Guide", "content": "More content"})).json()
    resp = await client.post(f"/api/v1/workspaces/{ws_id}/knowledge/items/{item['id']}/related", json={"related_item_id": item2["id"]})
    assert resp.status_code == 201
    resp = await client.get(f"/api/v1/workspaces/{ws_id}/knowledge/items/{item['id']}/related")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_document_upload_and_process(client):
    ws_id = (await client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme", "organization_id": "org-1"})).json()["id"]

    files = {"file": ("notes.md", b"# Notes\n\nSome useful content here.", "text/markdown")}
    data = {"document_type": "markdown", "title": "Notes", "classify": "false", "generate_embeddings": "false"}
    resp = await client.post(f"/api/v1/workspaces/{ws_id}/documents/upload", files=files, data=data)
    assert resp.status_code == 201
    doc = resp.json()
    assert doc["status"] == "processed"

    resp = await client.get(f"/api/v1/workspaces/{ws_id}/documents")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.get(f"/api/v1/workspaces/{ws_id}/documents/{doc['id']}/chunks")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_vector_index_and_search(client):
    ws_id = (await client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme", "organization_id": "org-1"})).json()["id"]

    resp = await client.post(f"/api/v1/workspaces/{ws_id}/vectors/index", json={
        "source_type": "document_chunk", "items": [["c1", "the quick brown fox", {}], ["c2", "jumps over the lazy dog", {}]],
    })
    assert resp.status_code == 201
    assert len(resp.json()) == 2

    resp = await client.get(f"/api/v1/workspaces/{ws_id}/vectors/indexes")
    assert resp.status_code == 200
    assert "default" in resp.json()

    resp = await client.get(f"/api/v1/workspaces/{ws_id}/vectors/indexes/default/health")
    assert resp.status_code == 200
    assert resp.json()["healthy"] is True

    resp = await client.get(f"/api/v1/workspaces/{ws_id}/vectors/search", params={"query": "fox", "top_k": 2})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_retrieval_endpoints(client, repos):
    from memory_platform.memory_registry.seed_types import seed_builtin_memory_types
    await seed_builtin_memory_types(repos)
    ws_id = (await client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme", "organization_id": "org-1"})).json()["id"]
    await client.post(f"/api/v1/workspaces/{ws_id}/memory", json={
        "memory_type": "project", "scope_type": "project", "scope_id": "proj-1", "content": "deployment runbook for project alpha",
    })

    resp = await client.get(f"/api/v1/workspaces/{ws_id}/retrieval/keyword", params={"query": "runbook"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.get(f"/api/v1/workspaces/{ws_id}/retrieval/hybrid", params={"query": "runbook"})
    assert resp.status_code == 200

    resp = await client.get(f"/api/v1/workspaces/{ws_id}/retrieval/project-aware/proj-1", params={"query": "runbook"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.get(f"/api/v1/workspaces/{ws_id}/retrieval/multi-stage", params={"query": "runbook", "scope_type": "project", "scope_id": "proj-1"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_knowledge_graph_endpoints(client):
    ws_id = (await client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme", "organization_id": "org-1"})).json()["id"]

    a = (await client.post(f"/api/v1/workspaces/{ws_id}/graph/entities", json={"entity_type": "concept", "name": "A"})).json()
    b = (await client.post(f"/api/v1/workspaces/{ws_id}/graph/entities", json={"entity_type": "concept", "name": "B"})).json()
    resp = await client.post(f"/api/v1/workspaces/{ws_id}/graph/relationships", json={"source_entity_id": a["id"], "target_entity_id": b["id"], "relation_type": "related_to"})
    assert resp.status_code == 201

    resp = await client.get(f"/api/v1/workspaces/{ws_id}/graph/entities/{a['id']}/neighbors")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.get(f"/api/v1/workspaces/{ws_id}/graph/entities/{a['id']}/traverse")
    assert resp.status_code == 200
    assert b["id"] in resp.json()["visited_entity_ids"]

    resp = await client.get(f"/api/v1/workspaces/{ws_id}/graph/entities/{a['id']}/shortest-path/{b['id']}")
    assert resp.status_code == 200
    assert resp.json()["path"] == [a["id"], b["id"]]

    resp = await client.get(f"/api/v1/workspaces/{ws_id}/graph/entities/search", params={"query": "A"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_context_assembly_endpoint(client, repos):
    from memory_platform.memory_registry.seed_types import seed_builtin_memory_types
    await seed_builtin_memory_types(repos)
    ws_id = (await client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme", "organization_id": "org-1"})).json()["id"]
    await client.post(f"/api/v1/workspaces/{ws_id}/memory", json={
        "memory_type": "semantic", "scope_type": "user", "scope_id": "u-1", "content": "The support SLA is 24 hours.",
        "title": "Support SLA",
    })

    resp = await client.post(f"/api/v1/workspaces/{ws_id}/context/assemble", json={"query": "support SLA"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["items_included"] == 1
    assert len(body["citations"]) == 1


@pytest.mark.asyncio
async def test_governance_endpoints(client):
    ws_id = (await client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme", "organization_id": "org-1"})).json()["id"]

    resp = await client.post(f"/api/v1/workspaces/{ws_id}/governance/rbac/grants", json={
        "principal_id": "user-2", "resource_type": "workspace", "resource_id": ws_id, "role": "admin",
    })
    assert resp.status_code == 201
    grant = resp.json()

    resp = await client.get(f"/api/v1/workspaces/{ws_id}/governance/rbac/resolve-role", params={"principal_id": "user-2"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"

    resp = await client.delete(f"/api/v1/workspaces/{ws_id}/governance/rbac/grants/{grant['id']}")
    assert resp.status_code == 204

    resp = await client.post(f"/api/v1/workspaces/{ws_id}/governance/retention-policies", json={
        "retention_days": 30, "action_on_expiry": "archive", "memory_type": "session",
    })
    assert resp.status_code == 201
    resp = await client.get(f"/api/v1/workspaces/{ws_id}/governance/retention-policies")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.post(f"/api/v1/workspaces/{ws_id}/governance/audit-log", json={
        "action": "knowledge_base.create", "resource_type": "knowledge_base", "resource_id": "kb-1",
    })
    assert resp.status_code == 201
    resp = await client.get(f"/api/v1/workspaces/{ws_id}/governance/audit-log/knowledge_base/kb-1")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.get(f"/api/v1/workspaces/{ws_id}/governance/compliance")
    assert resp.status_code == 200
    assert resp.json()["active_retention_policy_count"] == 1


@pytest.mark.asyncio
async def test_observability_endpoints(client, repos):
    from memory_platform.memory_registry.seed_types import seed_builtin_memory_types
    await seed_builtin_memory_types(repos)
    ws_id = (await client.post("/api/v1/workspaces", json={"name": "Acme", "slug": "acme", "organization_id": "org-1"})).json()["id"]
    await client.post(f"/api/v1/workspaces/{ws_id}/memory", json={
        "memory_type": "semantic", "scope_type": "user", "scope_id": "u-1", "content": "observability test fact",
    })
    await client.get(f"/api/v1/workspaces/{ws_id}/retrieval/multi-stage", params={"query": "observability test"})

    resp = await client.get(f"/api/v1/workspaces/{ws_id}/analytics/retrieval-performance")
    assert resp.status_code == 200
    assert resp.json()["total_queries"] == 1

    resp = await client.get(f"/api/v1/workspaces/{ws_id}/analytics/memory")
    assert resp.status_code == 200
    assert resp.json()["entries_created_in_window"] == 1

    resp = await client.get(f"/api/v1/workspaces/{ws_id}/analytics/storage-usage")
    assert resp.status_code == 200
    assert resp.json()["memory_entry_count"] == 1


@pytest.mark.asyncio
async def test_missing_auth_header_returns_401(app):
    import httpx
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post("/api/v1/workspaces/ws-x/memory", json={
            "memory_type": "semantic", "scope_type": "user", "scope_id": "u-1", "content": "no auth",
        })
        assert resp.status_code == 401
