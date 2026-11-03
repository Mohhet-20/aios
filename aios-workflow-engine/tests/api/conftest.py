import httpx
import pytest
import pytest_asyncio

from workflow_platform.node_library.registry import seed_node_definitions
from workflow_platform.workflow_api.application_factory import create_app
from workflow_platform.workflow_api.dependencies import get_ai_core, get_repos


@pytest_asyncio.fixture(autouse=True)
async def _seeded_node_definitions(repos):
    """Node definitions are normally seeded once at platform bootstrap
    (see `node_library/registry.seed_node_definitions`) — API tests need
    the same seeding since node-type lookups (e.g. `is_compensable`) hit
    the DB, not the in-memory NODE_TYPE_SPECS registry."""
    await seed_node_definitions(repos)


@pytest.fixture
def app(repos, scripted_ai_core):
    # Note: `_shared_bridge_set`/`_shared_handler_registry` in dependencies.py
    # are plain lru_cache'd functions called directly inside get_execution_engine
    # (not resolved via Depends), so they aren't overridable here. They default
    # to the echo/template reference bridges when no real ai_core is wired in,
    # which is fine for tests that don't exercise LLM_CALL/EMBEDDING_GENERATOR
    # nodes against a real provider.
    context, _provider = scripted_ai_core
    application = create_app()
    application.dependency_overrides[get_repos] = lambda: repos
    application.dependency_overrides[get_ai_core] = lambda: context
    return application


@pytest_asyncio.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", headers={"X-User-Id": "u1"}) as c:
        yield c
