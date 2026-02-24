# Search Architecture — How It Works

> Last updated: 2026-02-24 (Phase 8)

## Overview

The `search_memories` tool is the primary retrieval mechanism in Kioku. It provides a unified interface that combines three search strategies with automatic entity extraction and graph enrichment.

## Pipeline

```
User Question
  ↓
Agent (LLM) — Query Enrichment
  ↓ Replaces pronouns, adds known entity names
Enriched Query
  ↓
┌──────────────────────────────────────┐
│  search_memories(query)              │
│                                      │
│  1. Auto-Extract Entities            │
│     ├── Fetch top 50 canonical       │
│     │   entities from FalkorDB       │
│     ├── LLM extractor matches        │
│     │   query → entity vocabulary    │
│     └── Result: entity list          │
│                                      │
│  2. Tri-Hybrid Search                │
│     ├── BM25 (SQLite FTS5)           │
│     │   Keywords: entity names       │
│     ├── Vector (ChromaDB)            │
│     │   Semantic: original query     │
│     │   Filter: entity-relevant only │
│     └── Graph (FalkorDB)             │
│         Seeds: extracted entities    │
│                                      │
│  3. RRF Reranking                    │
│     └── Fuse BM25+Vector+Graph       │
│         into top-N results           │
│                                      │
│  4. Hydration (SQLite)               │
│     └── Replace all content with     │
│         authoritative SQLite text    │
│                                      │
│  5. Graph Context Enrichment         │
│     ├── Traverse entity neighbors    │
│     │   (2-hop, limit 20/entity)     │
│     ├── Collect nodes + edges        │
│     ├── Dedup evidence vs text       │
│     ├── Hydrate edge evidence        │
│     │   from SQLite                  │
│     ├── Budget: ≤20 heavyweight      │
│     └── Find shortest paths          │
│         between entity pairs         │
└──────────────────────────────────────┘
  ↓
Response JSON
  ↓
Agent (LLM) — Synthesize Answer
  ↓
User Reply
```

## Response Structure

```json
{
  "query": "Nguyễn Trọng Phúc profile gia đình...",
  "entities_used": ["Phúc", "Phong", "Vy", "BrSE", "TBV"],
  "count": 10,
  "results": [
    {
      "content": "Full hydrated text from SQLite...",
      "source": "vector",    // bm25 | vector | graph
      "score": 0.016,
      "date": "2026-02-24",
      "mood": "motivated"
    }
  ],
  "graph_context": {
    "nodes": [
      {"name": "Mẹ", "type": "PERSON", "mention_count": 21},
      {"name": "BrSE", "type": "TOPIC", "mention_count": 4}
    ],
    "evidence": [
      {
        "source": "BrSE",
        "target": "2021",
        "type": "TEMPORAL",
        "weight": 1.0,
        "evidence": "Năm 2021 - Chất lượng hơn số lượng..."
      }
    ]
  },
  "connections": [
    {
      "from": "Phong",
      "to": "Vy",
      "paths": [["Phong", "con", "Vy"]]
    }
  ]
}
```

## Component Roles

### BM25 (SQLite FTS5)
- **Strength:** Exact keyword matches, entity name lookups
- **In entity mode:** Searches using entity names as keywords
- **Observed contribution:** ~60% of results for specific entity queries

### Vector (ChromaDB + Ollama)
- **Strength:** Semantic similarity, conceptual queries
- **In entity mode:** Searches original query, then filters to results mentioning entities
- **Observed contribution:** ~16% of results, strong for mood/conceptual queries

### Graph (FalkorDB)
- **Strength:** Relationship discovery, multi-hop traversal
- **In entity mode:** Uses entities as seeds, traverses 2-hop neighborhood
- **Observed contribution:** ~24% of results, dominates for relationship queries

### Auto-Extract (LLM)
- **Engine:** Same ClaudeExtractor as save_memory
- **Input:** Query text + top 50 canonical entity names from DB
- **Output:** List of matched entity names
- **Cost:** ~3s latency, 1 LLM call per search (when entities not provided)

## Budget System

Total heavyweight entries (text results + graph evidence) are capped at **20**.

```
text_results:  min(N, limit)     → occupies budget first
evidence_budget = 20 - len(text_results)
graph_evidence:  top-K by weight → fills remaining budget
```

Graph evidence is **deduplicated** against text results using content_hash. Nodes and connections are lightweight metadata and always included.

## Real-World Performance (2026-02-24)

### Query: "Nguyễn Trọng Phúc profile gia đình công việc BrSE TBV kỹ năng con Phong Vy"

| Component | Contribution |
|---|---|
| Auto-extracted entities | 7: ['Nguyễn Trọng Phúc', 'Phong', 'Vy', 'Công việc', 'BrSE', 'TBV', 'kỹ năng'] |
| Text results | 10 (vector=5, graph=5) |
| Graph nodes | 74 |
| Graph evidence | 10 (unique, deduplicated) |
| Connections | 8 paths (Phúc↔BrSE, Phong↔Vy, etc.) |
| Response size | 19,096 chars JSON |
| User wait time | ~25s total |

### Latency Breakdown:
| Phase | Time | % |
|---|---|---|
| Agent enrichment | ~2s | 8% |
| Auto-extract (LLM) | ~3s | 12% |
| BM25+Vector+Graph search | ~4s | 16% |
| Graph traversal + hydration | ~4s | 16% |
| Agent reply synthesis (LLM) | ~12s | 48% |
| **Total** | **~25s** | 100% |
