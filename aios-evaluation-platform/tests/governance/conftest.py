import pytest

from eval_platform.governance.audit_service import AuditService
from eval_platform.governance.policy_service import EvaluationPolicyService
from eval_platform.governance.rbac_service import RBACService
from eval_platform.governance.retention_service import RetentionService
from eval_platform.models.workspace import WorkspaceModel


@pytest.fixture
async def workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="Governance Co", organization_id="org-1", slug="governance-co"))


@pytest.fixture
def rbac_service(repos):
    return RBACService(repos)


@pytest.fixture
def audit_service(repos):
    return AuditService(repos)


@pytest.fixture
def policy_service(repos):
    return EvaluationPolicyService(repos)


@pytest.fixture
def retention_service(repos):
    return RetentionService(repos)
