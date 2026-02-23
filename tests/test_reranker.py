"""Tests for RRF reranker."""

from kioku.search.bm25 import SearchResult
from kioku.search.reranker import rrf_rerank


def _make_result(content: str, score: float, source: str = "bm25") -> SearchResult:
    return SearchResult(
        content=content,
        date="2026-02-22",
        mood="",
        timestamp="2026-02-22T12:00:00+07:00",
        score=score,
        source=source,
    )


class TestRRFRerank:
    def test_single_source(self):
        results = [
            _make_result("A", 0.9),
            _make_result("B", 0.7),
            _make_result("C", 0.5),
        ]
        ranked = rrf_rerank(results, limit=3)
        assert len(ranked) == 3
        assert ranked[0].content == "A"  # Best rank

    def test_multi_source_fusion(self):
        bm25 = [_make_result("A", 0.9, "bm25"), _make_result("B", 0.7, "bm25")]
        vector = [_make_result("B", 0.95, "vector"), _make_result("C", 0.8, "vector")]
        ranked = rrf_rerank(bm25, vector, limit=3)
        # B appears in both lists, so it should be boosted
        assert ranked[0].content == "B"

    def test_dedup_by_content(self):
        list1 = [_make_result("Same", 0.9, "bm25")]
        list2 = [_make_result("Same", 0.8, "vector")]
        ranked = rrf_rerank(list1, list2, limit=5)
        assert len(ranked) == 1  # Deduped
        assert ranked[0].score > 0

    def test_limit_respected(self):
        results = [_make_result(f"Item {i}", 1.0 - i * 0.1) for i in range(10)]
        ranked = rrf_rerank(results, limit=3)
        assert len(ranked) == 3

    def test_empty_input(self):
        ranked = rrf_rerank([], limit=5)
        assert ranked == []
