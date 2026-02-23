# Kioku — Phase 7 Dev Log

> Tracking progress for `docs/07-phase7-plan.md`
> **Objectives:** Bi-temporal Modeling, Entity Resolution, Universal Identifier

---

## 2026-02-24

### Task 1: Bi-temporal — event_time across all stores ✅

**Completed:**
- [x] `storage/markdown.py`: Added `event_time` field to `MemoryEntry`, `save_entry()` writes it to frontmatter, `_parse_entries()` reads it back
- [x] `pipeline/keyword_writer.py`: Added `event_time` column to SQLite schema (with ALTER TABLE migration for older DBs)
- [x] `pipeline/vector_writer.py`: Added `event_time` and `content_hash` metadata to ChromaDB
- [x] `pipeline/graph_writer.py`: `GraphEdge` dataclass now has `source_hash` field; FalkorDB upsert stores `event_time` and `source_hash` on edges
- [x] `pipeline/extractor.py`: New `EXTRACTION_PROMPT_TEMPLATE` with event_time extraction; `ExtractionResult` now has `event_time` field; `_parse_response` extracts `event_time` from JSON
- [x] `service.py`: Entity extraction happens first (to get event_time), then markdown save and indexing use the extracted event_time
- [x] `server.py` + `cli.py`: Added `sort_by` param to `get_timeline` tool/command

**Design decisions:**
- `event_time` is extracted by LLM from relative time expressions ("hôm qua", "năm ngoái", "tuổi 22") relative to `processing_date`
- `FakeExtractor` doesn't produce event_time (returns None) — graceful degradation
- Timeline `sort_by=event_time` filters out entries without event_time automatically

---

### Task 2: Entity Resolution — Context-aware extraction ✅

**Completed:**
- [x] `pipeline/graph_writer.py`: Added `get_canonical_entities()` to both `FalkorGraphStore` and `InMemoryGraphStore`
- [x] `pipeline/extractor.py`: `ClaudeExtractor.extract()` accepts `context_entities` list; prompt instructs LLM to reuse existing canonical names instead of creating duplicates
- [x] `service.py`: Before extraction, queries graph for top-50 canonical entities and passes them to extractor

**How it works:**
1. Before calling LLM, `save_memory()` queries `graph_store.get_canonical_entities(limit=50)`
2. The entity list is injected into the extraction prompt: *"The following entities already exist: [...]. If an entity in the text refers to one of these, use the EXISTING canonical name."*
3. This prevents graph fragmentation from synonyms/nicknames (e.g., "Mẹ" vs "Mom" vs "Mother")

---

### Task 3: Universal Identifier — content_hash as foreign key ✅

**Completed:**
- [x] `pipeline/keyword_writer.py`: Added `get_by_hashes()` method for O(1) batch lookup by content_hash
- [x] `pipeline/graph_writer.py`: Added `source_hash` field to `GraphEdge`; FalkorDB edges store `source_hash` for back-reference to SQLite
- [x] `pipeline/vector_writer.py`: `content_hash` passed through and stored as ChromaDB metadata; doc_id still uses hash[:16]
- [x] `service.py`: `content_hash` computed once in `save_memory()` and passed to all stores consistently

**Architecture:**
- SQLite is the **Primary Document Store** (single source of raw text)
- ChromaDB stores only vectors + lightweight metadata (content_hash for cross-reference)
- FalkorDB edges carry `source_hash` to trace back to original memory
- `get_by_hashes()` enables O(1) hydration: collect IDs from vector/graph, then batch-fetch full text from SQLite

---

### Task 4: Update Tests ✅

**Integration tests (23/23 passed):**
- 16 original tests + 7 new Phase 7 tests:
  - `test_save_returns_event_time` — event_time field present in save response
  - `test_event_time_in_sqlite` — event_time stored and retrievable via get_by_hashes
  - `test_get_by_hashes_empty` — empty input returns empty dict
  - `test_get_by_hashes_multiple` — batch lookup of 3 entries
  - `test_graph_canonical_entities` — get_canonical_entities returns list
  - `test_graph_source_hash_on_edges` — edges carry source_hash attribute
  - `test_get_timeline_sort_by_event_time` — timeline with sort_by parameter

**E2E tests (MCP + CLI):**
- MCP E2E: All 6 tools + 2 resources + 3 prompts + 2 Phase 7 tests passed
- CLI E2E: All 6 commands + 2 Phase 7 tests passed
- Verified event_time extraction: "cuối tuần" → 2026-02-22, "hôm qua" → 2026-02-23, "năm ngoái" → 2025-01-01

---

## Final Test Results

| Test Suite | Status |
|---|---|
| Integration tests (pytest) | **23/23 passed** (was 16/16) |
| All pytest tests | **70/70 passed** |
| MCP E2E (real DBs) | **All tools + Phase 7 tests passed** |
| CLI E2E (real DBs) | **All commands + Phase 7 tests passed** |
| Lint (ruff) | **3 pre-existing E402 warnings only** |

---

## Files Modified

| File | Changes |
|---|---|
| `src/kioku/service.py` | Reordered save pipeline; context-aware extraction; event_time + content_hash flow |
| `src/kioku/storage/markdown.py` | `event_time` in MemoryEntry, save_entry, _parse_entries |
| `src/kioku/pipeline/extractor.py` | New `EXTRACTION_PROMPT_TEMPLATE`; event_time in ExtractionResult; context_entities param |
| `src/kioku/pipeline/keyword_writer.py` | `event_time` column; `get_by_hashes()`; `sort_by` param in get_timeline |
| `src/kioku/pipeline/vector_writer.py` | `content_hash` + `event_time` in ChromaDB metadata |
| `src/kioku/pipeline/graph_writer.py` | `source_hash` on GraphEdge; `get_canonical_entities()` on both stores |
| `src/kioku/server.py` | `sort_by` param on get_timeline tool |
| `src/kioku/cli.py` | `--sort-by` option on timeline command |
| `tests/test_server.py` | 7 new Phase 7 test cases |
| `tests/e2e_mcp_client.py` | 2 new Phase 7 MCP E2E tests |
| `tests/e2e_cli.py` | 2 new Phase 7 CLI E2E tests |
