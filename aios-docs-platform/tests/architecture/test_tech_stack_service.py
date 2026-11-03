import pytest

from docs_platform.architecture.tech_stack_service import TechStackService

pytestmark = pytest.mark.asyncio


async def test_add_entry_and_list(repos):
    svc = TechStackService(repos)
    await svc.add_entry("t-arch", category="backend", name="FastAPI", version_info="0.111.0")
    await svc.add_entry("t-arch", category="frontend", name="Next.js")
    backend_only = await svc.list_entries("t-arch", category="backend")
    assert len(backend_only) == 1
    assert backend_only[0].name == "FastAPI"
