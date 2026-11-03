"""Drives the platform purely through HTTP, end to end, across every
domain — the same style as every prior AIOS platform's API test
suite. Uses a dedicated tenant id (`api-e2e-tenant`, set in
conftest.py's `client` fixture) rather than the generic ids used
throughout the unit-level test suites, to keep this suite's state
isolated from those."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


async def test_health_probe(client):
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



async def test_documentation_flow(client):
    resp = await client.post("/api/v1/doc-spaces", json={"key": "api-space", "name": "API Space", "doc_type": "developer"})
    assert resp.status_code == 201
    space = resp.json()

    resp = await client.post("/api/v1/doc-pages", json={
        "space_id": space["id"], "title": "Getting Started", "slug": "getting-started", "doc_type": "developer", "content": "hello world",
    })
    assert resp.status_code == 201
    page = resp.json()
    assert page["status"] == "draft"

    resp = await client.put(f"/api/v1/doc-pages/{page['id']}/content", json={"content": "hello world v2"})
    assert resp.status_code == 200
    assert resp.json()["current_version"] == 2

    resp = await client.post(f"/api/v1/doc-pages/{page['id']}/submit-for-review")
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_review"

    resp = await client.post(f"/api/v1/doc-pages/{page['id']}/publish")
    assert resp.status_code == 200
    assert resp.json()["status"] == "published"

    resp = await client.get(f"/api/v1/doc-spaces/{space['id']}/pages")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_api_sdk_docs_and_automation_flow(client):
    resp = await client.post("/api/v1/api-docs", json={"protocol_type": "rest", "path": "/v1/widgets", "method": "GET"})
    assert resp.status_code == 201

    resp = await client.post("/api/v1/sdk-docs", json={"sdk_language": "python", "package_ref": "aios-sdk", "title": "Quickstart"})
    assert resp.status_code == 201

    resp = await client.get("/api/v1/sdk-docs/by-language/python")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.post("/api/v1/generation-jobs", json={"job_type": "api_docs", "target_ref": "svc:api-e2e"})
    assert resp.status_code == 201
    job = resp.json()

    resp = await client.post(f"/api/v1/generation-jobs/{job['id']}/run")
    assert resp.status_code == 200
    finished = resp.json()
    assert finished["status"] == "completed"


async def test_architecture_flow(client):
    resp = await client.post("/api/v1/diagrams", json={"diagram_type": "system_overview", "title": "System Overview"})
    assert resp.status_code == 201
    system = resp.json()

    resp = await client.post("/api/v1/diagrams", json={
        "diagram_type": "component", "title": "Component A", "related_refs": [system["id"]],
    })
    assert resp.status_code == 201

    resp = await client.get(f"/api/v1/diagrams/{system['id']}/related")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.post("/api/v1/tech-stack", json={"category": "backend", "name": "FastAPI"})
    assert resp.status_code == 201


async def test_knowledge_base_flow(client):
    resp = await client.post("/api/v1/kb-articles", json={
        "article_type": "troubleshooting", "title": "Fix login issues", "slug": "fix-login-issues", "content": "restart the service",
    })
    assert resp.status_code == 201
    article = resp.json()

    resp = await client.post(f"/api/v1/kb-articles/{article['id']}/publish")
    assert resp.status_code == 200
    assert resp.json()["status"] == "published"


async def test_learning_flow(client):
    resp = await client.post("/api/v1/tutorials", json={"tutorial_type": "getting_started", "title": "Intro", "role": "developer"})
    assert resp.status_code == 201
    tutorial = resp.json()

    resp = await client.post("/api/v1/enrollments", json={"user_id": "learner-1", "tutorial_id": tutorial["id"]})
    assert resp.status_code == 201
    enrollment = resp.json()
    assert enrollment["status"] == "enrolled"

    resp = await client.put(f"/api/v1/enrollments/{enrollment['id']}/progress", json={"progress_pct": 100.0})
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


async def test_assistant_flow(client):
    resp = await client.post("/api/v1/kb-articles", json={
        "article_type": "faq", "title": "Deploy Workflow Engine", "slug": "deploy-workflow-engine", "content": "deploy workflow engine steps",
    })
    article = resp.json()
    await client.post(f"/api/v1/kb-articles/{article['id']}/publish")

    resp = await client.post("/api/v1/assistant/ask", json={"question": "deploy workflow engine"})
    assert resp.status_code == 201
    session = resp.json()
    assert session["answer"] is not None

    resp = await client.post("/api/v1/assistant/summarize", json={"text": "Sentence one. Sentence two. Sentence three. Sentence four."})
    assert resp.status_code == 200
    assert "summary" in resp.json()


async def test_search_flow(client):
    resp = await client.post("/api/v1/doc-spaces", json={"key": "search-space", "name": "Search Space", "doc_type": "developer"})
    space = resp.json()
    resp = await client.post("/api/v1/doc-pages", json={
        "space_id": space["id"], "title": "Search Target", "slug": "search-target", "doc_type": "developer", "content": "unique searchable content",
    })
    page = resp.json()
    await client.post(f"/api/v1/doc-pages/{page['id']}/submit-for-review")
    await client.post(f"/api/v1/doc-pages/{page['id']}/publish")

    resp = await client.get("/api/v1/search", params={"q": "unique searchable content"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


async def test_versioning_flow(client):
    resp = await client.post("/api/v1/doc-spaces", json={"key": "ver-space", "name": "Ver Space", "doc_type": "developer"})
    space = resp.json()
    resp = await client.post("/api/v1/doc-pages", json={
        "space_id": space["id"], "title": "Versioned Page", "slug": "versioned-page", "doc_type": "developer", "content": "v1 content",
    })
    page = resp.json()
    await client.put(f"/api/v1/doc-pages/{page['id']}/content", json={"content": "v2 content"})

    resp = await client.get(f"/api/v1/doc-versions/{page['id']}")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp = await client.get(f"/api/v1/doc-versions/{page['id']}/diff/1/2")
    assert resp.status_code == 200
    assert "diff" in resp.json()

    resp = await client.post("/api/v1/release-notes", json={"version_label": "v1.4", "title": "Big release", "kind": "feature"})
    assert resp.status_code == 201

    resp = await client.post("/api/v1/deprecation-notices", json={"subject_ref": "api:old-endpoint", "message": "use v2 instead"})
    assert resp.status_code == 201


async def test_collaboration_flow(client):
    resp = await client.post("/api/v1/doc-spaces", json={"key": "collab-space", "name": "Collab Space", "doc_type": "developer"})
    space = resp.json()
    resp = await client.post("/api/v1/doc-pages", json={
        "space_id": space["id"], "title": "Collab Page", "slug": "collab-page", "doc_type": "developer",
    })
    page = resp.json()

    resp = await client.post("/api/v1/comments", json={"target_ref": f"page:{page['id']}", "author_id": "u2", "body": "needs work"})
    assert resp.status_code == 201
    comment = resp.json()

    resp = await client.post(f"/api/v1/comments/{comment['id']}/resolve")
    assert resp.status_code == 200
    assert resp.json()["resolved"] is True

    resp = await client.post("/api/v1/reviews", json={"page_id": page["id"], "requested_by": "u1"})
    assert resp.status_code == 201
    review = resp.json()

    resp = await client.post(f"/api/v1/reviews/{review['id']}/decide", json={"decision": "approved", "reviewer_id": "u3"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

    resp = await client.get(f"/api/v1/audit-log/by-target/page:{page['id']}")
    assert resp.status_code == 200


async def test_analytics_flow(client):
    resp = await client.post("/api/v1/analytics/events", json={"event_type": "page_view", "subject_ref": "page:api-e2e"})
    assert resp.status_code == 201

    resp = await client.get("/api/v1/analytics/most-viewed")
    assert resp.status_code == 200

    resp = await client.post("/api/v1/feedback", json={"subject_ref": "page:api-e2e", "score": 5})
    assert resp.status_code == 201

    resp = await client.get("/api/v1/feedback/by-subject/page:api-e2e/average")
    assert resp.status_code == 200
    assert resp.json()["average_score"] == 5.0

    resp = await client.post("/api/v1/broken-links", json={"source_ref": "page:api-e2e", "url": "https://dead.example.com"})
    assert resp.status_code == 201
    link = resp.json()

    resp = await client.post(f"/api/v1/broken-links/{link['id']}/resolve")
    assert resp.status_code == 200
    assert resp.json()["resolved"] is True


async def test_security_flow(client):
    resp = await client.post("/api/v1/roles", json={"user_id": "sec-user", "role": "editor"})
    assert resp.status_code == 201

    resp = await client.get("/api/v1/roles/by-user/sec-user")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.post("/api/v1/doc-spaces", json={"key": "sec-space", "name": "Sec Space", "doc_type": "developer"})
    space = resp.json()
    resp = await client.post("/api/v1/doc-pages", json={
        "space_id": space["id"], "title": "Internal Page", "slug": "internal-page", "doc_type": "developer", "visibility": "internal",
    })
    page = resp.json()

    resp = await client.get(f"/api/v1/visibility/can-view/{page['id']}", params={"user_id": "sec-user"})
    assert resp.status_code == 200
    assert resp.json()["can_view"] is True

    resp = await client.get(f"/api/v1/visibility/can-view/{page['id']}")
    assert resp.status_code == 200
    assert resp.json()["can_view"] is False

    resp = await client.get(f"/api/v1/governance/is-editable/{page['id']}")
    assert resp.status_code == 200
    assert resp.json()["editable"] is True

    await client.post(f"/api/v1/doc-pages/{page['id']}/submit-for-review")
    await client.post(f"/api/v1/doc-pages/{page['id']}/publish")

    resp = await client.get(f"/api/v1/governance/is-editable/{page['id']}")
    assert resp.status_code == 200
    assert resp.json()["editable"] is False
