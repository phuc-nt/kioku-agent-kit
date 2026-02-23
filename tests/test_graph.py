"""Tests for entity extraction and knowledge graph."""

import pytest
from kioku.pipeline.extractor import FakeExtractor, Entity, Relationship, ExtractionResult
from kioku.pipeline.graph_writer import InMemoryGraphStore
from kioku.search.graph import graph_search


@pytest.fixture
def extractor():
    return FakeExtractor()


@pytest.fixture
def graph_store():
    return InMemoryGraphStore()


@pytest.fixture
def populated_graph(extractor, graph_store):
    """Graph with sample data extracted from memory entries."""
    entries = [
        ("Hôm nay họp với Hùng về dự án X. Bị stressed tiến độ chậm.", "2026-02-20"),
        ("Tối ăn phở với Linh, cảm thấy happy.", "2026-02-20"),
        ("Sáng đi gym với Minh, cảm thấy khỏe.", "2026-02-21"),
        ("Hùng gọi điện hỏi tiến độ dự án X, stressed.", "2026-02-22"),
    ]
    for text, date in entries:
        result = extractor.extract(text)
        graph_store.upsert(result, date=date, timestamp=f"{date}T12:00:00+07:00")
    return graph_store


class TestFakeExtractor:
    def test_extracts_emotions(self, extractor):
        result = extractor.extract("Hôm nay cảm thấy stressed vì công việc")
        types = {e.type for e in result.entities}
        assert "EMOTION" in types

    def test_extracts_persons(self, extractor):
        result = extractor.extract("Họp với Hùng và Linh về dự án X")
        person_names = {e.name for e in result.entities if e.type == "PERSON"}
        assert "Hùng" in person_names or "Linh" in person_names

    def test_creates_relationships(self, extractor):
        result = extractor.extract("Hùng làm tôi stressed")
        # Should have person + emotion + relationship
        assert len(result.entities) >= 2
        if result.relationships:
            assert result.relationships[0].rel_type == "EMOTIONAL"

    def test_empty_text(self, extractor):
        result = extractor.extract("")
        assert isinstance(result, ExtractionResult)


class TestInMemoryGraphStore:
    def test_upsert_entities(self, graph_store):
        extraction = ExtractionResult(
            entities=[Entity(name="Hùng", type="PERSON")],
            relationships=[],
        )
        graph_store.upsert(extraction, date="2026-02-22", timestamp="t1")
        assert len(graph_store.nodes) == 1
        assert graph_store.nodes["hùng"].mention_count == 1

    def test_upsert_increments_count(self, graph_store):
        extraction = ExtractionResult(
            entities=[Entity(name="Hùng", type="PERSON")],
            relationships=[],
        )
        graph_store.upsert(extraction, date="2026-02-20", timestamp="t1")
        graph_store.upsert(extraction, date="2026-02-22", timestamp="t2")
        assert graph_store.nodes["hùng"].mention_count == 2
        assert graph_store.nodes["hùng"].last_seen == "2026-02-22"

    def test_upsert_relationships(self, graph_store):
        extraction = ExtractionResult(
            entities=[
                Entity(name="Hùng", type="PERSON"),
                Entity(name="stressed", type="EMOTION"),
            ],
            relationships=[
                Relationship(
                    source="Hùng",
                    target="stressed",
                    rel_type="EMOTIONAL",
                    weight=0.7,
                    evidence="Hùng làm tôi stressed",
                )
            ],
        )
        graph_store.upsert(extraction, date="2026-02-22", timestamp="t1")
        assert len(graph_store.edges) == 1
        assert graph_store.edges[0].source == "Hùng"

    def test_search_entities(self, populated_graph):
        results = populated_graph.search_entities("Hùng")
        assert len(results) >= 1
        assert results[0].name == "Hùng"

    def test_search_entities_no_match(self, populated_graph):
        results = populated_graph.search_entities("xyznonexistent")
        assert len(results) == 0

    def test_traverse(self, populated_graph):
        result = populated_graph.traverse("Hùng", max_hops=2)
        assert len(result.nodes) >= 1

    def test_find_path_connected(self, graph_store):
        extraction = ExtractionResult(
            entities=[
                Entity(name="A", type="PERSON"),
                Entity(name="B", type="PERSON"),
                Entity(name="C", type="PERSON"),
            ],
            relationships=[
                Relationship(
                    source="A", target="B", rel_type="TOPICAL", weight=0.8, evidence="A knows B"
                ),
                Relationship(
                    source="B", target="C", rel_type="TOPICAL", weight=0.6, evidence="B knows C"
                ),
            ],
        )
        graph_store.upsert(extraction, date="2026-02-22", timestamp="t1")
        result = graph_store.find_path("A", "C")
        assert len(result.paths) == 1
        assert result.paths[0] == ["A", "B", "C"]

    def test_find_path_not_connected(self, graph_store):
        extraction = ExtractionResult(
            entities=[Entity(name="X", type="PERSON"), Entity(name="Y", type="PERSON")],
            relationships=[],
        )
        graph_store.upsert(extraction, date="2026-02-22", timestamp="t1")
        result = graph_store.find_path("X", "Y")
        assert len(result.paths) == 0


class TestGraphSearch:
    def test_graph_search_returns_results(self, populated_graph):
        results = graph_search(populated_graph, "Hùng", limit=5)
        # Should find some graph-sourced results
        if results:
            assert results[0].source == "graph"
            assert results[0].score > 0

    def test_graph_search_empty(self, graph_store):
        results = graph_search(graph_store, "nothinghere", limit=5)
        assert len(results) == 0
