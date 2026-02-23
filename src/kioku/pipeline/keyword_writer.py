"""SQLite FTS5 keyword indexing for memory entries."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from dataclasses import dataclass


@dataclass
class FTSResult:
    """A result from the FTS5 search."""

    rowid: int
    content: str
    date: str
    mood: str
    timestamp: str
    rank: float


class KeywordIndex:
    """SQLite FTS5 keyword index for memory entries."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # FastMCP Async Server calls synchronous tools in a background worker thread.
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._create_tables()

    def _create_tables(self) -> None:
        """Create FTS5 virtual table and metadata table."""
        cur = self.conn.cursor()
        # Metadata table for structured data
        cur.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                date TEXT NOT NULL,
                mood TEXT DEFAULT '',
                timestamp TEXT NOT NULL,
                content_hash TEXT UNIQUE NOT NULL,
                tags TEXT DEFAULT '[]'
            )
        """)
        # Compatibility with older DBs
        try:
            cur.execute("ALTER TABLE memories ADD COLUMN tags TEXT DEFAULT '[]'")
        except sqlite3.OperationalError:
            pass
        # FTS5 virtual table linked to memories
        cur.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                content,
                date,
                mood,
                content='memories',
                content_rowid='id'
            )
        """)
        # Triggers to keep FTS in sync
        cur.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                INSERT INTO memory_fts(rowid, content, date, mood)
                VALUES (new.id, new.content, new.date, new.mood);
            END
        """)
        cur.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                INSERT INTO memory_fts(memory_fts, rowid, content, date, mood)
                VALUES ('delete', old.id, old.content, old.date, old.mood);
            END
        """)
        self.conn.commit()

    def index(
        self,
        content: str,
        date: str,
        timestamp: str,
        mood: str = "",
        content_hash: str = "",
        tags: list[str] | None = None,
    ) -> int:
        """Index a memory entry. Returns the row id.

        Skips duplicates based on content_hash.
        """
        import hashlib
        import json

        if not content_hash:
            content_hash = hashlib.sha256(content.encode()).hexdigest()

        tags_str = json.dumps(tags or [])

        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO memories (content, date, mood, timestamp, content_hash, tags) VALUES (?, ?, ?, ?, ?, ?)",
                (content, date, mood, timestamp, content_hash, tags_str),
            )
            self.conn.commit()
            return cur.lastrowid  # type: ignore
        except sqlite3.IntegrityError:
            # Duplicate content_hash — skip
            return -1

    def search(self, query: str, limit: int = 20) -> list[FTSResult]:
        """Search memories using FTS5 BM25 ranking.

        Args:
            query: Search query string.
            limit: Max results to return.

        Returns:
            List of FTSResult sorted by relevance (best first).
        """
        cur = self.conn.cursor()
        # FTS5 match with BM25 ranking (negative = more relevant)
        cur.execute(
            """
            SELECT m.id, m.content, m.date, m.mood, m.timestamp, rank
            FROM memory_fts
            JOIN memories m ON m.id = memory_fts.rowid
            WHERE memory_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (query, limit),
        )
        results = []
        for row in cur.fetchall():
            results.append(
                FTSResult(
                    rowid=row[0],
                    content=row[1],
                    date=row[2],
                    mood=row[3],
                    timestamp=row[4],
                    rank=abs(row[5]),  # Convert to positive score
                )
            )
        return results

    def count(self) -> int:
        """Return total number of indexed entries."""
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM memories")
        return cur.fetchone()[0]

    def get_by_date(self, date: str) -> list[dict]:
        """Get all memories for a specific date from SQLite."""
        cur = self.conn.cursor()
        cur.execute("SELECT content, date, mood, timestamp, tags FROM memories WHERE date = ? ORDER BY timestamp ASC", (date,))
        import json
        return [
            {
                "text": r[0],
                "date": r[1],
                "mood": r[2],
                "timestamp": r[3],
                "tags": json.loads(r[4]) if r[4] else []
            }
            for r in cur.fetchall()
        ]

    def get_timeline(self, start_date: str | None = None, end_date: str | None = None, limit: int = 50) -> list[dict]:
        """Get timeline bounded by dates, directly from SQLite."""
        query = "SELECT content, date, mood, timestamp, tags FROM memories"
        params = []
        conditions = []
        
        if start_date:
            conditions.append("date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("date <= ?")
            params.append(end_date)
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cur = self.conn.cursor()
        cur.execute(query, tuple(params))
        import json
        
        results = [
            {
                "text": r[0],
                "date": r[1],
                "mood": r[2],
                "timestamp": r[3],
                "tags": json.loads(r[4]) if r[4] else []
            }
            for r in cur.fetchall()
        ]
        results.reverse() # chronological relative to the slice
        return results

    def get_dates(self) -> list[str]:
        """List all unique dates in the database."""
        cur = self.conn.cursor()
        cur.execute("SELECT DISTINCT date FROM memories ORDER BY date DESC")
        return [r[0] for r in cur.fetchall()]

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()
