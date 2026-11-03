import httpx
import pytest
import pytest_asyncio

from developer_platform.dependencies.dependencies import get_repos
from developer_platform.dev_api.application_factory import create_app


@pytest.fixture
def app(repos):
    application = create_app()
    application.dependency_overrides[get_repos] = lambda: repos
    return application


@pytest_asyncio.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test", headers={"X-Tenant-Id": "api-e2e-tenant", "X-User-Id": "u1"}, trust_env=False
    ) as c:
        yield c
