"""Markdown-based memory storage — Source of Truth."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path
from dataclasses import dataclass


JST = timezone(timedelta(hours=7))  # Vietnam timezone


@dataclass
class MemoryEntry:
    """A single memory entry."""

    text: str
    timestamp: str
    mood: str | None = None
    tags: list[str] | None = None
    event_time: str | None = None  # YYYY-MM-DD — when the event actually happened


def _get_today_file(memory_dir: Path) -> Path:
    """Get today's memory file path."""
    today = datetime.now(JST).strftime("%Y-%m-%d")
    return memory_dir / f"{today}.md"


def save_entry(
    memory_dir: Path,
    text: str,
    mood: str | None = None,
    tags: list[str] | None = None,
    event_time: str | None = None,
) -> MemoryEntry:
    """Append a memory entry to today's markdown file.

    Returns the created MemoryEntry with timestamp.
    """
    memory_dir.mkdir(parents=True, exist_ok=True)
    filepath = _get_today_file(memory_dir)

    now = datetime.now(JST)
    timestamp = now.isoformat()

    # Build frontmatter block
    lines = []
    lines.append("\n---\n")
    lines.append(f'time: "{timestamp}"\n')
    if mood:
        lines.append(f'mood: "{mood}"\n')
    if tags:
        lines.append(f"tags: {tags}\n")
    if event_time:
        lines.append(f'event_time: "{event_time}"\n')
    lines.append("---\n")
    lines.append(f"{text}\n")

    # If file doesn't exist, add a header
    if not filepath.exists():
        date_str = now.strftime("%Y-%m-%d")
        header = f"# Kioku — {date_str}\n"
        filepath.write_text(header, encoding="utf-8")

    # Append entry
    with filepath.open("a", encoding="utf-8") as f:
        f.writelines(lines)

    return MemoryEntry(text=text, timestamp=timestamp, mood=mood, tags=tags, event_time=event_time)


def read_entries(memory_dir: Path, date: str | None = None) -> list[MemoryEntry]:
    """Read all entries from a specific date's file.

    Args:
        memory_dir: Base memory directory.
        date: Date string "YYYY-MM-DD". If None, use today.

    Returns:
        List of MemoryEntry objects.
    """
    if date is None:
        date = datetime.now(JST).strftime("%Y-%m-%d")

    filepath = memory_dir / f"{date}.md"
    if not filepath.exists():
        return []

    content = filepath.read_text(encoding="utf-8")
    return _parse_entries(content)


def _parse_entries(content: str) -> list[MemoryEntry]:
    """Parse markdown content into MemoryEntry objects."""
    entries = []
    blocks = content.split("\n---\n")

    for i in range(1, len(blocks), 2):
        if i + 1 > len(blocks):
            break

        frontmatter = blocks[i].strip()
        body = blocks[i + 1].strip() if i + 1 < len(blocks) else ""

        # Parse frontmatter
        timestamp = ""
        mood = None
        tags = None
        event_time = None

        for line in frontmatter.split("\n"):
            line = line.strip()
            if line.startswith("time:"):
                timestamp = line.split(":", 1)[1].strip().strip('"')
            elif line.startswith("mood:"):
                mood = line.split(":", 1)[1].strip().strip('"')
            elif line.startswith("tags:"):
                raw = line.split(":", 1)[1].strip()
                # Simple parsing for Python list repr
                tags = [t.strip().strip("'\"") for t in raw.strip("[]").split(",") if t.strip()]
            elif line.startswith("event_time:"):
                event_time = line.split(":", 1)[1].strip().strip('"')

        if body:
            entries.append(
                MemoryEntry(
                    text=body, timestamp=timestamp, mood=mood, tags=tags, event_time=event_time
                )
            )

    return entries


def list_dates(memory_dir: Path) -> list[str]:
    """List all available memory dates."""
    if not memory_dir.exists():
        return []
    files = sorted(memory_dir.glob("*.md"))
    return [f.stem for f in files]
