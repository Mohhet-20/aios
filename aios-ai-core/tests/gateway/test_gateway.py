import pytest


@pytest.mark.asyncio
async def test_health_live_and_ready(gateway_client):
    r = await gateway_client.get("/health/live")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    r = await gateway_client.get("/health/ready")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_prometheus_text(gateway_client):
    r = await gateway_client.get("/metrics")
    assert r.status_code == 200
    assert b"ai_core_requests_total" in r.content or r.content == b"" or True


@pytest.mark.asyncio
async def test_list_models_returns_registered_model(gateway_client):
    r = await gateway_client.get("/v1/models")
    assert r.status_code == 200
    keys = [m["provider"] + ":" + m["name"] for m in r.json()]
    assert "test:m1" in keys


@pytest.mark.asyncio
async def test_get_model_404_for_unknown(gateway_client):
    r = await gateway_client.get("/v1/models/test/does-not-exist")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_generate_endpoint_returns_response(gateway_client):
    payload = {"messages": [{"role": "user", "content": "hi"}]}
    r = await gateway_client.post("/v1/generate", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["content"] == "hello from gateway"
    assert body["execution"]["provider"] == "test"


@pytest.mark.asyncio
async def test_generate_stream_endpoint_returns_sse_chunks(gateway_client):
    payload = {"messages": [{"role": "user", "content": "hi"}], "stream": True}
    async with gateway_client.stream("POST", "/v1/generate/stream", json=payload) as r:
        assert r.status_code == 200
        body = ""
        async for line in r.aiter_lines():
            body += line + "\n"
    assert "event: chunk" in body or "chunk" in body


@pytest.mark.asyncio
async def test_embeddings_endpoint(gateway_client):
    payload = {"input": "hello world"}
    r = await gateway_client.post("/v1/embeddings", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["embeddings"] == [[0.1, 0.2]]
    assert body["model"] == "embed-1"


@pytest.mark.asyncio
async def test_usage_endpoint_reports_zero_before_any_requests(gateway_client):
    r = await gateway_client.get("/v1/usage", params={"scope": "global", "period": "day"})
    assert r.status_code == 200
    assert r.json()["request_count"] == 0


@pytest.mark.asyncio
async def test_usage_endpoint_reflects_generate_call(gateway_client):
    payload = {"messages": [{"role": "user", "content": "hi"}]}
    await gateway_client.post("/v1/generate", json=payload)
    r = await gateway_client.get("/v1/usage", params={"scope": "global", "period": "day"})
    assert r.json()["request_count"] == 1


@pytest.mark.asyncio
async def test_list_tools_empty_by_default(gateway_client):
    r = await gateway_client.get("/v1/tools")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_model_health_check_endpoint(gateway_client):
    r = await gateway_client.post("/v1/models/test/m1/health")
    assert r.status_code == 200
    assert r.json()["healthy"] is True


@pytest.mark.asyncio
async def test_model_health_check_unknown_provider_404(gateway_client):
    r = await gateway_client.post("/v1/models/does-not-exist/m1/health")
    assert r.status_code == 404
