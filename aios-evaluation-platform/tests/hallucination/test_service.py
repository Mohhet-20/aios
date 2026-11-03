import pytest

from eval_platform.core.exceptions import HallucinationCheckError


@pytest.mark.asyncio
async def test_run_check_rejects_empty_claim(service, workspace):
    with pytest.raises(HallucinationCheckError):
        await service.run_check(workspace.id, claim_text="", source_context=["ctx"], subject_type="adhoc")


@pytest.mark.asyncio
async def test_run_check_rejects_missing_context(service, workspace):
    with pytest.raises(HallucinationCheckError):
        await service.run_check(workspace.id, claim_text="a claim", source_context=[], subject_type="adhoc")


@pytest.mark.asyncio
async def test_run_check_grounded_result(service, workspace):
    result = await service.run_check(
        workspace.id, claim_text="Paris is the capital of France.",
        source_context=["Paris is the capital of France."], subject_type="adhoc",
    )
    assert result.grounded is True
    assert result.groundedness_score == 1.0
    assert result.method == "lexical_overlap"
    assert result.unsupported_claims == []


@pytest.mark.asyncio
async def test_run_check_ungrounded_result_lists_unsupported_claims(service, workspace):
    result = await service.run_check(
        workspace.id, claim_text="Bananas grow natively on the moon's surface.",
        source_context=["Paris is the capital of France."], subject_type="adhoc",
    )
    assert result.grounded is False
    assert result.unsupported_claims


@pytest.mark.asyncio
async def test_run_check_validates_citations(service, workspace):
    result = await service.run_check(
        workspace.id, claim_text="This is supported [1] but this citation is invalid [9].",
        source_context=["doc a"], subject_type="adhoc",
    )
    valid = {c["index"]: c["valid"] for c in result.citations_checked}
    assert valid[1] is True
    assert valid[9] is False


@pytest.mark.asyncio
async def test_run_check_computes_consistency_across_repeated_claims(service, workspace):
    result = await service.run_check(
        workspace.id, claim_text="the sky is blue", source_context=["the sky appears blue during the day"],
        subject_type="adhoc", repeated_claims=["the sky is blue", "the sky is completely green"],
    )
    assert result.consistency_score is not None
    assert 0.0 < result.consistency_score < 1.0


@pytest.mark.asyncio
async def test_run_check_persists_and_is_listable(service, workspace, repos):
    result = await service.run_check(
        workspace.id, claim_text="Paris is the capital of France.",
        source_context=["Paris is the capital of France."], subject_type="evaluation_item", subject_id="item-1",
    )
    fetched = await service.list_for_subject("evaluation_item", "item-1")
    assert len(fetched) == 1
    assert fetched[0].id == result.id
