"""Knowledge graph search via graph traversal."""

from __future__ import annotations

from kioku.pipeline.graph_writer import GraphStore
from kioku.search.bm25 import SearchResult


def graph_search(store: GraphStore, query: str, limit: int = 20) -> list[SearchResult]:
    """Search the knowledge graph by finding entities related to the query.

    Strategy:
    1. Search for entities matching the query text
    2. For each found entity, traverse its neighborhood
    3. Collect related edges as evidence and score by relationship weight
    """
    # Find seed entities
    seed_entities = store.search_entities(query, limit=5)

    if not seed_entities:
        return []

    seen_evidence = set()
    results = []

    for entity in seed_entities:
        # Traverse from each seed entity
        graph_result = store.traverse(entity.name, max_hops=2, limit=limit)

        for edge in graph_result.edges:
            if edge.evidence and edge.evidence not in seen_evidence:
                seen_evidence.add(edge.evidence)
                results.append(
                    SearchResult(
                        content=edge.evidence,
                        date="",  # Graph edges don't always have dates
                        mood="",
                        timestamp="",
                        score=edge.weight,
                        source="graph",
                    )
                )

    # Sort by weight (highest first)
    results.sort(key=lambda r: r.score, reverse=True)
    return results[:limit]
