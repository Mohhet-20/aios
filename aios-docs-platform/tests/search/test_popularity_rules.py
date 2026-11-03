from docs_platform.search.popularity_rules import top_queries


def test_top_queries_counts_and_orders():
    queries = ["deploy", "Deploy", "search", "deploy", "search", "search"]
    result = top_queries(queries)
    # both tie at count 3; Counter.most_common breaks ties by first-seen
    # insertion order, and "deploy" (case-insensitively) was seen first.
    assert result[0] == ("deploy", 3)
    assert result[1] == ("search", 3)


def test_top_queries_respects_limit():
    queries = ["a", "b", "c", "a", "b", "a"]
    result = top_queries(queries, limit=1)
    assert result == [("a", 3)]


def test_top_queries_ignores_blank():
    assert top_queries(["", "  ", "real"]) == [("real", 1)]
