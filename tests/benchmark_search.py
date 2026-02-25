"""Benchmark script for Kioku search quality evaluation.

Runs a fixed set of Vietnamese queries against the real telegram database,
measuring search quality metrics for before/after model comparison.

Scoring v2 — entity_match replaced with 3 meaningful metrics:
  - graph_quality:    min(evidence_count/5, 1.0) — graph actually contributed
  - content_relevance: % of top-10 results containing any expected keyword
  - entity_resolved:  1 if any canonical form of expected entity was extracted

Usage:
    KIOKU_USER_ID=telegram uv run python tests/benchmark_search.py [--tag label]
"""

import json
import os
import sys
import time
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from kioku.service import KiokuService

# Benchmark queries — diverse Vietnamese personal memory queries
# expect_keywords: content words that should appear in result texts (language-agnostic)
# accept_entities: list of acceptable canonical / alias forms (any match = pass)
QUERIES = [
    # Entity-focused (people)
    {
        "q": "Mẹ tôi là người thế nào",
        "accept_entities": ["mẹ", "Mẹ", "mama", "mẹ tôi"],
        "expect_keywords": ["mẹ"],
        "category": "person",
    },
    {
        "q": "Bố tôi có đặc điểm gì",
        "accept_entities": ["bố", "Bố", "bố anh", "ba"],
        "expect_keywords": ["bố"],
        "category": "person",
    },
    {
        "q": "con gái tôi tính cách ra sao",
        "accept_entities": ["con", "Vy", "Phong", "con gái"],
        "expect_keywords": ["con", "Vy", "Phong"],
        "category": "person",
    },

    # Relationship queries
    {
        "q": "quan hệ giữa tôi và mẹ",
        "accept_entities": ["mẹ", "Mẹ", "anh", "Phúc", "Nguyễn Trọng Phúc", "phuc-nt"],
        "expect_keywords": ["mẹ"],
        "category": "relationship",
    },
    {
        "q": "ai có ảnh hưởng lớn nhất đến tôi",
        "accept_entities": ["mẹ", "Mẹ", "bố", "anh", "Phúc", "gia đình"],
        "expect_keywords": ["mẹ", "bố", "ảnh hưởng"],
        "category": "relationship",
    },

    # Work/topic queries
    {
        "q": "kinh nghiệm làm BrSE là gì",
        "accept_entities": ["BrSE", "Phúc", "anh", "đồng nghiệp"],
        "expect_keywords": ["BrSE", "kỹ sư"],
        "category": "topic",
    },
    {
        "q": "công việc ở TBV thế nào",
        "accept_entities": ["TBV", "công việc"],
        "expect_keywords": ["TBV"],
        "category": "topic",
    },
    {
        "q": "tôi đọc sách như thế nào",
        "accept_entities": ["sách", "đọc sách", "đọc", "reading"],
        "expect_keywords": ["sách", "đọc"],
        "category": "topic",
    },

    # Emotional/mood queries
    {
        "q": "khi nào tôi cảm thấy hạnh phúc nhất",
        "accept_entities": ["hạnh phúc", "gia đình", "mẹ", "bố", "anh"],
        "expect_keywords": ["hạnh phúc", "vui"],
        "category": "emotion",
    },
    {
        "q": "điều gì khiến tôi căng thẳng",
        "accept_entities": ["căng thẳng", "stress", "khủng hoảng", "áp lực"],
        "expect_keywords": ["căng thẳng", "stress", "áp lực"],
        "category": "emotion",
    },

    # General/profile queries
    {
        "q": "Nguyễn Trọng Phúc là ai",
        "accept_entities": ["Nguyễn Trọng Phúc", "Phúc", "phuc-nt", "anh", "self"],
        "expect_keywords": ["Phúc", "phuc-nt"],
        "category": "profile",
    },
    {
        "q": "gia đình tôi gồm những ai",
        "accept_entities": ["gia đình", "mẹ", "bố", "con", "bà nội"],
        "expect_keywords": ["gia đình", "mẹ", "bố"],
        "category": "profile",
    },

    # Temporal queries
    {
        "q": "chuyện gì xảy ra năm 2019",
        "accept_entities": ["2019", "năm 2019"],
        "expect_keywords": ["2019"],
        "category": "temporal",
    },
    {
        "q": "từ Nhật về Việt Nam",
        "accept_entities": ["Nhật", "Nhật Bản", "Japan", "Việt Nam"],
        "expect_keywords": ["Nhật", "Việt Nam", "về"],
        "category": "temporal",
    },

    # Broad abstract queries
    {
        "q": "ý nghĩa cuộc sống",
        "accept_entities": ["ý nghĩa", "cuộc sống", "mẹ", "gia đình", "anh"],
        "expect_keywords": ["ý nghĩa", "cuộc sống", "sống"],
        "category": "abstract",
    },
]


def score_query(result: dict, q_info: dict) -> dict:
    """Compute 3 quality scores for a single query result.

    Returns:
        graph_quality (0-1):    evidence contribution — 5 evidence = perfect
        content_relevance (0-1): % of top-10 results containing expected keyword
        entity_resolved (0/1):  any canonical form of expected entity was extracted
    """
    evidence = result.get("graph_context", {}).get("evidence", [])
    text_results = result.get("results", [])
    entities_used = result.get("entities_used", [])

    accept = q_info.get("accept_entities", [])
    keywords = q_info.get("expect_keywords", [])

    # 1. Graph quality: 5 evidence = full score
    graph_quality = min(len(evidence) / 5.0, 1.0)

    # 2. Content relevance: how many of top-10 results contain expected keywords
    if keywords and text_results:
        hits = sum(
            1 for r in text_results
            if any(kw.lower() in r.get("content", "").lower() for kw in keywords)
        )
        content_relevance = hits / len(text_results)
    else:
        content_relevance = 1.0  # No expectation = not penalized

    # 3. Entity resolved: any accept_entities form found in entities_used
    if accept:
        eu_lower = [e.lower() for e in entities_used]
        entity_resolved = 1 if any(
            any(acc.lower() in eu or eu in acc.lower() for eu in eu_lower)
            for acc in accept
        ) else 0
    else:
        entity_resolved = 1  # No expected entities = not penalized

    return {
        "graph_quality": round(graph_quality, 2),
        "content_relevance": round(content_relevance, 2),
        "entity_resolved": entity_resolved,
    }


def run_benchmark(svc: KiokuService, tag: str = "default"):
    """Run all benchmark queries and collect metrics."""
    results = []
    total_start = time.time()

    print(f"\n{'='*70}")
    print(f"  KIOKU SEARCH BENCHMARK — {tag.upper()}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Queries: {len(QUERIES)}")
    print(f"{'='*70}\n")

    for i, q_info in enumerate(QUERIES):
        query = q_info["q"]
        category = q_info["category"]

        start = time.time()
        try:
            result = svc.search_memories(query, limit=10)
        except Exception as e:
            print(f"  [{i+1:2d}] ❌ ERROR: {e}")
            results.append({"query": query, "category": category, "error": str(e)})
            continue
        elapsed = time.time() - start

        # Extract metrics
        entities_used = result.get("entities_used", [])
        count = result.get("count", 0)
        text_results = result.get("results", [])
        gc = result.get("graph_context", {})
        nodes = gc.get("nodes", [])
        evidence = gc.get("evidence", [])
        connections = result.get("connections", [])

        # Source breakdown
        sources: dict[str, int] = {}
        for r in text_results:
            src = r.get("source", "?")
            sources[src] = sources.get(src, 0) + 1

        # Quality scores
        scores = score_query(result, q_info)

        # Overall quality: weighted average of 3 scores
        overall = round(
            scores["graph_quality"] * 0.4
            + scores["content_relevance"] * 0.4
            + scores["entity_resolved"] * 0.2,
            2,
        )

        metrics = {
            "query": query,
            "category": category,
            "latency_s": round(elapsed, 2),
            "entities_extracted": entities_used,
            "text_results": count,
            "graph_nodes": len(nodes),
            "graph_evidence": len(evidence),
            "connections": len(connections),
            "sources": sources,
            "graph_quality": scores["graph_quality"],
            "content_relevance": scores["content_relevance"],
            "entity_resolved": scores["entity_resolved"],
            "overall_quality": overall,
            "bm25_pct": round(sources.get("bm25", 0) / max(count, 1) * 100),
            "vector_pct": round(sources.get("vector", 0) / max(count, 1) * 100),
            "graph_pct": round(sources.get("graph", 0) / max(count, 1) * 100),
        }
        results.append(metrics)

        # Print progress
        src_str = " ".join(f"{k}={v}" for k, v in sorted(sources.items()))
        ent_str = ",".join(entities_used[:4]) if entities_used else "none"
        q_icon = "✅" if overall >= 0.7 else ("⚠️" if overall >= 0.4 else "➖")
        print(
            f"  [{i+1:2d}] {q_icon} {elapsed:5.1f}s | "
            f"r={count:2d} n={len(nodes):2d} e={len(evidence):2d} | "
            f"gq={scores['graph_quality']:.1f} cr={scores['content_relevance']:.1f} "
            f"er={scores['entity_resolved']} → Q={overall:.2f}"
        )
        print(f"       {category:12s} | \"{query}\"")
        print(f"       ent=[{ent_str}]")

    total_elapsed = time.time() - total_start

    # Summary
    valid = [r for r in results if "error" not in r]
    avg_gq = sum(r["graph_quality"] for r in valid) / len(valid)
    avg_cr = sum(r["content_relevance"] for r in valid) / len(valid)
    avg_er = sum(r["entity_resolved"] for r in valid) / len(valid)
    avg_q = sum(r["overall_quality"] for r in valid) / len(valid)

    print(f"\n{'='*70}")
    print(f"  SUMMARY — {tag.upper()}")
    print(f"{'='*70}")
    print(f"  Total time:        {total_elapsed:.1f}s ({total_elapsed/len(QUERIES):.1f}s/query)")
    print(f"  Avg latency:       {sum(r['latency_s'] for r in valid)/len(valid):.1f}s")
    print(f"  Avg text results:  {sum(r['text_results'] for r in valid)/len(valid):.1f}")
    print(f"  Avg graph nodes:   {sum(r['graph_nodes'] for r in valid)/len(valid):.1f}")
    print(f"  Avg graph evidence:{sum(r['graph_evidence'] for r in valid)/len(valid):.1f}")
    print()
    print(f"  Quality metrics (0–1, higher is better):")
    print(f"    Graph quality:     {avg_gq:.2f}  (evidence depth)")
    print(f"    Content relevance: {avg_cr:.2f}  (results contain expected keywords)")
    print(f"    Entity resolved:   {avg_er:.2f}  (canonical entity found)")
    print(f"    ── Overall:        {avg_q:.2f}")

    # Source distribution
    total_bm25 = sum(r.get("sources", {}).get("bm25", 0) for r in valid)
    total_vec = sum(r.get("sources", {}).get("vector", 0) for r in valid)
    total_graph = sum(r.get("sources", {}).get("graph", 0) for r in valid)
    total_all = total_bm25 + total_vec + total_graph
    if total_all > 0:
        print(f"\n  Source distribution:")
        print(f"    BM25:   {total_bm25:3d} ({total_bm25/total_all*100:.0f}%)")
        print(f"    Vector: {total_vec:3d} ({total_vec/total_all*100:.0f}%)")
        print(f"    Graph:  {total_graph:3d} ({total_graph/total_all*100:.0f}%)")

    # Save to file
    output = {
        "tag": tag,
        "timestamp": datetime.now().isoformat(),
        "total_queries": len(QUERIES),
        "total_time_s": round(total_elapsed, 2),
        "avg_latency_s": round(sum(r["latency_s"] for r in valid) / len(valid), 2),
        "avg_graph_quality": round(avg_gq, 2),
        "avg_content_relevance": round(avg_cr, 2),
        "avg_entity_resolved": round(avg_er, 2),
        "avg_overall_quality": round(avg_q, 2),
        "source_distribution": {
            "bm25": total_bm25,
            "vector": total_vec,
            "graph": total_graph,
        },
        "results": results,
    }

    outfile = f"tests/benchmark_{tag}.json"
    with open(outfile, "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n  Results saved to: {outfile}")

    return output


if __name__ == "__main__":
    tag = sys.argv[1] if len(sys.argv) > 1 else "default"
    if tag.startswith("--tag"):
        tag = sys.argv[2] if len(sys.argv) > 2 else "default"

    svc = KiokuService()
    try:
        run_benchmark(svc, tag=tag)
    finally:
        svc.close()
