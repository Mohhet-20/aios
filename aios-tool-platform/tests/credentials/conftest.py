import pytest

from tool_platform.credentials.vault_service import VaultService
from tool_platform.models.workspace import WorkspaceModel
from tool_platform.security.encryption import SecretsEncryptor


@pytest.fixture
async def workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="Vault Co", organization_id="org-1", slug="vault-co"))


@pytest.fixture
def vault_service(repos):
    return VaultService(repos, encryptor=SecretsEncryptor("test-secret-key-32-chars-minimum!!"))
