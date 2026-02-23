# Kioku — Restructure Plan: Dual Interface (MCP + CLI)

> Doc ID: 06 | Created: 2026-02-23 | Status: Draft

---

## 1. Bối cảnh

### 1.1. Hiện trạng

Kioku hiện là một MCP server thuần (Python + FastMCP), được tích hợp vào hệ thống OpenClaw thông qua **mcporter** — một CLI tool bên thứ ba đóng vai bridge giữa agent và MCP server:

```
OpenClaw Agent (Kioku)
    │
    │ gọi bash: mcporter call kioku.save_memory --args '{...}'
    ▼
mcporter (spawn process)
    │
    │ MCP stdio handshake → tools/list → tools/call
    ▼
Kioku MCP Server (uv run src/kioku/server.py)
    │
    ▼
SQLite + ChromaDB + FalkorDB
```

Cách tích hợp này hoạt động nhưng tồn tại nhiều vấn đề (xem mục 1.2).

Về mặt source code, toàn bộ business logic (khởi tạo services, save, search, graph traversal...) nằm trực tiếp trong `server.py` — file đồng thời là MCP entry point. Không có lớp trung gian nào giữa MCP interface và logic xử lý.

### 1.2. Các vấn đề cần giải quyết

**Vấn đề 1 — Hiệu năng kém qua mcporter:**
Mỗi lần agent gọi một tool, mcporter spawn MCP server mới, thực hiện MCP handshake, gọi `tools/list`, rồi mới gọi `tools/call`. Toàn bộ quá trình mất ~2-3 giây cold start cho mỗi lần gọi. Với Kioku là second brain được gọi thường xuyên (save, search, recall...), delay này tích lũy đáng kể.

**Vấn đề 2 — Agent dễ hallucinate syntax:**
Agent phải viết JSON nesting phức tạp trong bash string:
`mcporter call kioku.save_memory --args '{"text":"...","mood":"happy","tags":["food"]}'`
JSON bên trong single-quote bash dễ lỗi escape, agent thường nhầm syntax, lỗi im lặng.

**Vấn đề 3 — Token overhead cao:**
MCP protocol yêu cầu agent nắm full JSON schema của tất cả tools. Theo benchmark cộng đồng, MCP schema overhead tiêu tốn ~5% context window trước khi agent bắt đầu làm việc thực sự. CLI flags tiêu tốn ít token hơn đáng kể vì LLM đã quen pattern này từ training data.

**Vấn đề 4 — Không tách được interface khỏi logic:**
`server.py` chứa cả initialization, business logic, và MCP decorator. Muốn thêm CLI hoặc bất kỳ interface nào khác phải duplicate code.

**Vấn đề 5 — Không đóng gói được cho user khác:**
`fastmcp` là required dependency. User chỉ muốn dùng CLI phải cài cả MCP stack. Ngược lại, user chỉ cần MCP phải cài cả CLI dependencies. Không có cách nào cài tùy chọn.

### 1.3. Tại sao thêm CLI — không phải chỉ tối ưu MCP?

Quyết định này dựa trên nhiều yếu tố hội tụ:

- **Triết lý OpenClaw:** Creator của OpenClaw (Armin Ronacher, Steinberger) đã nói rõ rằng CLI là hướng đi chính cho tool integration, không phải MCP. OpenClaw không có native MCP client và chủ động disable MCP capabilities.
- **Benchmark thực tế:** Nhiều benchmark 2026 cho thấy CLI tools đạt hiệu quả token cao hơn 28-35% so với MCP, completion score cao hơn, và khả năng multi-step reasoning tốt hơn vì không bị context window bloat.
- **Tương thích rộng hơn:** CLI hoạt động với bất kỳ hệ thống nào có bash — không chỉ MCP client. Bất kỳ AI agent framework nào có exec/bash tool đều dùng được Kioku CLI ngay.
- **Giữ MCP cho ecosystem khác:** MCP vẫn có giá trị cho Claude Desktop, Cursor, hoặc bất kỳ MCP client nào khác. Không bỏ, chỉ thêm CLI song song.

### 1.4. Mục tiêu tái cấu trúc

1. Tách business logic ra khỏi MCP interface thành `KiokuService` dùng chung.
2. Thêm CLI interface (`cli.py`) gọi vào cùng `KiokuService`.
3. Update tính năng chỉ cần sửa `service.py` → cả MCP lẫn CLI đều có ngay.
4. Cho phép user cài tùy chọn: `pip install kioku[cli]`, `pip install kioku[mcp]`, hoặc `pip install kioku[full]`.
5. Đóng gói Docker cho full stack (app + databases).

---

## 2. Target Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     Interface Layer                          │
│                                                              │
│   ┌────────────────┐              ┌────────────────┐         │
│   │   server.py    │              │    cli.py       │         │
│   │  (MCP adapter) │              │  (CLI adapter)  │         │
│   │  @mcp.tool()   │              │  @app.command() │         │
│   └───────┬────────┘              └───────┬────────┘         │
│           │                               │                  │
│           └───────────┬───────────────────┘                  │
│                       ▼                                      │
│              ┌─────────────────┐                             │
│              │   service.py    │                             │
│              │  KiokuService   │  ← Single source of truth   │
│              └────────┬────────┘                             │
│                       │                                      │
│         ┌─────────────┼─────────────┐                        │
│         ▼             ▼             ▼                        │
│    pipeline/      search/      storage/                      │
│   (indexing)    (retrieval)   (markdown)                      │
│                                                              │
│         │             │             │                         │
│         ▼             ▼             ▼                        │
│    ┌─────────┐  ┌──────────┐  ┌───────────┐                │
│    │ ChromaDB│  │ FalkorDB │  │  SQLite   │                 │
│    └─────────┘  └──────────┘  │+ Markdown │                 │
│                               └───────────┘                 │
└──────────────────────────────────────────────────────────────┘
```

### Thay đổi file

```
src/kioku/
├── config.py        — không đổi
├── pipeline/        — không đổi
├── search/          — không đổi
├── storage/         — không đổi
│
├── service.py       — MỚI: KiokuService class, chứa toàn bộ logic
├── server.py        — SỬA: chỉ còn thin MCP wrappers gọi service
└── cli.py           — MỚI: Typer CLI gọi service
```

---

## 3. Implementation Phases

### Phase 0 — Refactor: Tách Service Layer

**Mục tiêu:** Tách toàn bộ business logic từ `server.py` vào `service.py`, server.py chỉ còn là thin MCP wrapper. Đây là nền tảng cho mọi phase sau — không thay đổi tính năng, không thay đổi hành vi.

**Việc cần làm:**

1. Tạo `src/kioku/service.py` chứa class `KiokuService`:
   - Di chuyển toàn bộ phần khởi tạo infrastructure (embedder, vector_store, graph_store, extractor, keyword_index) vào `__init__`.
   - Di chuyển toàn bộ phần thân logic của 8 tool functions thành 8 methods trong class.
   - Di chuyển phần logic của 2 resources và 3 prompts thành methods tương ứng.
2. Cập nhật `server.py`:
   - Import `KiokuService`, khởi tạo một instance `_svc`.
   - Mỗi `@mcp.tool()` function chỉ còn gọi `_svc.<method>()` và return kết quả.
   - Giữ nguyên docstring trong `@mcp.tool()` — FastMCP đọc từ đây cho MCP schema.
   - Resources và prompts cũng chuyển sang gọi `_svc`.
3. Chạy toàn bộ test suite hiện có — đảm bảo pass 100%.
4. Test thủ công qua mcporter — đảm bảo OpenClaw agent hoạt động y hệt cũ.

**Definition of Done:**
- [ ] `service.py` tồn tại với class `KiokuService` chứa đủ 8 public methods tương ứng 8 MCP tools.
- [ ] `server.py` không còn chứa business logic — mỗi `@mcp.tool()` chỉ là 1-3 dòng delegate.
- [ ] Không có code duplication giữa `server.py` và `service.py`.
- [ ] `pytest` pass 100% — không regression.
- [ ] `mcporter call kioku.<tool>` hoạt động đúng cho tất cả 8 tools.
- [ ] Kioku agent trên Telegram hoạt động bình thường (test save + search + recall).

---

### Phase 1 — Thêm CLI Interface

**Mục tiêu:** Tạo `cli.py` dùng Typer, expose đủ 8 commands tương ứng 8 tools. Agent Kioku có thể chuyển sang dùng CLI thay vì mcporter.

**Việc cần làm:**

1. Thêm `typer>=0.12` vào `[project.dependencies]` (hoặc optional, tùy quyết định Phase 3).
2. Tạo `src/kioku/cli.py`:
   - 8 commands: `save`, `search`, `recall`, `connect`, `day`, `dates`, `timeline`, `patterns`.
   - Mỗi command gọi `KiokuService.<method>()`.
   - Output JSON ra stdout (ensure_ascii=False cho tiếng Việt).
   - Mỗi command có `--help` tự giải thích.
3. Thêm `[project.scripts]` vào `pyproject.toml`: `kioku = "kioku.cli:app"`.
4. Chạy `uv sync` để register CLI entry point.
5. Viết tests cho CLI: test từng command, test output format, test error cases.
6. Cập nhật `TOOLS.md` của Kioku agent (`~/.openclaw/workspace-kioku/TOOLS.md`):
   - Thay hướng dẫn mcporter bằng hướng dẫn CLI.
   - Ví dụ: `kioku save "text" --mood happy` thay vì `mcporter call kioku.save_memory --args '{...}'`.
7. Cập nhật `SOUL.md` nếu cần — thay reference mcporter thành kioku CLI.

**Definition of Done:**
- [ ] `kioku --help` hiển thị danh sách commands.
- [ ] `kioku <command> --help` hiển thị hướng dẫn cho từng command.
- [ ] Tất cả 8 commands hoạt động đúng, output JSON hợp lệ.
- [ ] `kioku save "test" --mood happy --tags work,test` → lưu thành công, return JSON.
- [ ] `kioku search "test" --limit 5` → trả kết quả search.
- [ ] CLI tests pass.
- [ ] `TOOLS.md` đã cập nhật — agent dùng CLI syntax.
- [ ] Kioku agent trên Telegram hoạt động bình thường qua CLI (không còn dùng mcporter).

---

### Phase 2 — ChromaDB Embedded Mode

**Mục tiêu:** Hỗ trợ ChromaDB chạy embedded (trong cùng process) bên cạnh server mode hiện tại. Giúp user không cần Docker cho ChromaDB khi cài standalone.

**Việc cần làm:**

1. Cập nhật `config.py`:
   - Thêm setting `chroma_mode`: `"server"` (mặc định hiện tại) hoặc `"embedded"`.
   - Thêm setting `chroma_persist_dir` cho embedded mode (mặc định `~/.kioku/data/chroma`).
2. Cập nhật `pipeline/vector_writer.py`:
   - Nếu `chroma_mode == "embedded"`: dùng `chromadb.PersistentClient(path=...)`.
   - Nếu `chroma_mode == "server"`: giữ nguyên `chromadb.HttpClient(host, port)`.
   - Nếu cả hai không available: fallback gracefully (giữ hành vi hiện tại).
3. Auto-detect: nếu user không set `chroma_mode` explicitly, thử server trước → fallback embedded → fallback no vector search.
4. Cập nhật `.env.example` với chroma_mode option.
5. Test: embedded mode save + search hoạt động không cần Docker ChromaDB.

**Definition of Done:**
- [ ] `KIOKU_CHROMA_MODE=embedded kioku search "test"` hoạt động không cần ChromaDB Docker.
- [ ] `KIOKU_CHROMA_MODE=server kioku search "test"` hoạt động y hệt cũ.
- [ ] Không set mode → auto-detect: thử server → embedded → skip.
- [ ] Data persist qua restart khi dùng embedded mode.
- [ ] Tests cover cả hai mode.

---

### Phase 3 — Optional Dependencies & PyPI Packaging

**Mục tiêu:** Tách dependencies thành extras để user cài đúng thứ mình cần. Chuẩn bị publish lên PyPI.

**Việc cần làm:**

1. Refactor `pyproject.toml`:
   - Core dependencies chỉ còn: `pydantic`, `pydantic-settings`, `python-dotenv`.
   - Extras: `cli` (typer), `mcp` (fastmcp), `vector` (chromadb, ollama), `graph` (falkordb, anthropic), `full` (tất cả).
2. Refactor imports trong `service.py` thành lazy import:
   - `from kioku.pipeline.vector_writer import VectorStore` chỉ import khi `chromadb` available.
   - `from kioku.pipeline.graph_writer import FalkorGraphStore` chỉ import khi `falkordb` available.
   - Thiếu package nào → fallback gracefully với warning rõ ràng.
3. Tương tự cho `server.py`: chỉ import `fastmcp` nếu có, raise lỗi rõ ràng nếu user cố chạy MCP server mà không cài `[mcp]` extra.
4. Tương tự cho `cli.py`: chỉ import `typer` nếu có.
5. Cập nhật `pyproject.toml` metadata: `description`, `author`, `license`, `homepage`, `classifiers`, `readme`.
6. Test từng combo install:
   - `pip install kioku[cli]` → CLI works, MCP không có.
   - `pip install kioku[mcp]` → MCP works, CLI không có.
   - `pip install kioku[cli,vector]` → CLI + semantic search, không graph.
   - `pip install kioku[full]` → tất cả.

**Definition of Done:**
- [ ] `pip install kioku[cli]` cài thành công, `kioku --help` chạy, không lỗi import fastmcp.
- [ ] `pip install kioku[mcp]` cài thành công, MCP server chạy, không lỗi import typer.
- [ ] `pip install kioku` (không extra) cài thành công nhưng warn rằng cần chọn `[cli]` hoặc `[mcp]`.
- [ ] Lazy import test: import kioku trong Python REPL không fail dù thiếu optional deps.
- [ ] `pyproject.toml` có đủ metadata cho PyPI.
- [ ] `uv build` hoặc `python -m build` tạo được wheel thành công.

---

### Phase 4 — Docker Packaging

**Mục tiêu:** User có thể chạy toàn bộ stack (Kioku + databases) bằng một lệnh `docker compose up`.

**Việc cần làm:**

1. Tạo `Dockerfile`:
   - Base image: `python:3.12-slim`.
   - Cài `kioku[full]`.
   - Entry point linh hoạt: MCP server (default) hoặc CLI (override CMD).
2. Mở rộng `docker-compose.yml` hiện có:
   - Thêm service `kioku` với build context, environment, volumes, depends_on.
   - Mount volume cho `~/.kioku` data.
3. Tạo `docker-compose.minimal.yml`:
   - Chỉ `kioku` + `ollama`. Không FalkorDB, không ChromaDB server (dùng embedded).
   - Phù hợp user muốn chạy nhẹ nhất có thể.
4. Tạo `docker-compose.full.yml`:
   - Kioku + ChromaDB server + FalkorDB + Ollama.
   - Phù hợp user muốn full features.
5. Viết `scripts/docker-entrypoint.sh`:
   - Tự động pull Ollama model nếu chưa có.
   - Health check cho dependencies trước khi start Kioku.
6. Test: `docker compose up` từ clean state → hoạt động end-to-end.

**Definition of Done:**
- [ ] `docker compose -f docker-compose.minimal.yml up -d` → Kioku chạy với embedded ChromaDB + Ollama.
- [ ] `docker compose -f docker-compose.full.yml up -d` → Full stack chạy.
- [ ] `docker compose exec kioku kioku search "test"` → CLI hoạt động trong container.
- [ ] Data persist qua `docker compose down` + `docker compose up`.
- [ ] Ollama model tự pull lần đầu.
- [ ] Image size hợp lý (< 2GB không kể Ollama model).

---

### Phase 5 — Distribution-Ready

**Mục tiêu:** Kioku sẵn sàng cho người dùng bên ngoài: documentation rõ ràng, publish PyPI, CI/CD.

**Việc cần làm:**

1. Viết lại `README.md`:
   - Quick start cho 3 cấp user: CLI-only, CLI + semantic, Full Docker.
   - Architecture diagram (text-based).
   - Bảng so sánh install options.
2. Tạo `CONTRIBUTING.md` nếu cần.
3. Setup GitHub Actions CI:
   - Test matrix: Python 3.11, 3.12, 3.13 × extras (`cli`, `mcp`, `full`).
   - Lint (ruff).
   - Build wheel.
4. Publish lên PyPI: `kioku` package.
5. Tạo GitHub Release với changelog.
6. Publish Docker image lên GitHub Container Registry (ghcr.io).

**Definition of Done:**
- [ ] `pip install kioku[cli]` cài được từ PyPI.
- [ ] `docker pull ghcr.io/<owner>/kioku:latest` pull được.
- [ ] README có hướng dẫn đủ rõ để user mới setup từ zero trong < 5 phút.
- [ ] CI pass trên tất cả matrix entries.
- [ ] Ít nhất 1 user bên ngoài test thành công (có thể là chính mình trên máy khác).

---

## 4. Thứ tự và phụ thuộc

```
Phase 0  →  Phase 1  →  Phase 2  →  Phase 3  →  Phase 4  →  Phase 5
(refactor)  (CLI)       (embed)     (package)    (Docker)    (publish)
   │           │                       │
   │           │                       │
   └───────────┴── Kioku agent dùng    └── User bên ngoài
                   CLI ngay từ đây         cài được từ đây
```

- **Phase 0 → 1** là critical path — sau Phase 1, Kioku agent đã dùng CLI được, giải quyết ngay vấn đề latency và hallucination.
- **Phase 2 → 3** độc lập về logic nhưng Phase 3 phụ thuộc Phase 2 (cần embedded mode để tách dependency).
- **Phase 4 → 5** là distribution phase, có thể làm song song một phần.

---

## 5. Nguyên tắc xuyên suốt

- **Không breaking change cho MCP:** MCP interface phải hoạt động y hệt cũ ở mọi phase. User đang dùng qua Claude Desktop, Cursor, hoặc mcporter không bị ảnh hưởng.
- **Graceful degradation:** Thiếu ChromaDB → no vector search (nhưng BM25 vẫn hoạt động). Thiếu FalkorDB → no graph search. Thiếu Ollama → fake embeddings. Thiếu Anthropic key → rule-based extraction. Không bao giờ crash vì thiếu optional dependency.
- **Single source of truth:** `service.py` là nơi duy nhất chứa business logic. Nếu phải sửa logic ở hai nơi nghĩa là thiết kế sai.
- **Test trước, sửa sau:** Mỗi phase bắt đầu bằng đảm bảo test suite pass, kết thúc bằng đảm bảo test suite pass.
