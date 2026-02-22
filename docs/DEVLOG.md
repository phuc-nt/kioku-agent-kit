# Kioku MCP — Development Log

## 2026-02-22 (Day 1)

### Phase 1: Foundation — Skeleton + Save + Keyword Search ✅

**Completed:**
- [x] Project structure, pyproject.toml, docker-compose, .env
- [x] Markdown storage (source of truth)
- [x] SQLite FTS5 keyword indexing + BM25 search
- [x] FastMCP server with 4 tools
- [x] 31 tests passed
- [x] Pushed to GitHub

---

### Phase 2: Vector Search (Semantic) ✅

**Completed:**
- [x] OllamaEmbedder + FakeEmbedder
- [x] ChromaDB VectorStore (add, search, dedup)
- [x] Semantic search wrapper + hybrid BM25/Vector via RRF
- [x] 42 tests passed (31 + 11)
- [x] Pushed to GitHub

**Notes:**
- Python 3.13 required (ChromaDB incompatible with 3.14)
- FakeEmbedder auto-fallback when Ollama unavailable

---

### Phase 3: Knowledge Graph ✅

**Completed:**
- [x] `pipeline/extractor.py` — ClaudeExtractor (Haiku API) + FakeExtractor (rule-based)
- [x] `pipeline/graph_writer.py` — FalkorGraphStore (Cypher) + InMemoryGraphStore (for tests)
- [x] `search/graph.py` — seed entity → multi-hop traversal → evidence collection
- [x] Updated `server.py` — tri-hybrid search (BM25 + Vector + KG via RRF)
- [x] New tool: `recall_related` — graph traversal from any entity
- [x] New tool: `explain_connection` — shortest path between 2 entities
- [x] Updated `save_memory` — extracts entities + writes to knowledge graph
- [x] `tests/test_graph.py` — 13 tests (extractor, graph store, graph search)
- [x] Updated `tests/test_server.py` — 15 tests for all 6 tools
- [x] 61 tests passed (31 + 11 + 19)
- [x] Pushed to GitHub

**Design decisions:**
- FalkorDB uses `MERGE` for upsert — mention_count increments, last_seen updates
- Entity relationships average weights on re-encounter
- InMemoryGraphStore implements BFS for path finding
- Graceful fallback chain: FalkorDB → InMemoryGraphStore, Claude → FakeExtractor

**Total: 6 MCP Tools**
| Tool | Source |
|---|---|
| `save_memory` | Phase 1 |
| `search_memories` | Phase 1 (upgraded each phase) |
| `get_memories_by_date` | Phase 1 |
| `list_memory_dates` | Phase 1 |
| `recall_related` | Phase 3 |
| `explain_connection` | Phase 3 |

---
