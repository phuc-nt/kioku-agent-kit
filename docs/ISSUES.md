# Kioku MCP — Issues & TODOs

## 🔴 Blockers
_(none)_

## 🟡 Open Issues

### Phase 3 (Knowledge Graph)
- [ ] #P3-1: Implement `pipeline/extractor.py` (LLM entity extraction)

- [ ] #P3-2: Implement `pipeline/graph_writer.py` (FalkorDB)
- [ ] #P3-3: Implement `search/graph.py` (multi-hop traversal)
- [ ] #P3-4: Update `search/reranker.py` (RRF 3-way)
- [ ] #P3-5: Implement `recall_related` tool
- [ ] #P3-6: Implement `explain_connection` tool

### Phase 4 (Resources, Prompts & Polish)
- [ ] #P4-1: MCP Resources (`kioku://memories/*`, `kioku://entities/*`)
- [ ] #P4-2: MCP Prompts (`reflect_on_day`, `weekly_review`, `find_why`)
- [ ] #P4-3: `get_timeline` tool
- [ ] #P4-4: `get_life_patterns` tool
- [ ] #P4-5: Error handling & logging

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
