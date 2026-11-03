import pytest

from tool_platform.config.settings import Settings
from tool_platform.governance.approval_service import ApprovalService
from tool_platform.governance.audit_service import AuditService
from tool_platform.governance.policy_engine import PolicyEngine
from tool_platform.governance.rbac_service import RBACService
from tool_platform.models.workspace import WorkspaceModel
from tool_platform.tool_core.tool_service import ToolService
from tool_platform.tool_core.version_service import ToolVersionService
from tool_platform.tool_execution.engine import ToolExecutionEngine
from tool_platform.tool_execution.registry import build_default_connector_registry


@pytest.fixture
async def workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="Governance Co", organization_id="org-1", slug="governance-co"))


@pytest.fixture
async def other_workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="Other Co", organization_id="org-2", slug="other-co"))


@pytest.fixture
def tool_service(repos):
    return ToolService(repos)


@pytest.fixture
def version_service(repos):
    return ToolVersionService(repos)


@pytest.fixture
def rbac(repos):
    return RBACService(repos)


@pytest.fixture
def policy_engine(repos):
    return PolicyEngine(repos, Settings(rate_limit_calls_per_minute=1000, max_concurrent_tool_executions=1000, workspace_max_concurrent_executions=1000))


@pytest.fixture
def tight_policy_engine(repos):
    """A PolicyEngine with deliberately tiny limits, for tests that need
    to actually trip the guardrails."""
    return PolicyEngine(repos, Settings(rate_limit_calls_per_minute=2, max_concurrent_tool_executions=1000, workspace_max_concurrent_executions=1000))


@pytest.fixture
def approval_service(repos):
    return ApprovalService(repos)


@pytest.fixture
def audit_service(repos):
    return AuditService(repos)


@pytest.fixture
def engine(repos, policy_engine, approval_service, audit_service):
    return ToolExecutionEngine(
        repos, build_default_connector_registry(),
        policy_engine=policy_engine, approval_service=approval_service, audit_service=audit_service,
    )


async def make_published_tool(
    tool_service, version_service, workspace, *, name="Test Tool", category="custom", connector_key="echo",
    sensitivity_level="normal", default_max_retries=0,
):
    tool = await tool_service.create_tool(workspace.id, name=name, owner_id="u1", category=category, organization_id=workspace.organization_id)
    draft = await version_service.get_or_create_draft(tool.id, created_by="u1")
    await version_service.update_draft(
        draft.id, connector_key=connector_key, sensitivity_level=sensitivity_level,
        default_max_retries=default_max_retries, default_timeout_seconds=10, default_retry_backoff_seconds=0.01,
    )
    published = await version_service.publish_version(draft.id)
    return tool, published
