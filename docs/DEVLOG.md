# Kioku MCP — Development Log

## 2026-02-22 (Day 1)

### Phase 1: Foundation — Skeleton + Save + Keyword Search

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
- [x] `tests/test_storage.py` — markdown storage tests
- [x] `tests/test_bm25.py` — keyword search tests
- [x] `tests/test_server.py` — MCP tool integration tests
- [x] `Makefile` — dev commands

**Notes:**
- Phase 1 chỉ dùng SQLite FTS5 (BM25). Vector + Graph sẽ thêm ở Phase 2-3.
- MCP server chạy trên host (stdio), DBs chạy Docker.
- Markdown files lưu tại `~/.kioku/memory/` (configurable).

---
