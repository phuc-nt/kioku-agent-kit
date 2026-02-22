"""RRF Reranker — fuses results from multiple search backends."""

from __future__ import annotations

from kioku.search.bm25 import SearchResult


def rrf_rerank(
    *result_lists: list[SearchResult],
    k: int = 60,
    limit: int = 10,
) -> list[SearchResult]:
    """Reciprocal Rank Fusion across multiple result lists.

    Args:
        *result_lists: One or more lists of SearchResult (e.g., BM25, Vector, Graph).
        k: RRF constant (default 60, standard value).
        limit: Max results to return.

    Returns:
        Merged and reranked list of SearchResult.
    """
    # content -> (best SearchResult, accumulated RRF score)
    scores: dict[str, tuple[SearchResult, float]] = {}

    for results in result_lists:
        for rank_pos, result in enumerate(results):
            rrf_score = 1.0 / (k + rank_pos + 1)
            key = result.content  # Dedupe by content

            if key in scores:
                existing_result, existing_score = scores[key]
                scores[key] = (existing_result, existing_score + rrf_score)
            else:
                scores[key] = (result, rrf_score)

    # Sort by accumulated RRF score (descending)
    ranked = sorted(scores.values(), key=lambda x: x[1], reverse=True)

    # Update score on results and return
    output = []
    for result, score in ranked[:limit]:
        result.score = score
        output.append(result)

    return output
