import pytest

from docs_platform.core.exceptions import DocSpaceNotFoundError, UnsupportedDocTypeError
from docs_platform.documentation.doc_space_service import DocSpaceService

pytestmark = pytest.mark.asyncio


async def test_register_space_creates_new(repos):
    svc = DocSpaceService(repos)
    space = await svc.register_space("t1", key="arch-space", name="Architecture", doc_type="architecture")
    assert space.doc_type == "architecture"


async def test_register_space_is_idempotent_by_key(repos):
    svc = DocSpaceService(repos)
    first = await svc.register_space("t1", key="api-space", name="API", doc_type="api")
    second = await svc.register_space("t1", key="api-space", name="API (renamed)", doc_type="api")
    assert first.id == second.id
    assert second.name == "API"  # get-or-create: second call's differing name is not applied


async def test_register_space_rejects_unsupported_doc_type(repos):
    svc = DocSpaceService(repos)
    with pytest.raises(UnsupportedDocTypeError):
        await svc.register_space("t1", key="bad-space", name="Bad", doc_type="not-a-type")


async def test_get_or_404_cross_tenant(repos):
    svc = DocSpaceService(repos)
    space = await svc.register_space("t1", key="tenant-space", name="Tenant", doc_type="developer")
    with pytest.raises(DocSpaceNotFoundError):
        await svc.get_or_404("t2", space.id)
