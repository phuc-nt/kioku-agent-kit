"""Tests for SQLite FTS5 keyword search."""

import pytest
from kioku.pipeline.keyword_writer import KeywordIndex
from kioku.search.bm25 import bm25_search


@pytest.fixture
def keyword_index(tmp_path):
    """Create a temporary keyword index."""
    db_path = tmp_path / "test_fts.db"
    idx = KeywordIndex(db_path)
    yield idx
    idx.close()


@pytest.fixture
def populated_index(keyword_index):
    """Index with sample data."""
    entries = [
        ("Hôm nay họp với sếp Hùng về dự án X. Bị chê tiến độ chậm.", "2026-02-20", "stressed"),
        ("Tối ăn phở với Linh, cảm thấy đỡ hơn.", "2026-02-20", "happy"),
        ("Sáng đi gym, tập được 1 tiếng. Cảm thấy khỏe.", "2026-02-21", "energetic"),
        ("Đọc xong cuốn Designing Data-Intensive Applications.", "2026-02-21", "focused"),
        ("Deadline dự án X ngày mai, đang rất căng thẳng.", "2026-02-22", "stressed"),
        ("Gọi điện cho mẹ, nói chuyện 30 phút.", "2026-02-22", "warm"),
    ]
    for content, date, mood in entries:
        keyword_index.index(
            content=content,
            date=date,
            timestamp=f"{date}T12:00:00+07:00",
            mood=mood,
        )
    return keyword_index


class TestKeywordIndex:
    def test_index_entry(self, keyword_index):
        rowid = keyword_index.index(
            content="Test memory",
            date="2026-02-22",
            timestamp="2026-02-22T12:00:00+07:00",
        )
        assert rowid > 0
        assert keyword_index.count() == 1

    def test_dedup_by_hash(self, keyword_index):
        keyword_index.index(content="Same text", date="2026-02-22", timestamp="t1")
        keyword_index.index(content="Same text", date="2026-02-22", timestamp="t2")
        assert keyword_index.count() == 1  # Deduped

    def test_different_content_not_deduped(self, keyword_index):
        keyword_index.index(content="Text A", date="2026-02-22", timestamp="t1")
        keyword_index.index(content="Text B", date="2026-02-22", timestamp="t2")
        assert keyword_index.count() == 2


class TestBM25Search:
    def test_search_keyword_match(self, populated_index):
        results = bm25_search(populated_index, "dự án X")
        assert len(results) >= 1
        contents = [r.content for r in results]
        assert any("dự án X" in c for c in contents)

    def test_search_mood(self, populated_index):
        results = bm25_search(populated_index, "stressed")
        assert len(results) >= 1

    def test_search_person_name(self, populated_index):
        results = bm25_search(populated_index, "Linh")
        assert len(results) >= 1
        assert "Linh" in results[0].content

    def test_search_no_results(self, populated_index):
        results = bm25_search(populated_index, "xyznotexist123")
        assert len(results) == 0

    def test_search_results_have_score(self, populated_index):
        results = bm25_search(populated_index, "gym")
        assert len(results) >= 1
        assert results[0].score > 0
        assert results[0].source == "bm25"

    def test_search_limit(self, populated_index):
        results = bm25_search(populated_index, "cảm thấy", limit=2)
        assert len(results) <= 2
