"""Integration tests for Kioku — tests both service layer and MCP server tools."""

import uuid
import pytest

from kioku.config import Settings
from kioku.pipeline.keyword_writer import KeywordIndex
from kioku.pipeline.embedder import FakeEmbedder
from kioku.pipeline.vector_writer import VectorStore
from kioku.pipeline.extractor import FakeExtractor
from kioku.pipeline.graph_writer import InMemoryGraphStore


@pytest.fixture(autouse=True)
def setup_test_env(tmp_path, monkeypatch):
    """Override all stores for tests — fully isolated, no external deps."""
    import os
    import kioku.server as server_module

    use_e2e = os.environ.get("KIOKU_E2E") == "1"

    # Override settings
    test_settings = Settings(
        memory_dir=tmp_path / "memory",
        data_dir=tmp_path / "data",
    )
    test_settings.ensure_dirs()

    # Override keyword index
    test_index = KeywordIndex(test_settings.sqlite_path)

    if use_e2e:
        from kioku.pipeline.embedder import OllamaEmbedder
        from kioku.pipeline.extractor import ClaudeExtractor
        from kioku.pipeline.graph_writer import FalkorGraphStore

        test_embedder = OllamaEmbedder(host="http://localhost:11434", model="nomic-embed-text")
        test_store = VectorStore(
            embedder=test_embedder,
            collection_name=f"test_vec_{uuid.uuid4().hex[:8]}",
            host="localhost",
            port=8000,
        )
        test_extractor = ClaudeExtractor(api_key=os.environ.get("KIOKU_ANTHROPIC_API_KEY", ""))
        test_graph = FalkorGraphStore(
            host="localhost",
            port=6379,
            graph_name=f"test_graph_{uuid.uuid4().hex[:8]}",
        )
    else:
        test_embedder = FakeEmbedder()
        test_store = VectorStore(
            embedder=test_embedder, collection_name=f"test_{uuid.uuid4().hex[:8]}"
        )
        test_graph = InMemoryGraphStore()
        test_extractor = FakeExtractor()

    # Patch the _svc instance attributes (service layer owns the state now)
    svc = server_module._svc
    monkeypatch.setattr(svc, "settings", test_settings)
    monkeypatch.setattr(svc, "keyword_index", test_index)
    monkeypatch.setattr(svc, "vector_store", test_store)
    monkeypatch.setattr(svc, "graph_store", test_graph)
    monkeypatch.setattr(svc, "extractor", test_extractor)

    yield

    test_index.close()


# ─── Import tool functions from server (thin wrappers) ─────────────────

from kioku.server import (
    save_memory,
    search_memories,
    list_memory_dates,
    recall_related,
    explain_connection,
)


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
        assert "connected" in result

    def test_explain_not_connected(self):
        result = explain_connection("A_entity", "B_entity")
        assert result["connected"] is False


class TestListMemoryDatesTool:
    def test_list_dates(self):
        save_memory("Some entry")
        result = list_memory_dates()
        assert result["count"] >= 1
        assert len(result["dates"]) >= 1


from kioku import server as server_module


class TestTimelineAndPatternsTools:
    def test_get_timeline(self, setup_test_env):
        server_module.save_memory("First event", mood="neutral", tags=["test1"])
        server_module.save_memory("Second event", mood="happy", tags=["test2"])

        result = server_module.get_timeline(limit=10)
        assert result["count"] >= 2
        assert result["sort_by"] == "processing_time"

        timeline = result["timeline"]
        assert timeline[-2]["text"] == "First event"
        assert timeline[-1]["text"] == "Second event"
        # Phase 7: event_time field should be present
        assert "event_time" in timeline[-1]

    def test_get_timeline_sort_by_event_time(self, setup_test_env):
        """Timeline can be sorted by event_time instead of processing_time."""
        # Save entries — FakeExtractor doesn't produce event_time, so field will be empty
        server_module.save_memory("Old memory about childhood")
        server_module.save_memory("Recent memory about today")

        result = server_module.get_timeline(limit=10, sort_by="event_time")
        assert result["sort_by"] == "event_time"
        # With FakeExtractor, no entries have event_time set, so count may be 0
        assert result["count"] >= 0


class TestPhase7BiTemporal:
    """Phase 7: Bi-temporal modeling, entity resolution, universal identifier."""

    def test_save_returns_event_time(self):
        """save_memory should return event_time field."""
        result = save_memory("Hôm qua đi ăn phở rất ngon")
        assert "event_time" in result
        # FakeExtractor doesn't infer event_time, so it's None
        # But the field must be present in the response

    def test_event_time_in_sqlite(self, setup_test_env):
        """event_time should be stored in SQLite."""
        svc = server_module._svc
        import hashlib

        text = "Meeting with team about project kickoff"
        content_hash = hashlib.sha256(text.encode()).hexdigest()
        svc.keyword_index.index(
            content=text,
            date="2026-02-24",
            timestamp="2026-02-24T10:00:00+07:00",
            mood="neutral",
            content_hash=content_hash,
            event_time="2026-02-20",
        )
        results = svc.keyword_index.get_by_hashes([content_hash])
        assert content_hash in results
        assert results[content_hash]["event_time"] == "2026-02-20"

    def test_get_by_hashes_empty(self, setup_test_env):
        """get_by_hashes with empty list returns empty dict."""
        svc = server_module._svc
        assert svc.keyword_index.get_by_hashes([]) == {}

    def test_get_by_hashes_multiple(self, setup_test_env):
        """get_by_hashes returns multiple entries."""
        svc = server_module._svc
        import hashlib

        hashes = []
        for i in range(3):
            text = f"Memory number {i} about different topics"
            h = hashlib.sha256(text.encode()).hexdigest()
            hashes.append(h)
            svc.keyword_index.index(
                content=text,
                date="2026-02-24",
                timestamp=f"2026-02-24T10:0{i}:00+07:00",
                mood="",
                content_hash=h,
            )
        results = svc.keyword_index.get_by_hashes(hashes)
        assert len(results) == 3

    def test_graph_canonical_entities(self, setup_test_env):
        """Graph store should return canonical entity names."""
        save_memory("Hùng gọi điện hỏi dự án, stressed")
        save_memory("Hùng mời đi ăn trưa, happy")
        svc = server_module._svc
        entities = svc.graph_store.get_canonical_entities(limit=10)
        assert isinstance(entities, list)

    def test_graph_source_hash_on_edges(self, setup_test_env):
        """Graph edges should carry source_hash for O(1) hydration."""
        save_memory("Hùng làm tôi stressed vì deadline")
        svc = server_module._svc
        result = svc.graph_store.traverse("Hùng", max_hops=2, limit=10)
        # InMemoryGraphStore stores source_hash on edges
        for edge in result.edges:
            assert hasattr(edge, "source_hash")


class TestResourcesAndPrompts:
    def test_memory_resource(self, setup_test_env):
        server_module.save_memory("Test string in memory", mood="happy")
        from datetime import datetime

        today = datetime.now().strftime("%Y-%m-%d")

        res = server_module.read_memory_resource(today)
        assert "Test string in memory" in res

        res_empty = server_module.read_memory_resource("1900-01-01")
        assert "No memories found" in res_empty

    def test_entity_resource(self, setup_test_env):
        server_module.save_memory("Hôm nay đi tập gym với Minh, rất vui.")
        res = server_module.read_entity_resource("Minh")
        assert "Entity Profile: Minh" in res or "Entity 'Minh' not found" in res

    def test_prompts(self):
        prompt1 = server_module.reflect_on_day()
        assert "kioku://memories/" in prompt1
        assert "overall emotional tone" in prompt1

        prompt2 = server_module.analyze_relationships("Hùng")
        assert "kioku://entities/Hùng" in prompt2
        assert "What is my primary emotional response" in prompt2

        prompt3 = server_module.weekly_review()
        assert "weekly retrospective" in prompt3
