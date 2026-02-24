# Save Architecture — How It Works

> Last updated: 2026-02-24 (Phase 8)

## Overview

The `save_memory` tool is the ingestion pipeline for Kioku. It takes raw text from the user and indexes it across three storage engines simultaneously, with intelligent entity extraction for the knowledge graph.

## Pipeline

```
User shares info / Agent calls save
  ↓
┌──────────────────────────────────────────────┐
│  save_memory(text, mood, tags)               │
│                                              │
│  1. Content Hash                             │
│     └── SHA256(text) → content_hash          │
│         (dedup key across all stores)        │
│                                              │
│  2. Entity Extraction (LLM)                  │
│     ├── Fetch top 50 canonical entities      │
│     │   from FalkorDB (disambiguation)       │
│     ├── Claude Haiku extracts:               │
│     │   • Entities (name, type)              │
│     │   • Relationships (source→target,      │
│     │     type, weight, evidence)             │
│     │   • Event time (relative date parsing)  │
│     └── Result: ExtractionResult             │
│                                              │
│  3. Write to 4 stores (parallel-ish):        │
│     ├── FalkorDB (Knowledge Graph)           │
│     │   └── upsert(entities, relationships)  │
│     ├── Markdown (Source of Truth)            │
│     │   └── append to YYYY-MM-DD.md          │
│     ├── SQLite FTS5 (Keyword Index)          │
│     │   └── index(text, date, mood, hash)    │
│     └── ChromaDB (Vector Store)              │
│         └── add(text, embedding, metadata)   │
└──────────────────────────────────────────────┘
  ↓
Response: {status, date, mood, tags, event_time, indexed}
```

## Storage Engines

### 1. Markdown Files (Source of Truth)
- **Path:** `~/.kioku/users/{user_id}/memory/YYYY-MM-DD.md`
- **Format:** Timestamped entries with metadata headers
- **Purpose:** Human-readable, git-trackable, portable
- **Content:** Raw text + mood + tags + event_time

### 2. SQLite FTS5 (Keyword Index)
- **Path:** `~/.kioku/users/{user_id}/kioku.db`
- **Purpose:** BM25 full-text search, date filtering, primary document store for hydration
- **Fields:** content, date, timestamp, mood, content_hash, event_time
- **Key role:** All search results are **hydrated** from SQLite to ensure consistent text

### 3. ChromaDB (Vector Store)
- **Host:** `localhost:8000` (server mode) or embedded
- **Collection:** `kioku_{user_id}`
- **Embedding:** Ollama `nomic-embed-text` (768-dim)
- **Purpose:** Semantic similarity search
- **Graceful degradation:** If ChromaDB/Ollama unavailable, save continues without vector indexing

### 4. FalkorDB (Knowledge Graph)
- **Host:** `localhost:6379`
- **Graph name:** `kioku_{user_id}`
- **Schema:**
  ```
  (:Entity {name, type, mention_count})
  -[:REL_TYPE {weight, evidence, source_hash, date}]->
  (:Entity)
  ```
- **Entity types:** PERSON, PLACE, EVENT, EMOTION, TOPIC, PRODUCT
- **Relationship types:** CAUSAL, EMOTIONAL, TEMPORAL, TOPICAL, INVOLVES

## Entity Extraction Detail

The extractor (Claude Haiku) receives:
1. **Text:** The raw user input
2. **Context entities:** Top 50 canonical entity names from the graph (for disambiguation)
3. **Processing date:** Current date (for relative time parsing)

It returns:
```python
ExtractionResult(
    entities=[Entity(name="Mẹ", type="PERSON"), ...],
    relationships=[
        Relationship(
            source="Mẹ", target="giỏi",
            type="EMOTIONAL", weight=0.9,
            evidence="Mẹ giỏi và cầu toàn..."
        ), ...
    ],
    event_time="2025-03-15"  # parsed from "hồi tháng 3 năm ngoái"
)
```

**Context-aware disambiguation:** When the extractor sees "Hùng" in the text, it checks against canonical entities. If "Hùng" exists as PERSON with 4 mentions, it reuses the exact same name instead of creating "sếp Hùng" as a new entity.

## Graceful Degradation

| Component Down | Impact |
|---|---|
| FalkorDB | Skip graph indexing, entity extraction. BM25 + Vector still work. |
| ChromaDB/Ollama | Skip vector indexing. BM25 + Graph still work. |
| Claude API | Skip entity extraction entirely. All 3 stores still index text. |
| SQLite | ❌ Critical — BM25 search and hydration fail |
| Markdown dir | ❌ Critical — source of truth unavailable |

## Content Hash Linking

The `content_hash` (SHA256) is the universal key that links the same memory across all stores:

```
Markdown entry  ─── content_hash ───┐
SQLite row      ─── content_hash ───┤
ChromaDB doc    ─── content_hash ───┤
Graph edge      ─── source_hash  ───┘
```

This enables:
- **Search hydration:** Graph edge → source_hash → SQLite row → full text
- **Deduplication:** Same text won't be indexed twice
- **Cross-store consistency:** All stores reference the same content
