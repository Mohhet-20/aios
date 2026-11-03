import pytest

from memory_platform.core.exceptions import AuthorizationError
from memory_platform.governance.isolation import enforce_organization_isolation, enforce_workspace_isolation
from memory_platform.models.workspace import WorkspaceModel


def test_enforce_workspace_isolation_passes_when_matching():
    enforce_workspace_isolation("ws-1", "ws-1")  # no raise


def test_enforce_workspace_isolation_raises_when_mismatched():
    with pytest.raises(AuthorizationError):
        enforce_workspace_isolation("ws-1", "ws-2")


def test_enforce_organization_isolation_passes_when_matching():
    ws = WorkspaceModel(id="ws-1", name="Acme", slug="acme", organization_id="org-1")
    enforce_organization_isolation(ws, "org-1")  # no raise


def test_enforce_organization_isolation_raises_when_mismatched():
    ws = WorkspaceModel(id="ws-1", name="Acme", slug="acme", organization_id="org-1")
    with pytest.raises(AuthorizationError):
        enforce_organization_isolation(ws, "org-2")
