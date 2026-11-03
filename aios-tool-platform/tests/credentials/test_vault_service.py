from datetime import datetime, timedelta, timezone

import pytest

from tool_platform.core.exceptions import ValidationError


@pytest.mark.asyncio
async def test_create_and_get_secret_roundtrip(vault_service, workspace):
    cred = await vault_service.create_credential(
        workspace.id, name="GitHub PAT", credential_type="api_key", secret_material={"api_key": "ghp_secret123"}, owner_id="u1",
    )
    assert cred.encrypted_payload != "ghp_secret123"  # never plaintext at rest
    secret = await vault_service.get_secret(cred.id)
    assert secret == {"api_key": "ghp_secret123"}


@pytest.mark.asyncio
async def test_get_secret_updates_last_used_at(vault_service, workspace, repos):
    cred = await vault_service.create_credential(workspace.id, name="C", credential_type="api_key", secret_material={"api_key": "x"}, owner_id="u1")
    assert cred.last_used_at is None
    await vault_service.get_secret(cred.id)
    refreshed = await repos.credentials.get_or_404(cred.id)
    assert refreshed.last_used_at is not None


@pytest.mark.asyncio
async def test_get_secret_rejects_revoked(vault_service, workspace):
    cred = await vault_service.create_credential(workspace.id, name="C", credential_type="api_key", secret_material={"api_key": "x"}, owner_id="u1")
    await vault_service.revoke_credential(cred.id)
    with pytest.raises(ValidationError):
        await vault_service.get_secret(cred.id)


@pytest.mark.asyncio
async def test_rotate_credential_changes_ciphertext(vault_service, workspace, repos):
    cred = await vault_service.create_credential(workspace.id, name="C", credential_type="api_key", secret_material={"api_key": "old"}, owner_id="u1")
    old_ciphertext = cred.encrypted_payload
    rotated = await vault_service.rotate_credential(cred.id, new_secret_material={"api_key": "new"})
    assert rotated.encrypted_payload != old_ciphertext
    assert rotated.status == "active"
    assert rotated.rotated_at is not None
    secret = await vault_service.get_secret(cred.id)
    assert secret == {"api_key": "new"}


@pytest.mark.asyncio
async def test_sweep_expirations_transitions_expired_credentials(vault_service, workspace, repos):
    past = datetime.now(timezone.utc) - timedelta(seconds=1)
    cred = await vault_service.create_credential(
        workspace.id, name="Expiring", credential_type="api_key", secret_material={"api_key": "x"}, owner_id="u1", expires_at=past,
    )
    expired = await vault_service.sweep_expirations(workspace_id=workspace.id)
    assert cred.id in {c.id for c in expired}
    refreshed = await repos.credentials.get_or_404(cred.id)
    assert refreshed.status == "expired"


@pytest.mark.asyncio
async def test_sweep_expirations_leaves_unexpired_alone(vault_service, workspace, repos):
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    cred = await vault_service.create_credential(
        workspace.id, name="Fresh", credential_type="api_key", secret_material={"api_key": "x"}, owner_id="u1", expires_at=future,
    )
    expired = await vault_service.sweep_expirations(workspace_id=workspace.id)
    assert cred.id not in {c.id for c in expired}


@pytest.mark.asyncio
async def test_bind_credential_to_tool_and_lookup_default(vault_service, workspace, repos):
    from tool_platform.models.tool import ToolModel
    tool = await repos.tools.add(ToolModel(workspace_id=workspace.id, organization_id="org-1", name="T", slug="t", owner_id="u1", category="github"))
    cred = await vault_service.create_credential(workspace.id, name="GH", credential_type="oauth2", secret_material={"access_token": "abc"}, owner_id="u1")
    await vault_service.bind_to_tool(tool.id, workspace.id, cred.id)
    default_cred = await vault_service.get_default_credential_for_tool(tool.id, workspace.id)
    assert default_cred.id == cred.id


@pytest.mark.asyncio
async def test_rebinding_default_credential_demotes_old_default(vault_service, workspace, repos):
    from tool_platform.models.tool import ToolModel
    tool = await repos.tools.add(ToolModel(workspace_id=workspace.id, organization_id="org-1", name="T2", slug="t2", owner_id="u1", category="github"))
    cred1 = await vault_service.create_credential(workspace.id, name="GH1", credential_type="oauth2", secret_material={"access_token": "a"}, owner_id="u1")
    cred2 = await vault_service.create_credential(workspace.id, name="GH2", credential_type="oauth2", secret_material={"access_token": "b"}, owner_id="u1")
    await vault_service.bind_to_tool(tool.id, workspace.id, cred1.id)
    await vault_service.bind_to_tool(tool.id, workspace.id, cred2.id)

    default_cred = await vault_service.get_default_credential_for_tool(tool.id, workspace.id)
    assert default_cred.id == cred2.id

    bindings = await repos.tool_credential_bindings.list_for_tool(tool.id)
    assert sum(1 for b in bindings if b.is_default) == 1
