"""Benchmark script for Kioku search quality evaluation.

Runs a fixed set of Vietnamese queries against the real telegram database,
measuring search quality metrics for before/after model comparison.

Usage:
    KIOKU_USER_ID=telegram uv run python tests/benchmark_search.py [--tag before|after]
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
QUERIES = [
    # Entity-focused (people)
    {"q": "Mẹ tôi là người thế nào", "expect_entities": ["Mẹ"], "category": "person"},
    {"q": "Bố tôi có đặc điểm gì", "expect_entities": ["Bố"], "category": "person"},
    {"q": "con gái tôi tính cách ra sao", "expect_entities": ["Vy", "Phong"], "category": "person"},

    # Relationship queries
    {"q": "quan hệ giữa tôi và mẹ", "expect_entities": ["Mẹ", "Phúc"], "category": "relationship"},
    {"q": "ai có ảnh hưởng lớn nhất đến tôi", "expect_entities": ["Mẹ"], "category": "relationship"},

    # Work/topic queries
    {"q": "kinh nghiệm làm BrSE là gì", "expect_entities": ["BrSE"], "category": "topic"},
    {"q": "công việc ở TBV thế nào", "expect_entities": ["TBV"], "category": "topic"},
    {"q": "tôi đọc sách như thế nào", "expect_entities": ["sách"], "category": "topic"},

    # Emotional/mood queries
    {"q": "khi nào tôi cảm thấy hạnh phúc nhất", "expect_entities": [], "category": "emotion"},
    {"q": "điều gì khiến tôi căng thẳng", "expect_entities": ["stress"], "category": "emotion"},

    # General/profile queries
    {"q": "Nguyễn Trọng Phúc là ai", "expect_entities": ["Nguyễn Trọng Phúc"], "category": "profile"},
    {"q": "gia đình tôi gồm những ai", "expect_entities": ["gia đình"], "category": "profile"},

    # Temporal queries
    {"q": "chuyện gì xảy ra năm 2019", "expect_entities": ["2019"], "category": "temporal"},
    {"q": "từ Nhật về Việt Nam", "expect_entities": ["Nhật", "Việt Nam"], "category": "temporal"},

    # Broad abstract queries
    {"q": "ý nghĩa cuộc sống", "expect_entities": [], "category": "abstract"},
]


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
        expect = q_info["expect_entities"]

        start = time.time()
        try:
            result = svc.search_memories(query, limit=10)
        except Exception as e:
            print(f"  [{i+1:2d}] ❌ ERROR: {e}")
            results.append({"query": query, "error": str(e)})
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
        sources = {}
        for r in text_results:
            src = r.get("source", "?")
            sources[src] = sources.get(src, 0) + 1

        # Entity match score
        entity_match = 0
        if expect:
            matched = sum(1 for e in expect if any(e.lower() in eu.lower() for eu in entities_used))
            entity_match = matched / len(expect) if expect else 0

        # Content relevance (simple: check if any expected entity in results text)
        content_hits = 0
        if expect:
            for r in text_results:
                content = r.get("content", "").lower()
                if any(e.lower() in content for e in expect):
                    content_hits += 1

        metrics = {
            "query": query,
            "category": category,
            "latency_s": round(elapsed, 2),
            "entities_extracted": entities_used,
            "entity_match_score": round(entity_match, 2),
            "text_results": count,
            "graph_nodes": len(nodes),
            "graph_evidence": len(evidence),
            "connections": len(connections),
            "sources": sources,
            "content_hits": content_hits,
            "bm25_pct": round(sources.get("bm25", 0) / max(count, 1) * 100),
            "vector_pct": round(sources.get("vector", 0) / max(count, 1) * 100),
            "graph_pct": round(sources.get("graph", 0) / max(count, 1) * 100),
        }
        results.append(metrics)

        # Print progress
        src_str = " ".join(f"{k}={v}" for k, v in sorted(sources.items()))
        ent_str = ",".join(entities_used) if entities_used else "none"
        match_icon = "✅" if entity_match >= 0.5 else ("⚠️" if entity_match > 0 else "➖")
        print(f"  [{i+1:2d}] {match_icon} {elapsed:5.1f}s | r={count:2d} n={len(nodes):2d} e={len(evidence):2d} | {src_str:30s} | ent=[{ent_str}]")
        print(f"       {category:12s} | \"{query}\"")

    total_elapsed = time.time() - total_start

    # Summary
    valid = [r for r in results if "error" not in r]
    print(f"\n{'='*70}")
    print(f"  SUMMARY — {tag.upper()}")
    print(f"{'='*70}")
    print(f"  Total time:        {total_elapsed:.1f}s ({total_elapsed/len(QUERIES):.1f}s/query)")
    print(f"  Avg latency:       {sum(r['latency_s'] for r in valid)/len(valid):.1f}s")
    print(f"  Avg text results:  {sum(r['text_results'] for r in valid)/len(valid):.1f}")
    print(f"  Avg graph nodes:   {sum(r['graph_nodes'] for r in valid)/len(valid):.1f}")
    print(f"  Avg graph evidence:{sum(r['graph_evidence'] for r in valid)/len(valid):.1f}")

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

    # Entity extraction quality
    with_expect = [r for r in valid if r.get("entity_match_score") is not None and any(True for q in QUERIES if q["q"] == r["query"] and q["expect_entities"])]
    if with_expect:
        avg_match = sum(r["entity_match_score"] for r in with_expect) / len(with_expect)
        print(f"\n  Entity extraction:")
        print(f"    Avg match score: {avg_match:.0%}")
        full_match = sum(1 for r in with_expect if r["entity_match_score"] >= 1.0)
        print(f"    Full match:      {full_match}/{len(with_expect)}")

    # Save to file
    output = {
        "tag": tag,
        "timestamp": datetime.now().isoformat(),
        "total_queries": len(QUERIES),
        "total_time_s": round(total_elapsed, 2),
        "avg_latency_s": round(sum(r["latency_s"] for r in valid) / len(valid), 2),
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
