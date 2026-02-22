"""Semantic vector search via ChromaDB."""

from __future__ import annotations

from kioku.pipeline.vector_writer import VectorStore
from kioku.search.bm25 import SearchResult


def vector_search(store: VectorStore, query: str, limit: int = 20) -> list[SearchResult]:
    """Run semantic vector search and return unified SearchResults.

    ChromaDB returns cosine distances (0 = identical, 2 = opposite).
    We convert to similarity scores (1 = identical, 0 = opposite).
    """
    raw_results = store.search(query, limit=limit)

    if not raw_results:
        return []

    results = []
    for r in raw_results:
        # Convert cosine distance to similarity score
        similarity = max(0.0, 1.0 - r["distance"])
        results.append(
            SearchResult(
                content=r["content"],
                date=r["date"],
                mood=r["mood"],
                timestamp=r["timestamp"],
                score=similarity,
                source="vector",
            )
        )
    return results
