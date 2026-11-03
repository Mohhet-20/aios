import pytest

from eval_platform.hallucination.verifier import LexicalOverlapVerifier


@pytest.mark.asyncio
async def test_fully_grounded_claim():
    verifier = LexicalOverlapVerifier()
    outcome = await verifier.verify(
        "Paris is the capital of France.", ["Paris is the capital city of France, located on the Seine river."]
    )
    assert outcome.groundedness_score == 1.0
    assert outcome.unsupported_claims == []


@pytest.mark.asyncio
async def test_partially_grounded_claim_flags_unsupported_sentence():
    verifier = LexicalOverlapVerifier()
    outcome = await verifier.verify(
        "Paris is the capital of France. Bananas grow on the moon.",
        ["Paris is the capital of France."],
    )
    assert 0.0 < outcome.groundedness_score < 1.0
    assert "Bananas grow on the moon" in outcome.unsupported_claims


@pytest.mark.asyncio
async def test_empty_claim_returns_zero_score_no_crash():
    verifier = LexicalOverlapVerifier()
    outcome = await verifier.verify("   ", ["some context"])
    assert outcome.groundedness_score == 0.0
    assert outcome.sentence_verdicts == []


@pytest.mark.asyncio
async def test_trivial_sentence_marked_supported_but_not_scorable():
    verifier = LexicalOverlapVerifier()
    outcome = await verifier.verify("Ok.", ["irrelevant context"])
    assert outcome.sentence_verdicts[0].scorable is False
    assert outcome.sentence_verdicts[0].supported is True
