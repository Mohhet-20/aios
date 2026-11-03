import pytest

from tests.conftest import make_response


async def _seed_prompt_and_version(client) -> tuple[str, str, str]:
    """Returns (workspace_id, prompt_id, version_id) for an APPROVED, promoted version."""
    ws = (await client.post("/api/v1/workspaces", json={"name": "WS", "slug": "ws-dom", "organization_id": "org1"})).json()
    proj = (await client.post(f"/api/v1/workspaces/{ws['id']}/projects", json={"name": "Proj", "slug": "proj-dom"})).json()
    prompt = (await client.post("/api/v1/prompts", json={"workspace_id": ws["id"], "project_id": proj["id"], "name": "QA"})).json()
    version = (await client.post(f"/api/v1/prompts/{prompt['id']}/versions", json={"user_template": "Answer {{q}}."})).json()
    await client.post(f"/api/v1/prompts/{prompt['id']}/versions/{version['id']}/submit-for-review")
    await client.post(f"/api/v1/prompts/{prompt['id']}/versions/{version['id']}/approve")
    return ws["id"], prompt["id"], version["id"]


@pytest.mark.asyncio
async def test_studio_validate_and_preview(client):
    body = {"user_template": "Answer {{q}} clearly.", "variables_schema": [{"name": "q"}], "parameters": {}}
    validate_resp = await client.post("/api/v1/studio/validate", json=body)
    assert validate_resp.status_code == 200
    assert validate_resp.json()["is_valid"] is True

    preview_resp = await client.post("/api/v1/studio/preview", json={**body, "variables": {"q": "2+2"}})
    assert preview_resp.status_code == 200
    assert preview_resp.json()["token_estimate"] > 0


@pytest.mark.asyncio
async def test_studio_run_executes_through_ai_core(client, scripted_ai_core):
    _, provider = scripted_ai_core
    provider.push(make_response("4"))
    body = {"user_template": "Answer {{q}}.", "variables": {"q": "2+2"}, "parameters": {"model": "m1", "provider": "test"}}
    resp = await client.post("/api/v1/studio/run", json=body)
    assert resp.status_code == 200
    assert resp.json()["content"] == "4"


@pytest.mark.asyncio
async def test_testing_run_single(client, scripted_ai_core):
    _, provider = scripted_ai_core
    ws_id, prompt_id, version_id = await _seed_prompt_and_version(client)
    provider.push(make_response("4"))

    resp = await client.post(
        f"/api/v1/prompts/{prompt_id}/versions/{version_id}/tests/run-single",
        json={"variables": {"q": "2+2"}, "expected_output": "4"},
    )
    assert resp.status_code == 201
    run = resp.json()
    assert run["summary"]["passed"] == 1


@pytest.mark.asyncio
async def test_evaluation_run_automatic(client, scripted_ai_core):
    _, provider = scripted_ai_core
    ws_id, prompt_id, version_id = await _seed_prompt_and_version(client)
    provider.push(make_response("4"))
    provider.push(make_response('{"score": 90, "rationale": "correct"}'))

    resp = await client.post(
        f"/api/v1/prompts/{prompt_id}/evaluations/automatic",
        json={"version_id": version_id, "test_inputs": [{"q": "2+2"}], "metrics": ["accuracy"]},
    )
    assert resp.status_code == 201
    assert resp.json()["summary"]["overall_score"] == 90.0


@pytest.mark.asyncio
async def test_optimization_suggest(client):
    ws_id, prompt_id, version_id = await _seed_prompt_and_version(client)
    resp = await client.post(f"/api/v1/prompts/{prompt_id}/versions/{version_id}/optimization/suggest", json={"objective": "quality"})
    assert resp.status_code == 201
    assert resp.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_experiments_full_flow(client, scripted_ai_core):
    _, provider = scripted_ai_core
    ws_id, prompt_id, version_id = await _seed_prompt_and_version(client)
    version_b = (await client.post(f"/api/v1/prompts/{prompt_id}/versions", json={"user_template": "Reply to {{q}}."})).json()

    exp = (await client.post("/api/v1/experiments", json={
        "workspace_id": ws_id, "prompt_id": prompt_id, "name": "A/B", "sample_size_per_variant": 1,
    })).json()
    variant_a = (await client.post(f"/api/v1/experiments/{exp['id']}/variants", json={"name": "A", "prompt_version_id": version_id})).json()
    variant_b = (await client.post(f"/api/v1/experiments/{exp['id']}/variants", json={"name": "B", "prompt_version_id": version_b["id"]})).json()
    assert variant_b["name"] == "B"
    start_resp = await client.post(f"/api/v1/experiments/{exp['id']}/start")
    assert start_resp.status_code == 200

    provider.push(make_response("A answer"))
    provider.push(make_response('{"score": 90, "rationale": "good"}'))
    provider.push(make_response("B answer"))
    provider.push(make_response('{"score": 60, "rationale": "meh"}'))

    run_resp = await client.post(f"/api/v1/experiments/{exp['id']}/run", json={"test_inputs": [{"q": "2+2"}]})
    assert run_resp.status_code == 200
    assert run_resp.json()["status"] == "completed"

    summary_resp = await client.get(f"/api/v1/experiments/{exp['id']}/statistical-summary")
    assert summary_resp.status_code == 200
    assert summary_resp.json()["leader_variant_id"] == variant_a["id"]


@pytest.mark.asyncio
async def test_deployment_flow(client):
    ws_id, prompt_id, version_id = await _seed_prompt_and_version(client)
    dep = (await client.post("/api/v1/deployments", json={"prompt_id": prompt_id, "version_id": version_id, "environment": "staging"})).json()
    assert dep["status"] == "pending_approval"

    approve_resp = await client.post(f"/api/v1/deployments/{dep['id']}/approve")
    assert approve_resp.status_code == 200

    deploy_resp = await client.post(f"/api/v1/deployments/{dep['id']}/deploy")
    assert deploy_resp.status_code == 200
    assert deploy_resp.json()["status"] == "deployed"

    current_resp = await client.get(f"/api/v1/deployments/prompts/{prompt_id}/environments/staging/current")
    assert current_resp.status_code == 200
    assert current_resp.json()["id"] == dep["id"]


@pytest.mark.asyncio
async def test_observability_analytics(client, scripted_ai_core):
    _, provider = scripted_ai_core
    ws_id, prompt_id, version_id = await _seed_prompt_and_version(client)
    provider.push(make_response("4"))
    await client.post(
        f"/api/v1/prompts/{prompt_id}/versions/{version_id}/tests/run-single",
        json={"variables": {"q": "2+2"}, "expected_output": "4"},
    )
    resp = await client.get(f"/api/v1/prompts/{prompt_id}/observability/analytics")
    assert resp.status_code == 200
    assert resp.json()["total_executions"] == 1


@pytest.mark.asyncio
async def test_governance_grant_and_compliance_report(client):
    ws_id, prompt_id, version_id = await _seed_prompt_and_version(client)
    grant_resp = await client.post("/api/v1/permissions", json={"resource_type": "prompt", "resource_id": prompt_id, "principal_id": "editor1", "role": "editor"})
    assert grant_resp.status_code == 201

    report_resp = await client.get(f"/api/v1/prompts/{prompt_id}/compliance-report")
    assert report_resp.status_code == 200
    assert report_resp.json()["explicit_grant_count"] == 1


@pytest.mark.asyncio
async def test_security_scan_endpoint(client):
    resp = await client.post("/api/v1/security/scan", json={"text": "Here is a key: sk-abcdefghijklmnopqrstuvwxyz123456"})
    assert resp.status_code == 200
    assert resp.json()["is_safe"] is False


@pytest.mark.asyncio
async def test_import_export_roundtrip(client):
    ws_id, prompt_id, version_id = await _seed_prompt_and_version(client)
    export_resp = await client.get(f"/api/v1/prompts/{prompt_id}/export")
    assert export_resp.status_code == 200
    bundle = export_resp.json()
    assert len(bundle["versions"]) == 1

    import_resp = await client.post("/api/v1/prompts/import", json={
        "workspace_id": ws_id, "project_id": bundle["prompt"]["project_id"], "name": "Imported Copy",
        "versions": [{"user_template": v["user_template"]} for v in bundle["versions"]],
    })
    assert import_resp.status_code == 201
    imported = import_resp.json()
    assert len(imported["versions"]) == 1
    assert imported["prompt"]["name"] == "Imported Copy"
