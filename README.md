# Kioku — Personal Memory Agent

**Kioku** (記憶 — *memory*) is a personal memory agent with tri-hybrid search. Save any thought, event, or feeling — Kioku stores it, understands the meaning, and retrieves it by **deep semantic context**.

```
You → "Went to coffee with Mai, discussed the OpenClaw project"
Kioku → saves to markdown, indexes BM25 + vector + knowledge graph
You → "Who is Mai?" or "What do I know about OpenClaw?"
Kioku → traverses the graph, finds connections, returns evidence
```

## Features

- **Tri-hybrid Search** — BM25 keyword + semantic vector + knowledge graph traversal, fused with RRF reranking
- **Dual Interface** — CLI for AI agents (OpenClaw, etc.) + MCP server for Claude Desktop / Cursor
- **Local-first** — All data on your machine. Markdown files are the source of truth
- **Graceful degradation** — Missing ChromaDB? BM25 still works. No FalkorDB? Skip graph. No Ollama? Fake embeddings

## Quick Start

### Option 1: CLI only (fastest)

```bash
pip install kioku-mcp[cli,vector]
kioku save "First memory — testing Kioku" --mood happy --tags test
kioku search "test"
kioku timeline --from 2026-02-24 --to 2026-02-24
```

### Option 2: Full stack with Docker

```bash
git clone https://github.com/phuc-nt/kioku_mcp.git && cd kioku_mcp
cp .env.example .env  # edit KIOKU_ANTHROPIC_API_KEY

# Start all databases
docker compose -f docker-compose.full.yml up -d

# Install with all features
pip install -e ".[full,dev]"

# Test
make test
kioku search "test"
```

### Option 3: MCP server (for Claude Desktop / Cursor)

```bash
pip install kioku-mcp[mcp,vector,graph]
python -m kioku.server
```

## Install Options

| Install command | What you get |
|---|---|
| `pip install kioku-mcp[cli]` | CLI only (BM25 search) |
| `pip install kioku-mcp[cli,vector]` | CLI + semantic search (ChromaDB + Ollama) |
| `pip install kioku-mcp[mcp]` | MCP server only |
| `pip install kioku-mcp[full]` | Everything: CLI + MCP + vector + graph |

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Interface Layer                        │
│                                                          │
│   server.py (MCP)              cli.py (Typer CLI)        │
│   @mcp.tool()                  @app.command()            │
│         │                            │                   │
│         └────────────┬───────────────┘                   │
│                      ▼                                   │
│             service.py (KiokuService)                    │
│             Single source of truth                       │
│                      │                                   │
│        ┌─────────────┼─────────────┐                     │
│        ▼             ▼             ▼                     │
│   pipeline/      search/      storage/                   │
│  (indexing)    (retrieval)   (markdown)                   │
│        │             │             │                      │
│        ▼             ▼             ▼                     │
│   ChromaDB      FalkorDB      SQLite FTS5               │
│   (vector)      (graph)       (keyword)                  │
└──────────────────────────────────────────────────────────┘
```

## CLI Commands

| Command | Description | Example |
|---|---|---|
| `kioku save` | Save a memory | `kioku save "Đi ăn phở với Minh" --mood happy --tags food,friend` |
| `kioku search` | Unified search (auto-extracts entities) | `kioku search "Minh dự án AI" --limit 10` |
| `kioku entities` | Browse entity vocabulary | `kioku entities --limit 50` |
| `kioku timeline` | Chronological entries | `kioku timeline --from 2026-02-01 --to 2026-02-28` |

`search` automatically extracts entities from the query using LLM + canonical entity vocabulary. Pass `--entities "X,Y"` to override.

## MCP Interface

**4 Tools:** `save_memory`, `search_memories` (with auto-extract), `list_entities`, `get_timeline`

**2 Resources:** `kioku://memories/{date}`, `kioku://entities/{entity}`

**3 Prompts:** `reflect_on_day`, `analyze_relationships`, `weekly_review`

## Docker

```bash
# Minimal: Kioku + Ollama (embedded ChromaDB, no graph)
docker compose -f docker-compose.minimal.yml up -d

# Full: Kioku + ChromaDB + FalkorDB + Ollama
docker compose -f docker-compose.full.yml up -d

# Use CLI inside container
docker compose exec kioku kioku search "test"
```

## Tech Stack

| Component | Technology |
|---|---|
| Core | Python 3.12+ / Pydantic |
| CLI | Typer |
| MCP Server | FastMCP |
| Vector DB | ChromaDB (server or embedded) |
| Graph DB | FalkorDB |
| Keyword Index | SQLite FTS5 |
| Embedding | Ollama (`nomic-embed-text`) |
| Entity Extraction | Claude Haiku 4.5 (Anthropic API) |

## Development

```bash
git clone https://github.com/phuc-nt/kioku_mcp.git && cd kioku_mcp
pip install -e ".[full,dev]"
docker compose up -d          # databases

uv run pytest tests/ -v         # 67 tests (mocked DBs)
python tests/e2e_mcp_client.py  # MCP E2E (real DBs)
python tests/e2e_cli.py         # CLI E2E (real DBs)
make lint                       # ruff check + format
```

## Docs

- [System Architecture](docs/architecture/system.md) ⭐
- [Search Architecture](docs/architecture/search.md) ⭐
- [Save Architecture](docs/architecture/save.md) ⭐
- [Requirements](docs/01-requirements.md)
- [System Design](docs/02-system-design.md)
- [Dev Log](docs/DEVLOG.md) | [Phase 8](docs/DEVLOG-phase8.md)

## License

MIT
