"""Tests for markdown storage layer."""

import pytest
from pathlib import Path
from kioku.storage.markdown import save_entry, read_entries, list_dates


@pytest.fixture
def tmp_memory_dir(tmp_path):
    """Create a temporary memory directory."""
    d = tmp_path / "memory"
    d.mkdir()
    return d


class TestSaveEntry:
    def test_save_creates_file(self, tmp_memory_dir):
        entry = save_entry(tmp_memory_dir, "Test memory")
        files = list(tmp_memory_dir.glob("*.md"))
        assert len(files) == 1
        assert entry.text == "Test memory"
        assert entry.timestamp != ""

    def test_save_with_mood(self, tmp_memory_dir):
        entry = save_entry(tmp_memory_dir, "Feeling good", mood="happy")
        assert entry.mood == "happy"

    def test_save_with_tags(self, tmp_memory_dir):
        entry = save_entry(tmp_memory_dir, "Work meeting", tags=["work", "meeting"])
        assert entry.tags == ["work", "meeting"]

    def test_save_appends_to_same_file(self, tmp_memory_dir):
        save_entry(tmp_memory_dir, "First entry")
        save_entry(tmp_memory_dir, "Second entry")
        files = list(tmp_memory_dir.glob("*.md"))
        assert len(files) == 1  # Same day = same file
        content = files[0].read_text()
        assert "First entry" in content
        assert "Second entry" in content


class TestReadEntries:
    def test_read_empty(self, tmp_memory_dir):
        entries = read_entries(tmp_memory_dir, date="2026-01-01")
        assert entries == []

    def test_read_saved_entries(self, tmp_memory_dir):
        save_entry(tmp_memory_dir, "Entry one", mood="neutral")
        save_entry(tmp_memory_dir, "Entry two", mood="happy")
        entries = read_entries(tmp_memory_dir)
        assert len(entries) == 2
        assert entries[0].text == "Entry one"
        assert entries[0].mood == "neutral"
        assert entries[1].text == "Entry two"
        assert entries[1].mood == "happy"


class TestListDates:
    def test_list_empty(self, tmp_memory_dir):
        dates = list_dates(tmp_memory_dir)
        assert dates == []

    def test_list_with_files(self, tmp_memory_dir):
        (tmp_memory_dir / "2026-02-22.md").write_text("# Test")
        (tmp_memory_dir / "2026-02-23.md").write_text("# Test")
        dates = list_dates(tmp_memory_dir)
        assert dates == ["2026-02-22", "2026-02-23"]
