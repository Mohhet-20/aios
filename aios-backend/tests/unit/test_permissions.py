from app.security.permissions import Permission, Role, permissions_for_role, role_has_permission


def test_owner_has_every_permission():
    for permission in Permission:
        assert role_has_permission(Role.OWNER, permission)


def test_viewer_only_has_read_permissions():
    for permission in Permission:
        has_it = role_has_permission(Role.VIEWER, permission)
        assert has_it == permission.value.endswith(":read")


def test_member_cannot_promote_prompts():
    assert not role_has_permission(Role.MEMBER, Permission.PROMPT_PROMOTE)


def test_admin_can_promote_prompts():
    assert role_has_permission(Role.ADMIN, Permission.PROMPT_PROMOTE)


def test_permissions_for_role_is_sorted_and_stringy():
    perms = permissions_for_role(Role.MEMBER)
    assert perms == sorted(perms)
    assert all(isinstance(p, str) for p in perms)
