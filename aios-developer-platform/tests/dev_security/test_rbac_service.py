import uuid

import pytest

from developer_platform.core.exceptions import PermissionDeniedError
from developer_platform.dev_security.rbac_service import DeveloperRbacService

pytestmark = pytest.mark.asyncio


def _tid() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


async def test_grant_and_require_role(repos, db_session):
    tenant_id = _tid()
    service = DeveloperRbacService(repos)
    await service.grant_role(tenant_id, principal_id="dev-1", role="operator")
    await db_session.commit()

    role = await service.get_effective_role(tenant_id, "dev-1")
    assert role.value == "operator"

    await service.require_role(tenant_id, "dev-1", minimum_role="viewer")
    with pytest.raises(PermissionDeniedError):
        await service.require_role(tenant_id, "dev-1", minimum_role="admin")


async def test_no_binding_denies_everything(repos, db_session):
    service = DeveloperRbacService(repos)
    with pytest.raises(PermissionDeniedError):
        await service.require_role(_tid(), "nobody", minimum_role="viewer")


async def test_scoped_binding_overrides_global(repos, db_session):
    tenant_id = _tid()
    service = DeveloperRbacService(repos)
    await service.grant_role(tenant_id, principal_id="dev-2", role="viewer")
    await service.grant_role(tenant_id, principal_id="dev-2", role="admin", scope="plugin:my-plugin")
    await db_session.commit()

    global_role = await service.get_effective_role(tenant_id, "dev-2")
    assert global_role.value == "viewer"

    scoped_role = await service.get_effective_role(tenant_id, "dev-2", scope="plugin:my-plugin")
    assert scoped_role.value == "admin"


async def test_regrant_updates_existing_binding(repos, db_session):
    tenant_id = _tid()
    service = DeveloperRbacService(repos)
    await service.grant_role(tenant_id, principal_id="dev-3", role="viewer")
    await db_session.commit()
    await service.grant_role(tenant_id, principal_id="dev-3", role="admin")
    await db_session.commit()

    bindings = await service.list_for_principal(tenant_id, "dev-3")
    assert len(bindings) == 1
    assert bindings[0].role == "admin"
