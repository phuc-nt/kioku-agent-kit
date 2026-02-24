# DEVLOG — Phase 8: Search Unification & Auto-Extract

**Date:** 2026-02-24  
**Author:** phucnt (with AI pair programming)

---

## Overview

This phase consolidates the search toolset from 6 tools down to 4, with the flagship `search_memories` tool becoming fully self-contained through automatic entity extraction.

## Changes Made

### 1. Tool Consolidation (6 → 4 tools)

**Removed:**
- `recall_related` — graph traversal for entity profiling → merged into `search_memories`
- `explain_connection` — shortest path between entities → merged into `search_memories`
- `list_memory_dates` — list dates with entries → superseded by `get_timeline`

**Retained:**
| Tool | Purpose |
|---|---|
| `search_memories` | Unified read: text + graph context + connections |
| `list_entities` | Browse entity vocabulary |
| `get_timeline` | Chronological queries |
| `save_memory` | Write new memories |

### 2. Unified `search_memories` Response

When entities are detected (auto or manual), the response now includes:

```json
{
  "query": "enriched query text",
  "entities_used": ["Mẹ", "Bố", "Phong"],
  "count": 10,
  "results": [...],            // Text results (BM25+Vector+Graph, RRF-ranked)
  "graph_context": {
    "nodes": [...],            // Entity nodes: name, type, mention_count
    "evidence": [...]          // Unique hydrated relationship evidence
  },
  "connections": [...]         // Shortest paths between entity pairs
}
```

**Budget enforcement:** Total heavyweight entries (text + graph evidence) capped at 20. Graph evidence is deduplicated against text results and sorted by edge weight.

### 3. Auto-Extract Entities

When `entities` parameter is not provided, `search_memories` now automatically:
1. Fetches top 50 canonical entities from FalkorDB
2. Uses LLM extractor (same as `save_memory`) to extract entities from query
3. Enters entity-focused mode with auto-extracted entities

This means the Agent only needs to call `search_memories("query")` — no need to call `list_entities` first.

### 4. Query Enrichment (Agent-Level)

Agent instructions updated to require **query enrichment** before calling search:
- Replace pronouns ("tôi", "bạn") with real names
- Expand vague queries with known context
- Add entity names when known

**Example:**
```
User: "bạn biết gì về tôi"
Agent enriches: "Nguyễn Trọng Phúc profile gia đình công việc BrSE TBV kỹ năng con Phong Vy"
→ Auto-extract: ['Nguyễn Trọng Phúc', 'Phong', 'Vy', 'Công việc', 'BrSE', 'TBV', 'kỹ năng']
→ Results: 10 text + 74 nodes + 10 evidence + 8 connections
```

## Test Results (2026-02-24, user=telegram)

### Before Query Enrichment:
| Query | Entities | Results | Nodes | Evidence |
|---|---|---|---|---|
| "tôi ai" | ['tôi'] | 3 | 0 | 0 |
| "Hùng" | ['Hùng'] | 0 | 0 | 0 |

### After Query Enrichment:
| Query | Entities | Results | Nodes | Evidence |
|---|---|---|---|---|
| "Phúc profile gia đình BrSE TBV..." | 7 entities | 10 | 74 | 10 |
| "công việc Phúc TBV BrSE stress..." | 7 entities | 10 | 61 | 10 |

### Source Distribution:
```
BM25 (Keywords):  60% → dominant for exact entity matches
Graph (KG):       24% → strong for relationship queries
Vector (Semantic): 16% → good for conceptual/mood queries
```

### Latency:
```
Auto-extract entities:  ~3s
BM25 + Vector + Graph:  ~4s
Graph traversal:        ~4s
Agent LLM reply:       ~12s
────────────────────────
Total user wait:       ~25s
```

## Files Modified

### Code:
- `src/kioku/service.py` — Unified search with graph context, auto-extract
- `src/kioku/server.py` — Removed recall, explain, dates MCP tools
- `src/kioku/cli.py` — Removed recall, explain, dates CLI commands
- `tests/test_server.py` — Updated tests for new tool set

### Agent Config:
- `AGENTS.md` — Rewritten for 4-tool architecture + query enrichment
- `SOUL.md` — Updated search workflow instructions

## Commits
1. `refactor: remove recall, explain, dates tools — consolidated into search`
2. `feat: auto-extract entities in search when not provided`
