import httpx
import pytest
import pytest_asyncio

from agent_platform.agent_api.application_factory import create_app
from agent_platform.agent_api.dependencies import get_ai_core, get_repos


@pytest.fixture
def app(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    application = create_app()
    application.dependency_overrides[get_repos] = lambda: repos
    application.dependency_overrides[get_ai_core] = lambda: context
    return application


@pytest_asyncio.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", headers={"X-User-Id": "u1"}) as c:
        yield c
