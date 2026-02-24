"""BM25 keyword search via SQLite FTS5."""

from __future__ import annotations

from dataclasses import dataclass
from kioku.pipeline.keyword_writer import KeywordIndex


@dataclass
class SearchResult:
    """A unified search result (used across all search backends)."""

    content: str
    date: str
    mood: str
    timestamp: str
    score: float
    source: str  # "bm25", "vector", "graph"
    content_hash: str = ""  # Phase 7: Universal Identifier for SQLite hydration


def bm25_search(index: KeywordIndex, query: str, limit: int = 20) -> list[SearchResult]:
    """Run BM25 keyword search and return unified SearchResults.

    Args:
        index: The KeywordIndex instance.
        query: Search query string.
        limit: Max results.

    Returns:
        List of SearchResult sorted by BM25 score (highest first).
    """
    fts_results = index.search(query, limit=limit)

    # Normalize scores: FTS5 BM25 scores vary widely,
    # so we normalize relative to the best score
    if not fts_results:
        return []

    max_score = max(r.rank for r in fts_results) if fts_results else 1.0
    if max_score == 0:
        max_score = 1.0

    results = []
    for r in fts_results:
        results.append(
            SearchResult(
                content=r.content,
                date=r.date,
                mood=r.mood,
                timestamp=r.timestamp,
                score=r.rank / max_score,  # Normalize to 0-1
                source="bm25",
            )
        )
    return results
