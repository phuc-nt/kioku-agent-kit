# Kioku Agent Kit

**Kioku** (記憶 — *memory*) is a personal memory engine for AI agents. Save any thought, event, or feeling — Kioku stores it, understands context, and retrieves it via **tri-hybrid search** (BM25 + semantic vector + knowledge graph).

```
You → "Went to coffee with Mai, discussed the AI project"
Kioku → saves to markdown + indexes BM25 + vector + knowledge graph
You → "Who is Mai?" or "What did I discuss last week?"
Kioku → traverses the graph, finds connections, returns evidence
```

Designed to be used by AI agents (OpenClaw, Claude Code, Cursor, etc.) as a long-term memory CLI tool — or as an MCP server for Claude Desktop.

---

## Quick Start

### Option 1: CLI only (fastest, BM25 only)

```bash
pip install kioku-agent-kit[cli]
kioku save "First memory — testing Kioku" --mood happy --tags test
kioku search "test"
```

### Option 2: Full stack with Docker (recommended)

```bash
git clone https://github.com/phuc-nt/kioku-agent-kit.git && cd kioku-agent-kit
cp .env.example .env  # add KIOKU_ANTHROPIC_API_KEY

# Start databases (ChromaDB + FalkorDB + Ollama)
docker compose up -d

# Install with all features
pip install -e ".[full]"

# Test
kioku save "Hello Kioku" --mood happy
kioku search "hello"
```

### Option 3: MCP Server (for Claude Desktop / Cursor)

```bash
pip install kioku-agent-kit[mcp,vector,graph]
python -m kioku.server
```

Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "kioku": {
      "command": "python",
      "args": ["-m", "kioku.server"],
      "env": { "KIOKU_USER_ID": "myproject" }
    }
  }
}
```

### Option 4: Claude Code (CLI agent mode)

If you have a blank project and want Claude Code to use Kioku:

```bash
# 1-liner to bootstrap any project
curl -fsSL https://raw.githubusercontent.com/phuc-nt/kioku-agent-kit/main/scripts/bootstrap.sh | bash
```

Or manually:
```bash
# Strongly recommended: use Python 3.12 for ChromaDB compatibility
python3.12 -m venv .venv
source .venv/bin/activate
pip install "kioku-agent-kit[full]"
kioku init  # Creates CLAUDE.md and .claude/skills/kioku/SKILL.md
```

Then just type `claude` and start! **Important:** In your first prompt, tell Claude: *"I just ran kioku init. Read .claude/skills/kioku/SKILL.md and complete the setup as instructed."*

The generated `.claude/skills/kioku/SKILL.md` contains the specific instructions for Claude to dynamically load the virtual environment and configs for each subprocess call.

---

## Install Options

| Command | What you get |
|---|---|
| `pip install kioku-agent-kit[cli]` | CLI + BM25 keyword search |
| `pip install kioku-agent-kit[cli,vector]` | + semantic search (ChromaDB + Ollama) |
| `pip install kioku-agent-kit[mcp]` | MCP server only |
| `pip install "kioku-agent-kit[full]"` | Everything: CLI + MCP + vector + graph |

---

## CLI Commands

| Command | Description | Example |
|---|---|---|
| `kioku save TEXT` | Save a memory | `kioku save "Lunch with Mai" --mood happy --tags food,friend` |
| `kioku search QUERY` | Unified search (BM25 + vector + graph) | `kioku search "Mai AI project" --limit 10` |
| `kioku entities` | Browse entity vocabulary | `kioku entities --limit 50` |
| `kioku timeline` | Chronological entries | `kioku timeline --from 2026-02-01 --to 2026-02-28` |

`search` automatically extracts entities from the query using LLM + canonical entity vocabulary. Pass `--entities "X,Y"` to override.

**Environment:**
```bash
KIOKU_USER_ID=myproject          # data isolation key (default: default)
KIOKU_ANTHROPIC_API_KEY=sk-ant-  # for entity extraction (optional — degrades gracefully)
KIOKU_OLLAMA_MODEL=bge-m3        # embedding model (default: bge-m3)
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Interface Layer                       │
│                                                         │
│   server.py (MCP)           cli.py (Typer CLI)          │
│   @mcp.tool()               @app.command()              │
│         │                         │                     │
│         └───────────┬─────────────┘                     │
│                     ▼                                   │
│           service.py (KiokuService)                     │
│                     │                                   │
│        ┌────────────┼────────────┐                      │
│        ▼            ▼            ▼                      │
│   pipeline/     search/      storage/                   │
│  (indexing)   (retrieval)   (markdown)                  │
│        │            │            │                      │
│        ▼            ▼            ▼                      │
│   ChromaDB     FalkorDB     SQLite FTS5                │
│   (vector)     (graph)      (keyword)                   │
└─────────────────────────────────────────────────────────┘
```

**Search pipeline:** BM25 + Vector + Graph → RRF rerank → Graph context enrichment → Results with evidence

**Save pipeline:** Markdown → SQLite FTS5 → ChromaDB embedding → FalkorDB entity/relationship graph

---

## MCP Interface (for Claude Desktop)

**4 Tools:** `save_memory`, `search_memories`, `list_entities`, `get_timeline`

**2 Resources:** `kioku://memories/{date}`, `kioku://entities/{entity}`

**3 Prompts:** `reflect_on_day`, `analyze_relationships`, `weekly_review`

---

## Docker

```bash
# Full: Kioku + ChromaDB + FalkorDB + Ollama
docker compose up -d

# Minimal: no graph DB
docker compose -f docker-compose.minimal.yml up -d

# Use CLI inside container
docker compose exec kioku kioku search "test"
```

---

## Graceful Degradation

| Missing | Fallback |
|---|---|
| Ollama / ChromaDB | Fake embeddings (BM25 still works) |
| FalkorDB | InMemoryGraphStore (search still works) |
| Anthropic API key | No auto entity extraction (pass `--entities` manually) |

Kioku never crashes on missing infrastructure — it just skips the unavailable component.

---

## Tech Stack

| Component | Technology |
|---|---|
| Core | Python 3.12+ / Pydantic |
| CLI | Typer |
| MCP Server | FastMCP |
| Vector DB | ChromaDB |
| Graph DB | FalkorDB |
| Keyword Index | SQLite FTS5 |
| Embedding | Ollama (`bge-m3`) |
| Entity Extraction | Claude Haiku 4.5 (Anthropic API) |

---

## Development

```bash
git clone https://github.com/phuc-nt/kioku-agent-kit.git && cd kioku-agent-kit
pip install -e ".[full,dev]"
docker compose up -d

uv run pytest tests/ -v           # unit tests (mocked DBs)
python tests/e2e_mcp_client.py    # MCP E2E (real DBs)
python tests/e2e_cli.py           # CLI E2E (real DBs)
make lint                         # ruff check + format
```

---

## Docs

- [System Architecture](docs/architecture/system.md)
- [Search Architecture](docs/architecture/search.md)
- [Save Architecture](docs/architecture/save.md)

---

## License

MIT
