"""Knowledge graph search via graph traversal."""

from __future__ import annotations

import re

from kioku.pipeline.graph_writer import GraphStore
from kioku.search.bm25 import SearchResult

# Vietnamese stopwords (common words that rarely match useful entities)
_STOPWORDS = {
    "là", "và", "của", "có", "cho", "với", "được", "này", "đó", "các",
    "một", "những", "trong", "để", "từ", "theo", "về", "hay", "hoặc",
    "nhưng", "mà", "nếu", "khi", "thì", "đã", "sẽ", "đang", "rồi",
    "nào", "gì", "thế", "sao", "tại", "vì", "bị", "do", "qua", "lại",
    "như", "hơn", "nhất", "rất", "quá", "cũng", "vẫn", "còn", "chỉ",
    "tôi", "anh", "em", "bạn", "mình", "chúng", "họ", "ai",
    "the", "is", "are", "was", "were", "what", "who", "how", "why",
}


def graph_search(
    store: GraphStore,
    query: str,
    limit: int = 20,
    entities: list[str] | None = None,
) -> list[SearchResult]:
    """Search the knowledge graph by finding entities related to the query.

    Strategy (Phase 7 — Entity-aware search):
    1. If `entities` provided (Agent-extracted): use them as seeds directly
    2. Otherwise: tokenize query, filter stopwords, search per-token (fallback)
    3. Deduplicate and rank seeds by mention_count
    4. Traverse top seeds and collect edges with source_hash
    """
    seed_map: dict[str, object] = {}

    if entities:
        # Priority path: Agent has pre-extracted entity names
        for entity_name in entities:
            for entity in store.search_entities(entity_name, limit=3):
                if entity.name not in seed_map:
                    seed_map[entity.name] = entity
    else:
        # Fallback: tokenize query and search per-token
        tokens = re.findall(r"\w+", query.lower())
        meaningful_tokens = [t for t in tokens if t not in _STOPWORDS and len(t) >= 2]
        if not meaningful_tokens:
            return []
        for token in meaningful_tokens:
            for entity in store.search_entities(token, limit=3):
                if entity.name not in seed_map:
                    seed_map[entity.name] = entity

    if not seed_map:
        return []

    # Rank seeds by mention_count (most mentioned = most important)
    ranked_seeds = sorted(
        seed_map.values(),
        key=lambda e: getattr(e, "mention_count", 0),
        reverse=True,
    )[:5]

    # Traverse from each seed and collect edges
    seen_hashes = set()
    results = []

    for entity in ranked_seeds:
        graph_result = store.traverse(entity.name, max_hops=2, limit=limit)

        for edge in graph_result.edges:
            dedup_key = edge.source_hash or edge.evidence
            if dedup_key and dedup_key not in seen_hashes:
                seen_hashes.add(dedup_key)
                results.append(
                    SearchResult(
                        content=edge.evidence or "",
                        date="",
                        mood="",
                        timestamp="",
                        score=edge.weight,
                        source="graph",
                        content_hash=edge.source_hash,
                    )
                )

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:limit]
