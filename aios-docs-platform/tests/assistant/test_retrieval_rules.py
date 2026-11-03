from docs_platform.assistant.retrieval_rules import extractive_summary, rank_candidates, score_match, tokenize


def test_tokenize_lowercases_and_strips_punctuation():
    assert tokenize("Deploy the Workflow Engine!") == {"deploy", "the", "workflow", "engine"}


def test_score_match_full_containment():
    assert score_match("deploy workflow", "how to deploy a workflow engine") == 1.0


def test_score_match_partial():
    assert score_match("deploy workflow", "how to deploy an agent") == 0.5


def test_score_match_empty_query():
    assert score_match("", "anything") == 0.0


def test_rank_candidates_orders_by_score_desc():
    candidates = [("a", "irrelevant text"), ("b", "deploy the workflow engine"), ("c", "deploy something else")]
    ranked = rank_candidates("deploy workflow engine", candidates)
    assert ranked[0][0] == "b"
    assert all(ranked[i][1] >= ranked[i + 1][1] for i in range(len(ranked) - 1))


def test_rank_candidates_excludes_zero_scores():
    candidates = [("a", "totally unrelated")]
    assert rank_candidates("deploy workflow", candidates) == []


def test_extractive_summary_takes_first_sentences():
    text = "First sentence. Second sentence. Third sentence. Fourth sentence."
    assert extractive_summary(text, max_sentences=2) == "First sentence. Second sentence."
