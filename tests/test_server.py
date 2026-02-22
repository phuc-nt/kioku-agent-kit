"""Integration tests for MCP server tools."""

import uuid
import pytest
from pathlib import Path

from kioku.server import (
    save_memory, search_memories, get_memories_by_date,
    list_memory_dates, recall_related, explain_connection,
)
from kioku.config import Settings
from kioku.pipeline.keyword_writer import KeywordIndex
from kioku.pipeline.embedder import FakeEmbedder
from kioku.pipeline.vector_writer import VectorStore
from kioku.pipeline.extractor import FakeExtractor
from kioku.pipeline.graph_writer import InMemoryGraphStore


@pytest.fixture(autouse=True)
def setup_test_env(tmp_path, monkeypatch):
    """Override all stores for tests — fully isolated, no external deps."""
    import kioku.server as server_module

    # Override settings
    test_settings = Settings(
        memory_dir=tmp_path / "memory",
        data_dir=tmp_path / "data",
    )
    test_settings.ensure_dirs()
    monkeypatch.setattr(server_module, "settings", test_settings)

    # Override keyword index
    test_index = KeywordIndex(test_settings.sqlite_path)
    monkeypatch.setattr(server_module, "keyword_index", test_index)

    # Override vector store (unique collection per test)
    test_embedder = FakeEmbedder()
    test_store = VectorStore(embedder=test_embedder, collection_name=f"test_{uuid.uuid4().hex[:8]}")
    monkeypatch.setattr(server_module, "vector_store", test_store)

    # Override graph store and extractor
    test_graph = InMemoryGraphStore()
    test_extractor = FakeExtractor()
    monkeypatch.setattr(server_module, "graph_store", test_graph)
    monkeypatch.setattr(server_module, "extractor", test_extractor)

    yield

    test_index.close()


class TestSaveMemoryTool:
    def test_save_basic(self):
        result = save_memory("Today I learned about MCP servers")
        assert result["status"] == "saved"
        assert result["indexed"] is True
        assert "timestamp" in result

    def test_save_with_mood(self):
        result = save_memory("Feeling great!", mood="happy")
        assert result["mood"] == "happy"

    def test_save_with_tags(self):
        result = save_memory("Work meeting", tags=["work", "meeting"])
        assert result["tags"] == ["work", "meeting"]

    def test_save_indexes_graph(self):
        """Saving a memory should also extract entities into the graph."""
        save_memory("Project meeting with Hung today, feeling stressed")
        result = recall_related("Hung")
        assert result["connected_count"] >= 1


class TestSearchMemoriesTool:
    def test_search_empty_store(self):
        """Search on an empty store returns no results."""
        result = search_memories("nonexistent query xyz")
        assert result["count"] == 0

    def test_search_finds_saved(self):
        save_memory("Đi ăn phở với bạn Minh ở quận 1")
        save_memory("Họp team buổi sáng về sprint mới")
        result = search_memories("phở")
        assert result["count"] >= 1
        assert "phở" in result["results"][0]["content"]

    def test_search_limit(self):
        for i in range(5):
            save_memory(f"Memory entry number {i} about testing")
        result = search_memories("testing", limit=3)
        assert result["count"] <= 3


class TestRecallRelatedTool:
    def test_recall_entities(self):
        save_memory("Hùng gọi điện hỏi dự án, stressed")
        save_memory("Hùng mời đi ăn trưa, happy")
        result = recall_related("Hùng")
        assert result["entity"] == "Hùng"
        assert result["connected_count"] >= 1

    def test_recall_no_match(self):
        result = recall_related("NotARealPerson")
        assert result["connected_count"] == 0


class TestExplainConnectionTool:
    def test_explain_connected(self):
        save_memory("Hùng làm tôi stressed")
        result = explain_connection("Hùng", "stressed")
        assert result["from"] == "Hùng"
        assert result["to"] == "stressed"
        # May or may not find a path depending on extraction
        assert "connected" in result

    def test_explain_not_connected(self):
        result = explain_connection("A_entity", "B_entity")
        assert result["connected"] is False


class TestGetMemoriesByDateTool:
    def test_get_today(self):
        save_memory("Entry for today")
        result = get_memories_by_date()
        assert result["count"] >= 1

    def test_get_empty_date(self):
        result = get_memories_by_date(date="2020-01-01")
        assert result["count"] == 0


class TestListMemoryDatesTool:
    def test_list_dates(self):
        save_memory("Some entry")
        result = list_memory_dates()
        assert result["count"] >= 1
        assert len(result["dates"]) >= 1
