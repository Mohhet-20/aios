import pytest

from workflow_platform.core.exceptions import VariableResolutionError
from workflow_platform.domain.enums import VariableScope
from workflow_platform.state.variable_service import VariableService


@pytest.mark.asyncio
async def test_set_and_get_variable_roundtrips_any_json_type(repos):
    svc = VariableService(repos)
    await svc.set_variable(VariableScope.WORKSPACE, "ws-1", "max_retries", 5)
    await svc.set_variable(VariableScope.WORKSPACE, "ws-1", "enabled", True)
    await svc.set_variable(VariableScope.WORKSPACE, "ws-1", "tags", ["a", "b"])

    assert await svc.get_variable(VariableScope.WORKSPACE, "ws-1", "max_retries") == 5
    assert await svc.get_variable(VariableScope.WORKSPACE, "ws-1", "enabled") is True
    assert await svc.get_variable(VariableScope.WORKSPACE, "ws-1", "tags") == ["a", "b"]


@pytest.mark.asyncio
async def test_get_missing_variable_returns_default(repos):
    svc = VariableService(repos)
    assert await svc.get_variable(VariableScope.GLOBAL, "global", "nope", default="fallback") == "fallback"


@pytest.mark.asyncio
async def test_set_variable_twice_updates_in_place(repos):
    svc = VariableService(repos)
    await svc.set_variable(VariableScope.WORKFLOW, "wf-1", "k", "v1")
    await svc.set_variable(VariableScope.WORKFLOW, "wf-1", "k", "v2")
    assert await svc.get_variable(VariableScope.WORKFLOW, "wf-1", "k") == "v2"
    all_vars = await svc.list_for_scope(VariableScope.WORKFLOW, "wf-1")
    assert len(all_vars) == 1  # updated, not duplicated


@pytest.mark.asyncio
async def test_delete_variable(repos):
    svc = VariableService(repos)
    await svc.set_variable(VariableScope.WORKFLOW, "wf-1", "k", "v")
    assert await svc.delete_variable(VariableScope.WORKFLOW, "wf-1", "k") is True
    assert await svc.delete_variable(VariableScope.WORKFLOW, "wf-1", "k") is False
    assert await svc.get_variable(VariableScope.WORKFLOW, "wf-1", "k") is None


@pytest.mark.asyncio
async def test_resolve_scope_chain_most_specific_wins(repos):
    svc = VariableService(repos)
    await svc.set_variable(VariableScope.GLOBAL, "global", "region", "us-global")
    await svc.set_variable(VariableScope.WORKSPACE, "ws-1", "region", "us-workspace")
    await svc.set_variable(VariableScope.WORKFLOW, "wf-1", "region", "us-workflow")
    await svc.set_variable(VariableScope.GLOBAL, "global", "only_global", "g")

    merged = await svc.resolve_scope_chain(workflow_id="wf-1", workspace_id="ws-1", global_scope_id="global")
    assert merged["region"] == "us-workflow"  # workflow beats workspace beats global
    assert merged["only_global"] == "g"


@pytest.mark.asyncio
async def test_resolve_template_substitutes_from_merged_scopes(repos):
    svc = VariableService(repos)
    await svc.set_variable(VariableScope.WORKSPACE, "ws-1", "api_base", "https://api.example.com")
    result = await svc.resolve_template("GET {{api_base}}/v1/status", workspace_id="ws-1")
    assert result == "GET https://api.example.com/v1/status"


@pytest.mark.asyncio
async def test_resolve_template_extra_takes_highest_precedence(repos):
    svc = VariableService(repos)
    await svc.set_variable(VariableScope.WORKSPACE, "ws-1", "name", "from-scope")
    result = await svc.resolve_template("hello {{name}}", workspace_id="ws-1", extra={"name": "from-context"})
    assert result == "hello from-context"


@pytest.mark.asyncio
async def test_resolve_template_raises_on_unknown_variable(repos):
    svc = VariableService(repos)
    with pytest.raises(VariableResolutionError):
        await svc.resolve_template("hello {{missing}}", workspace_id="ws-1")


@pytest.mark.asyncio
async def test_secret_variable_is_encrypted_at_rest(repos):
    svc = VariableService(repos)
    await svc.set_variable(VariableScope.WORKSPACE, "ws-1", "api_key", "sk-super-secret-value", is_secret=True)

    raw_model = await repos.variables.get_by_key(VariableScope.WORKSPACE.value, "ws-1", "api_key")
    assert raw_model.is_secret is True
    assert "sk-super-secret-value" not in raw_model.value["v"]  # stored ciphertext, not plaintext

    assert await svc.get_variable(VariableScope.WORKSPACE, "ws-1", "api_key") == "sk-super-secret-value"


@pytest.mark.asyncio
async def test_secrets_excluded_from_scope_chain_by_default(repos):
    svc = VariableService(repos)
    await svc.set_variable(VariableScope.WORKSPACE, "ws-1", "api_key", "sk-secret", is_secret=True)
    await svc.set_variable(VariableScope.WORKSPACE, "ws-1", "region", "us-east", is_secret=False)

    merged = await svc.resolve_scope_chain(workspace_id="ws-1")
    assert "region" in merged
    assert "api_key" not in merged

    merged_with_secrets = await svc.resolve_scope_chain(workspace_id="ws-1", include_secrets=True)
    assert merged_with_secrets["api_key"] == "sk-secret"


@pytest.mark.asyncio
async def test_resolve_template_does_not_leak_secret_by_default(repos):
    svc = VariableService(repos)
    await svc.set_variable(VariableScope.WORKSPACE, "ws-1", "api_key", "sk-secret", is_secret=True)

    with pytest.raises(VariableResolutionError):
        await svc.resolve_template("Authorization: Bearer {{api_key}}", workspace_id="ws-1")

    result = await svc.resolve_template("Authorization: Bearer {{api_key}}", workspace_id="ws-1", include_secrets=True)
    assert result == "Authorization: Bearer sk-secret"
