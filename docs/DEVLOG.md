# Kioku MCP — Development Log

## 2026-02-22 (Day 1)

### Phase 1: Foundation — Skeleton + Save + Keyword Search ✅

**Completed:**
- [x] Project structure created
- [x] `pyproject.toml` with dependencies
- [x] `docker-compose.yml` (FalkorDB + ChromaDB + Ollama)
- [x] `.env.example`
- [x] `src/kioku/config.py` — settings & paths
- [x] `src/kioku/storage/markdown.py` — read/write memory markdown
- [x] `src/kioku/pipeline/keyword_writer.py` — SQLite FTS5 indexing
- [x] `src/kioku/search/bm25.py` — keyword search
- [x] `src/kioku/server.py` — FastMCP entry point with `save_memory` + `search_memories`
- [x] Tests: 31 passed
- [x] Pushed to GitHub

---

### Phase 2: Vector Search (Semantic) ✅

**Completed:**
- [x] `src/kioku/pipeline/embedder.py` — OllamaEmbedder + FakeEmbedder (for tests)
- [x] `src/kioku/pipeline/vector_writer.py` — ChromaDB vector store (add, search, dedup)
- [x] `src/kioku/search/semantic.py` — vector similarity search wrapper
- [x] Updated `server.py` — hybrid BM25 + Vector search via RRF reranker
- [x] Updated `save_memory` — now indexes into both FTS5 and ChromaDB
- [x] `tests/test_vector.py` — 11 tests (embedder, vector store, semantic search)
- [x] Fixed ChromaDB test isolation with unique collection names
- [x] Fixed `n_results` clamping for empty collections
- [x] Tests: 42 passed (31 Phase 1 + 11 Phase 2)

**Notes:**
- ChromaDB >=0.6.3 required (1.5.x incompatible with Python 3.14; using Python 3.13)
- FakeEmbedder used when Ollama is unavailable — deterministic hash-based vectors
- Server auto-detects Ollama on startup; falls back to FakeEmbedder gracefully
- ChromaDB EphemeralClient shares state within process — tests use uuid-based collection names for isolation

---
