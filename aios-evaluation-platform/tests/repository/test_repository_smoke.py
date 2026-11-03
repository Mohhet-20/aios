import pytest

from eval_platform.models.evaluation import EvaluationModel, EvaluationVersionModel
from eval_platform.models.workspace import WorkspaceModel


@pytest.mark.asyncio
async def test_workspace_and_evaluation_crud_roundtrip(repos):
    ws = await repos.workspaces.add(WorkspaceModel(name="Repo Co", organization_id="org-1", slug="repo-co"))
    assert ws.id

    evaluation = await repos.evaluations.add(EvaluationModel(
        workspace_id=ws.id, organization_id="org-1", name="Groundedness Check", slug="groundedness-check",
        category="groundedness", owner_id="u1",
    ))
    fetched = await repos.evaluations.get_or_404(evaluation.id)
    assert fetched.name == "Groundedness Check"

    version = await repos.evaluation_versions.add(EvaluationVersionModel(
        evaluation_id=evaluation.id, version_number=1, created_by="u1",
    ))
    versions = await repos.evaluation_versions.list_for_evaluation(evaluation.id)
    assert len(versions) == 1
    assert versions[0].id == version.id

    listed = await repos.evaluations.list_for_workspace(ws.id)
    assert len(listed) == 1

    await repos.evaluations.delete(evaluation)
    listed_after_delete = await repos.evaluations.list_for_workspace(ws.id)
    assert listed_after_delete == []
