# Kioku MCP Server 🧠

**Kioku** (記憶 — *ký ức*) là một MCP Server đóng vai trợ lý lưu trữ ký ức cá nhân. Nhắn bất kỳ suy nghĩ, sự kiện, cảm xúc nào → Kioku lưu trữ, hiểu ngữ nghĩa, và truy vấn lại theo **ý nghĩa sâu** — giúp bạn lý giải bản thân và không bao giờ quên các ký ức quan trọng.

## Tính năng

- 📝 **Zero-friction capture** — Nhắn tin tự do, Kioku tự lưu + index
- 🔍 **Tri-hybrid Search** — Keyword (BM25) + Semantic (Vector) + Knowledge Graph
- 🧩 **MCP Protocol** — Dùng được với OpenClaw, Claude Desktop, Cursor
- 🔒 **Local-first** — Mọi thứ chạy trên máy, dữ liệu thuộc về bạn
- 📄 **Markdown = Source of Truth** — Dữ liệu gốc luôn đọc được bằng mắt

## Tech Stack

| Component | Technology |
|---|---|
| MCP Server | Python + FastMCP |
| Vector DB | ChromaDB (Docker) |
| Graph DB | FalkorDB (Docker) |
| Keyword Index | SQLite FTS5 |
| Embedding | Ollama (local) |
| Entity Extraction | Claude Haiku 4.5 (API) |

## Quick Start

```bash
# Clone
git clone git@github.com:phuc-nt/kioku_mcp.git
cd kioku_mcp

# Setup Python env
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Copy env config
cp .env.example .env

# Start DBs (Phase 2+)
docker compose up -d

# Run tests
make test

# Run MCP server
python -m kioku.server
```

## Project Structure

```
src/kioku/
├── server.py                 # FastMCP entry point
├── config.py                 # Settings
├── storage/markdown.py       # Markdown read/write (Source of Truth)
├── pipeline/
│   └── keyword_writer.py     # SQLite FTS5 indexing
├── search/
│   ├── bm25.py               # Keyword search
│   └── reranker.py           # RRF fusion
└── tools/                    # (Phase 2-3)
```

## MCP Tools

| Tool | Description |
|---|---|
| `save_memory` | Lưu ký ức mới (text + mood + tags) |
| `search_memories` | Tìm kiếm tri-hybrid |
| `get_memories_by_date` | Xem nhật ký theo ngày |
| `list_memory_dates` | Liệt kê các ngày có nhật ký |
| `recall_related` | Truy xuất mạng quan hệ đa chiều từ một người/sự vật |
| `explain_connection` | Phân tích mối liên kết giữa 2 thực thể |
| `get_timeline` | Lấy dòng thời gian các sự kiện |
| `get_life_patterns` | Thống kê xu hướng tâm trạng và chủ đề |

## MCP Resources & Prompts

- **Resources**: `kioku://memories/{date}`, `kioku://entities/{entity}`
- **Prompts**: `reflect_on_day`, `analyze_relationships`, `weekly_review`

## Roadmap

- [x] **Phase 1** — Save + Keyword Search (BM25)
- [x] **Phase 2** — Vector Search (ChromaDB + Ollama)
- [x] **Phase 3** — Knowledge Graph (FalkorDB + Entity Extraction)
- [x] **Phase 4** — MCP Resources, Prompts & Polish
- [ ] **Phase 5** — OpenClaw Integration

## Docs

- [`docs/01-requirements.md`](docs/01-requirements.md) — Requirements
- [`docs/02-system-design.md`](docs/02-system-design.md) — System Design & Tech Stack
- [`docs/03-implementation-plan.md`](docs/03-implementation-plan.md) — Implementation Plan
- [`docs/DEVLOG.md`](docs/DEVLOG.md) — Daily Progress
- [`docs/ISSUES.md`](docs/ISSUES.md) — Issue Tracker

## License

Private project.
