# Kioku — Restructure Dev Log (Dual Interface: MCP + CLI)

> Tracking progress for `docs/06-restructure-plan.md`

---

## 2026-02-23

### Phase 0: Refactor — Tách Service Layer ✅

**Completed:**
- [x] Tạo `src/kioku/service.py` — class `KiokuService` chứa toàn bộ business logic
  - 6 tool methods: `save_memory`, `search_memories`, `recall_related`, `explain_connection`, `list_memory_dates`, `get_timeline`
  - 2 resource methods: `read_memory_resource`, `read_entity_resource`
  - 3 prompt methods: `reflect_on_day`, `analyze_relationships`, `weekly_review`
  - `__init__` khởi tạo tất cả infrastructure (embedder, vector_store, graph_store, extractor, keyword_index) với graceful fallback
- [x] Refactor `src/kioku/server.py` — thin MCP wrapper, mỗi `@mcp.tool()` chỉ delegate 1 dòng sang `_svc.<method>()`
- [x] Cập nhật `tests/test_server.py` — monkeypatch `_svc` attributes thay vì module-level globals
- [x] Integration tests: **16/16 passed**
- [x] MCP E2E test (real DBs): **All 6 tools + 2 resources + 3 prompts passed**

**Design decisions:**
- `KiokuService.__init__` nhận optional `Settings` — dùng singleton mặc định nếu không truyền
- `_svc` là module-level instance trong `server.py` — khởi tạo 1 lần khi import

---

### Phase 1: Thêm CLI Interface ✅

**Completed:**
- [x] Thêm `typer>=0.24.1` vào dependencies
- [x] Tạo `src/kioku/cli.py` — 6 commands: `save`, `search`, `recall`, `explain`, `dates`, `timeline`
  - Lazy-init `KiokuService` để `--help` không trigger slow startup
  - Output JSON với `ensure_ascii=False` cho tiếng Việt
  - Tags nhận comma-separated string (`--tags work,meeting`)
- [x] Thêm `[project.scripts]` entry point: `kioku = "kioku.cli:app"`
- [x] Tạo `tests/e2e_cli.py` — E2E test cho tất cả 6 CLI commands
- [x] CLI E2E test (real DBs): **All 6 commands passed**

**CLI syntax examples:**
```bash
kioku save "Đi ăn phở với Minh" --mood happy --tags food,friend
kioku search "dự án AI" --limit 5
kioku recall "Minh" --hops 2
kioku explain "Minh" "AI"
kioku dates
kioku timeline --from 2026-02-01 --to 2026-02-23 --limit 10
```

---

### Phase 2: ChromaDB Embedded Mode ✅

**Completed:**
- [x] Thêm `chroma_mode` setting: `"server"`, `"embedded"`, hoặc `"auto"` (default)
- [x] Thêm `chroma_persist_dir` setting (default: `~/.kioku/data/chroma`)
- [x] `_init_vector_store()` trong `KiokuService` hỗ trợ auto-detect: server → embedded → ephemeral
- [x] `VectorStore` đã hỗ trợ `persist_dir` param từ trước — không cần sửa
- [x] All tests pass: 16/16 integration + MCP E2E + CLI E2E

**Config env vars:**
```bash
KIOKU_CHROMA_MODE=auto      # auto (default) | server | embedded
KIOKU_CHROMA_PERSIST_DIR=   # default: ~/.kioku/data/chroma
```

---

### Phase 3: Optional Dependencies & PyPI Packaging ✅

**Completed:**
- [x] Refactor `pyproject.toml` — core deps chỉ còn `pydantic`, `pydantic-settings`, `python-dotenv`
- [x] Extras: `cli` (typer), `mcp` (fastmcp), `vector` (chromadb, ollama), `graph` (falkordb, anthropic), `full` (tất cả)
- [x] Lazy import `chromadb` trong `vector_writer.py` (moved inside `__init__`)
- [x] Guard import cho `fastmcp` trong `server.py` — raise clear error message
- [x] Guard import cho `typer` trong `cli.py` — raise clear error message
- [x] `ollama`, `anthropic`, `falkordb` đã lazy từ trước (import inside class methods)
- [x] `uv build` tạo wheel thành công
- [x] All tests pass: 16/16 integration + MCP E2E + CLI E2E

**Install options:**
```bash
pip install kioku-mcp[cli]        # CLI only
pip install kioku-mcp[mcp]        # MCP server only
pip install kioku-mcp[cli,vector] # CLI + semantic search
pip install kioku-mcp[full]       # Everything
```

---

### Phase 4: Docker Packaging ✅

**Completed:**
- [x] Tạo `Dockerfile` — `python:3.12-slim`, cài `kioku[full]`, flexible entrypoint (mcp/cli)
- [x] Tạo `scripts/docker-entrypoint.sh` — wait for services, auto-pull Ollama model, route mcp/cli
- [x] Tạo `docker-compose.minimal.yml` — Kioku (embedded ChromaDB) + Ollama only
- [x] Tạo `docker-compose.full.yml` — Kioku + ChromaDB server + FalkorDB + Ollama
- [x] Cập nhật `.env.example` với tất cả `KIOKU_*` env vars mới
- [x] Docker build thành công, image size: **1.07GB** (< 2GB target)
- [x] Container CLI verified: `docker run --rm kioku-mcp:test cli --help` works

**Docker usage:**
```bash
# Minimal (embedded ChromaDB, no graph)
docker compose -f docker-compose.minimal.yml up -d

# Full stack (all features)
docker compose -f docker-compose.full.yml up -d

# CLI inside container
docker compose exec kioku kioku search "test"
```

---

### Phase 5: Distribution-Ready (Partial) ✅

**Completed:**
- [x] GitHub Actions CI: `.github/workflows/ci.yml`
  - Test matrix: Python 3.11/3.12/3.13 × extras (cli, mcp, full)
  - Lint (ruff) on full + 3.12
  - Integration tests on full
  - Import verification per extra
  - Build wheel + upload artifact
- [x] `uv build` produces valid wheel

**Remaining (manual steps):**
- [ ] Viết lại `README.md` với quick start guide
- [ ] Publish lên PyPI
- [ ] Publish Docker image lên ghcr.io
- [ ] Tạo GitHub Release

---

## Final Test Results

| Test Suite | Status |
|---|---|
| Integration tests (pytest) | **16/16 passed** |
| MCP E2E (real DBs) | **All 6 tools + 2 resources + 3 prompts passed** |
| CLI E2E (real DBs) | **All 6 commands passed** |
| Docker build | **1.07GB image, CLI works** |
| Wheel build | **kioku_mcp-0.1.0-py3-none-any.whl** |
