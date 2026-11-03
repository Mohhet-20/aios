import httpx
import pytest
import pytest_asyncio

from tool_platform.dependencies.dependencies import get_ai_core, get_repos
from tool_platform.tool_api.application_factory import create_app


class _FakeEmbeddingEngine:
    async def embed(self, request):
        class _Result:
            embeddings = [[0.1, 0.2, 0.3]]
            dimensions = 3
        return _Result()


class _FakeAiCore:
    embedding_engine = _FakeEmbeddingEngine()


@pytest.fixture
def app(repos):
    application = create_app()
    application.dependency_overrides[get_repos] = lambda: repos
    application.dependency_overrides[get_ai_core] = lambda: _FakeAiCore()
    return application


@pytest_asyncio.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", headers={"X-User-Id": "u1"}) as c:
        yield c
