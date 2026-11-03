import datetime as dt

from memory_platform.reranking.reranker import rerank, top_k
from memory_platform.retrieval.schemas import RetrievalResult


def _result(id_, score, importance, days_ago, source_type="memory_entry"):
    now = dt.datetime.now(dt.timezone.utc)
    return RetrievalResult(
        id=id_, source_type=source_type, content=f"content {id_}", score=score, importance_score=importance,
        created_at=now - dt.timedelta(days=days_ago), last_accessed_at=now - dt.timedelta(days=days_ago),
    )


def test_rerank_favors_recent_important_over_slightly_higher_similarity_stale_low_importance():
    stale_but_similar = _result("a", score=0.95, importance=0.1, days_ago=365)
    recent_important = _result("b", score=0.80, importance=0.9, days_ago=0)
    ranked = rerank([stale_but_similar, recent_important])
    assert ranked[0].id == "b"


def test_rerank_preserves_all_results_and_attaches_score():
    results = [_result(f"r{i}", score=0.5, importance=0.5, days_ago=i) for i in range(5)]
    ranked = rerank(results)
    assert len(ranked) == 5
    assert all("rerank_score" in r.metadata for r in ranked)
    scores = [r.metadata["rerank_score"] for r in ranked]
    assert scores == sorted(scores, reverse=True)


def test_rerank_empty_list():
    assert rerank([]) == []


def test_rerank_missing_timestamps_uses_neutral_recency():
    no_ts = RetrievalResult(id="x", source_type="memory_entry", content="c", score=0.5, importance_score=0.5)
    ranked = rerank([no_ts])
    assert ranked[0].metadata["rerank_score"] > 0


def test_top_k_truncates():
    results = [_result(f"r{i}", score=1.0 - i * 0.01, importance=0.5, days_ago=0) for i in range(20)]
    assert len(top_k(results, 5)) == 5
