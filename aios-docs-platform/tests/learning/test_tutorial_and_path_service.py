import pytest

from docs_platform.core.exceptions import LearningError, UnsupportedTutorialTypeError
from docs_platform.learning.learning_path_service import LearningPathService
from docs_platform.learning.tutorial_service import TutorialService

pytestmark = pytest.mark.asyncio

TENANT = "t-learning"


async def test_create_tutorial_rejects_unsupported_type(repos):
    svc = TutorialService(repos)
    with pytest.raises(UnsupportedTutorialTypeError):
        await svc.create_tutorial(TENANT, tutorial_type="not-a-type", title="X", role="developer")


async def test_create_tutorial_rejects_unsupported_role(repos):
    svc = TutorialService(repos)
    with pytest.raises(LearningError):
        await svc.create_tutorial(TENANT, tutorial_type="getting_started", title="X", role="not-a-role")


async def test_create_tutorial_defaults_pass_threshold(repos):
    svc = TutorialService(repos)
    tutorial = await svc.create_tutorial(TENANT, tutorial_type="hands_on_lab", title="Lab 1", role="developer")
    assert tutorial.pass_threshold_pct == svc.settings.tutorial_pass_threshold_pct


async def test_list_tutorials_filters_by_role(repos):
    svc = TutorialService(repos)
    await svc.create_tutorial(TENANT, tutorial_type="getting_started", title="Admin 101", role="administrator")
    await svc.create_tutorial(TENANT, tutorial_type="getting_started", title="Dev 101", role="developer")
    admin_only = await svc.list_tutorials(TENANT, role="administrator")
    assert len(admin_only) == 1


async def test_create_learning_path(repos):
    svc = LearningPathService(repos)
    path = await svc.create_path(TENANT, name="Developer Track", role="developer", tutorial_ids=["t1", "t2"])
    assert path.tutorial_ids == ["t1", "t2"]
    paths = await svc.list_paths(TENANT, role="developer")
    assert len(paths) == 1
