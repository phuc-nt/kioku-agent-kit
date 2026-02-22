"""Tests for vector pipeline: embedder + vector writer + semantic search."""

import uuid
import pytest
from kioku.pipeline.embedder import FakeEmbedder
from kioku.pipeline.vector_writer import VectorStore
from kioku.search.semantic import vector_search


@pytest.fixture
def embedder():
    return FakeEmbedder(dimensions=128)


@pytest.fixture
def store(embedder):
    """In-memory ChromaDB vector store for testing — unique collection per test."""
    name = f"test_{uuid.uuid4().hex[:8]}"
    return VectorStore(embedder=embedder, collection_name=name)


@pytest.fixture
def populated_store(store):
    """Store with sample data."""
    entries = [
        ("Hôm nay họp với sếp Hùng về dự án X. Bị chê tiến độ chậm.", "2026-02-20", "stressed"),
        ("Tối ăn phở với Linh, cảm thấy đỡ hơn.", "2026-02-20", "happy"),
        ("Sáng đi gym, tập được 1 tiếng. Cảm thấy khỏe.", "2026-02-21", "energetic"),
        ("Đọc xong cuốn Designing Data-Intensive Applications.", "2026-02-21", "focused"),
        ("Deadline dự án X ngày mai, đang rất căng thẳng.", "2026-02-22", "stressed"),
        ("Gọi điện cho mẹ, nói chuyện 30 phút.", "2026-02-22", "warm"),
    ]
    for content, date, mood in entries:
        store.add(
            content=content,
            date=date,
            timestamp=f"{date}T12:00:00+07:00",
            mood=mood,
        )
    return store


class TestFakeEmbedder:
    def test_deterministic(self, embedder):
        v1 = embedder.embed("hello")
        v2 = embedder.embed("hello")
        assert v1 == v2

    def test_different_texts(self, embedder):
        v1 = embedder.embed("hello")
        v2 = embedder.embed("world")
        assert v1 != v2

    def test_correct_dimensions(self, embedder):
        v = embedder.embed("test")
        assert len(v) == 128

    def test_batch(self, embedder):
        vectors = embedder.embed_batch(["a", "b", "c"])
        assert len(vectors) == 3
        assert all(len(v) == 128 for v in vectors)


class TestVectorStore:
    def test_add_entry(self, store):
        doc_id = store.add(
            content="Test memory",
            date="2026-02-22",
            timestamp="2026-02-22T12:00:00+07:00",
        )
        assert doc_id != ""
        assert store.count() == 1

    def test_dedup(self, store):
        store.add(content="Same text", date="2026-02-22", timestamp="t1")
        store.add(content="Same text", date="2026-02-22", timestamp="t2")
        assert store.count() == 1

    def test_search_returns_results(self, populated_store):
        results = populated_store.search("dự án", limit=5)
        assert len(results) >= 1

    def test_search_has_metadata(self, populated_store):
        results = populated_store.search("gym", limit=5)
        assert len(results) >= 1
        assert results[0]["date"] != ""
        assert "distance" in results[0]

    def test_count(self, populated_store):
        assert populated_store.count() == 6


class TestSemanticSearch:
    def test_returns_search_results(self, populated_store):
        results = vector_search(populated_store, "gym tập thể dục", limit=5)
        assert len(results) >= 1
        assert results[0].source == "vector"
        assert 0.0 <= results[0].score <= 1.0

    def test_empty_store(self, embedder):
        empty = VectorStore(embedder=embedder, collection_name=f"empty_{uuid.uuid4().hex[:8]}")
        results = vector_search(empty, "anything", limit=5)
        assert len(results) == 0
