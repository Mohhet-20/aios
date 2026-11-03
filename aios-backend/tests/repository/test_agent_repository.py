import pytest

from app.models.agent import AgentModel
from app.repositories.agent_repository import AgentRepository


@pytest.mark.asyncio
async def test_list_by_workspace(db_session):
    repo = AgentRepository(db_session)
    await repo.add(AgentModel(workspace_id="ws-a", name="Agent 1", role="Classifier", model_id="m1"))
    await repo.add(AgentModel(workspace_id="ws-a", name="Agent 2", role="Retriever", model_id="m1"))
    await repo.add(AgentModel(workspace_id="ws-b", name="Agent 3", role="Classifier", model_id="m1"))

    results = await repo.list_by_workspace("ws-a")
    assert len(results) == 2
