"""Integration tests for MCP server tools."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from kioku.server import save_memory, search_memories, get_memories_by_date, list_memory_dates
from kioku.config import Settings
from kioku.pipeline.keyword_writer import KeywordIndex


@pytest.fixture(autouse=True)
def setup_test_env(tmp_path, monkeypatch):
    """Override settings and keyword index for tests."""
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


class TestSearchMemoriesTool:
    def test_search_finds_saved(self):
        save_memory("Đi ăn phở với bạn Minh ở quận 1")
        save_memory("Họp team buổi sáng về sprint mới")
        result = search_memories("phở")
        assert result["count"] >= 1
        assert "phở" in result["results"][0]["content"]

    def test_search_empty(self):
        result = search_memories("nonexistent query xyz")
        assert result["count"] == 0

    def test_search_limit(self):
        for i in range(5):
            save_memory(f"Memory entry number {i} about testing")
        result = search_memories("testing", limit=3)
        assert result["count"] <= 3


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
