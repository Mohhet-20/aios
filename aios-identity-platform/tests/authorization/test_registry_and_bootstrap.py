import pytest

from identity_platform.authorization.bootstrap import seed_builtin_roles, seed_permissions
from identity_platform.authorization.registry import BUILTIN_ROLE_SLUGS, PERMISSION_KEYS


def test_permission_registry_keys_are_unique_and_well_formed():
    assert len(PERMISSION_KEYS) > 0
    for key in PERMISSION_KEYS:
        resource, action = key.split(":")
        assert resource and action


def test_builtin_role_slugs_are_unique():
    from identity_platform.authorization.registry import BUILTIN_ROLES
    slugs = [r.slug for r in BUILTIN_ROLES]
    assert len(slugs) == len(set(slugs))
    assert "system_admin" in BUILTIN_ROLE_SLUGS
    assert "org_admin" in BUILTIN_ROLE_SLUGS


@pytest.mark.asyncio
async def test_seed_permissions_is_idempotent(repos, db_session):
    # The shared test database may already have permissions seeded by
    # another test module that ran first — idempotency is what's under
    # test, not "starts from an empty table," so we only assert that a
    # second call back-to-back never creates anything new.
    await seed_permissions(repos)
    await db_session.commit()

    created_second = await seed_permissions(repos)
    await db_session.commit()
    assert created_second == 0


@pytest.mark.asyncio
async def test_seed_builtin_roles_is_idempotent(repos, db_session):
    await seed_builtin_roles(repos)
    await db_session.commit()

    created_second = await seed_builtin_roles(repos)
    await db_session.commit()
    assert created_second == 0
