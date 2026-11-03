import pytest

from eval_platform.core.exceptions import RecommendationError


@pytest.mark.asyncio
async def test_create_recommendation_requires_evidence(recommendation_service, workspace):
    with pytest.raises(RecommendationError):
        await recommendation_service.create_recommendation(
            workspace.id, category="cost_optimization", target_type="evaluation", title="x", description="y", evidence={},
        )


@pytest.mark.asyncio
async def test_create_recommendation_rejects_unknown_category(recommendation_service, workspace):
    with pytest.raises(RecommendationError):
        await recommendation_service.create_recommendation(
            workspace.id, category="not_real", target_type="evaluation", title="x", description="y", evidence={"a": 1},
        )


@pytest.mark.asyncio
async def test_create_and_accept_recommendation(recommendation_service, workspace):
    rec = await recommendation_service.create_recommendation(
        workspace.id, category="cost_optimization", target_type="evaluation", title="Cut cost", description="y", evidence={"a": 1},
    )
    assert rec.status == "open"
    accepted = await recommendation_service.accept(rec.id)
    assert accepted.status == "accepted"
    assert accepted.resolved_at is not None


@pytest.mark.asyncio
async def test_dismiss_recommendation(recommendation_service, workspace):
    rec = await recommendation_service.create_recommendation(
        workspace.id, category="reliability", target_type="evaluation", title="x", description="y", evidence={"a": 1},
    )
    dismissed = await recommendation_service.dismiss(rec.id)
    assert dismissed.status == "dismissed"


@pytest.mark.asyncio
async def test_cannot_resolve_twice(recommendation_service, workspace):
    rec = await recommendation_service.create_recommendation(
        workspace.id, category="reliability", target_type="evaluation", title="x", description="y", evidence={"a": 1},
    )
    await recommendation_service.accept(rec.id)
    with pytest.raises(RecommendationError):
        await recommendation_service.dismiss(rec.id)


@pytest.mark.asyncio
async def test_list_recommendations_filters(recommendation_service, workspace):
    a = await recommendation_service.create_recommendation(workspace.id, category="cost_optimization", target_type="evaluation", title="a", description="d", evidence={"x": 1})
    await recommendation_service.create_recommendation(workspace.id, category="reliability", target_type="evaluation", title="b", description="d", evidence={"x": 1})
    await recommendation_service.accept(a.id)

    open_recs = await recommendation_service.list_recommendations(workspace.id, status="open")
    assert len(open_recs) == 1
    cost_recs = await recommendation_service.list_recommendations(workspace.id, category="cost_optimization")
    assert len(cost_recs) == 1
