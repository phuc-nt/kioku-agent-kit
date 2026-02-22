# Kioku MCP — Issues & TODOs

## 🔴 Blockers
_(none)_

## 🟡 Open Issues

### Phase 5 (OpenClaw Integration)
- [ ] #P5-1: Create `kioku` agent in OpenClaw
- [ ] #P5-2: Write SOUL.md for Kioku
- [ ] #P5-3: Bind Telegram bot
- [ ] #P5-4: End-to-end test

## 🟢 Resolved
- [x] #P1-1: Project skeleton — 2026-02-22
- [x] #P1-2: `save_memory` tool — 2026-02-22
- [x] #P1-3: SQLite FTS5 indexing — 2026-02-22
- [x] #P1-4: `search_memories` (BM25 only) — 2026-02-22
- [x] #P1-5: Test suite (storage + search + server) — 2026-02-22
- [x] #P2-1: Setup Ollama container — 2026-02-22 (Docker Compose)
- [x] #P2-2: `pipeline/embedder.py` — 2026-02-22
- [x] #P2-3: `pipeline/vector_writer.py` (ChromaDB) — 2026-02-22
- [x] #P2-4: `search/semantic.py` — 2026-02-22
- [x] #P2-5: RRF fusion BM25 + Vector — 2026-02-22
- [x] #P2-6: Hybrid `search_memories` tool — 2026-02-22
- [x] #P3-1: `pipeline/extractor.py` (LLM entity extraction) — 2026-02-22
- [x] #P3-2: `pipeline/graph_writer.py` (FalkorDB + InMemory) — 2026-02-22
- [x] #P3-3: `search/graph.py` (multi-hop traversal) — 2026-02-22
- [x] #P3-4: RRF 3-way fusion — 2026-02-22
- [x] #P3-5: `recall_related` tool — 2026-02-22
- [x] #P3-6: `explain_connection` tool — 2026-02-22
- [x] #P4-1: MCP Resources (`kioku://memories/*`, `kioku://entities/*`) — 2026-02-22
- [x] #P4-2: MCP Prompts (`reflect_on_day`, `weekly_review`, `find_why`) — 2026-02-22
- [x] #P4-3: `get_timeline` tool — 2026-02-22
- [x] #P4-4: `get_life_patterns` tool — 2026-02-22
- [x] #P4-5: Error handling & logging — 2026-02-22
