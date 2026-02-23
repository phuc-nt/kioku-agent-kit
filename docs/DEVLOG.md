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

### Phase 4: Resources, Prompts & Polish ✅

**Completed:**
- [x] Implemented MCP Resources: `kioku://memories/{date}` and `kioku://entities/{entity}` for direct Markdown/Profile reading.
- [x] Implemented MCP Prompts: `reflect_on_day`, `analyze_relationships`, `weekly_review`.
- [x] New Tool: `get_timeline` — fetch chronologically ordered events.
- [x] New Tool: `get_life_patterns` — analyze tags and moods over time using frequency counting.
- [x] Test coverage: 19 integration tests spanning all updated tools, resources, and prompts.
- [x] Fixed ChromaDB connection issue where vector metrics weren't persisting due to implicit ephemeral client.
- [x] Pushed to GitHub.

**Total: 8 MCP Tools + 3 Prompts + 2 Resources**
| Features | Added In |
|---|---|
| `get_timeline` | Phase 4 |
| `get_life_patterns` | Phase 4 |
| `kioku://memories/*` | Phase 4 |
| `kioku://entities/*` | Phase 4 |

---

### Phase 5: Refinement & Prompt Engineering ✅ (2026-02-23)

**Completed:**
- [x] Refactored `server.py`: Dropped `get_memories_by_date` and `get_life_patterns` to stick strictly to the Minimalist RAG Architecture.
- [x] Restructured OpenClaw `AGENTS.md` core instructions: Defined clear use cases preventing the LLM from misusing the master key `search_memories` for entity queries.
- [x] Forced priority of Knowledge Graph extraction (`recall_related`, `explain_connection`) for "Who is/What is/Why" relationship questions.
- [x] Patched SQLite `FTS5` punctuation bug: Fixed regex sanitization in `search_memories` to safely strip punctuation before executing `bm25_search`.
- [x] Reset local DB Context and resolved recurrent `openclaw gateway stop` LaunchAgent detachment issues. Evaluated Gateway reset workflows.

**Notes:**
- `LLM Bias` pushes agents toward generic summary tools like `search_memories`. Writing strict negative constraints (e.g., "CRITICAL WARNING - DO NOT USE IF...") inside prompt structures successfully enforces path traversal tools (`recall_related`).

---

### Phase 6: Dual Interface (MCP + CLI) Restructure ✅ (2026-02-23)

**Completed:**
- [x] Refactored `server.py` and extracted all business logic into `service.py` (`KiokuService`).
- [x] Created `cli.py` to expose 6 commands using `typer`: `save`, `search`, `recall`, `explain`, `dates`, `timeline`.
- [x] Implemented embedded ChromaDB mode fallback to remove Docker dependency for CLI users.
- [x] Configured optional dependencies in `pyproject.toml` (`[cli]`, `[mcp]`, `[full]`).
- [x] Dockerized the full stack (`minimal` and `full` compose setups).
- [x] Added robust integrations tests (63/63 passing) and E2E Tests for both MCP and CLI modes.
- [x] Verified 100% data isolation for `test_user` when running E2E.

**See `docs/06-restructure-plan.md` and `docs/DEVLOG-restructure.md` for full breakdown.**
