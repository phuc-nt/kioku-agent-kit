# System Architecture — Kioku Overview

> Last updated: 2026-02-26 (v0.2.10)

## Overview

Kioku (記憶) is a personal memory agent that stores and retrieves memories using a tri-hybrid search engine. It serves as the memory backend for AI agents (via CLI) and for direct use (via MCP server).

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        INTERFACE LAYER                          │
│                                                                 │
│  ┌─────────────────────┐    ┌──────────────────────────────┐   │
│  │  server.py (MCP)    │    │  cli.py (Typer CLI)          │   │
│  │  4 tools:           │    │  4 commands:                 │   │
│  │  • save_memory      │    │  • kioku save                │   │
│  │  • search_memories  │    │  • kioku search              │   │
│  │  • list_entities    │    │  • kioku entities            │   │
│  │  • get_timeline     │    │  • kioku timeline            │   │
│  │                     │    │                              │   │
│  │  2 resources:       │    │  Usage:                      │   │
│  │  • memories/{date}  │    │  OpenClaw Agent → CLI        │   │
│  │  • entities/{name}  │    │  via shell commands          │   │
│  │                     │    │                              │   │
│  │  3 prompts:         │    │                              │   │
│  │  • reflect_on_day   │    │                              │   │
│  │  • analyze_rels     │    │                              │   │
│  │  • weekly_review    │    │                              │   │
│  └────────┬────────────┘    └──────────────┬───────────────┘   │
│           └───────────────┬────────────────┘                    │
│                           ▼                                     │
│              ┌─────────────────────────┐                        │
│              │  service.py             │                        │
│              │  (KiokuService)         │                        │
│              │  Single source of truth │                        │
│              └────────────┬────────────┘                        │
│                           │                                     │
│           ┌───────────────┼───────────────┐                     │
│           ▼               ▼               ▼                     │
│  ┌────────────────┐ ┌──────────┐ ┌────────────────┐            │
│  │  WRITE PIPELINE│ │  SEARCH  │ │   STORAGE      │            │
│  │  pipeline/     │ │  search/ │ │   storage/     │            │
│  │                │ │          │ │                │            │
│  │  • extractor   │ │  • bm25  │ │  • markdown    │            │
│  │  • embedder    │ │  • sem.  │ │    (save_entry)│            │
│  │  • graph_writer│ │  • graph │ │                │            │
│  │  • vector_writ.│ │  • rerank│ │                │            │
│  │  • keyword_writ│ │          │ │                │            │
│  └────────┬───────┘ └────┬─────┘ └────────┬───────┘            │
│           │              │                │                     │
└───────────┼──────────────┼────────────────┼─────────────────────┘
            ▼              ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       DATA LAYER                                │
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ SQLite FTS5 │  │  ChromaDB    │  │  FalkorDB              │ │
│  │             │  │              │  │                        │ │
│  │ • BM25 kw   │  │ • Embeddings │  │ • Entity nodes         │ │
│  │ • Doc store │  │ • Vec search │  │ • Relationships        │ │
│  │ • Hydration │  │ • Metadata   │  │ • Graph traversal      │ │
│  │             │  │              │  │ • Shortest paths       │ │
│  │ kioku_fts.db│  │ :8001        │  │ :6381                  │ │
│  └─────────────┘  └──────────────┘  └────────────────────────┘ │
│                                                                 │
│  ┌─────────────────────────────────────┐  ┌──────────────────┐ │
│  │ Markdown Files (Source of Truth)    │  │ Ollama (Embed)   │ │
│  │ ~/.kioku/users/{id}/memory/*.md     │  │ bge-m3 (1024d)   │ │
│  └─────────────────────────────────────┘  │ :11435 (Docker)  │ │
│                                           └──────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow: Save

```
Text → LLM Extract → Write 4 stores simultaneously
```

See [Save Architecture](save.md) for details.

| Step | Component | Output |
|---|---|---|
| 1 | SHA256 | content_hash (universal key) |
| 2 | Claude Haiku | entities, relationships, event_time |
| 3a | FalkorDB | Graph nodes + edges |
| 3b | Markdown | YYYY-MM-DD.md entry |
| 3c | SQLite FTS5 | Indexed document |
| 3d | ChromaDB | Embedded vector |

## Data Flow: Search

```
Query → Agent Enrichment → Auto-Extract → Tri-Hybrid Search → RRF → Hydrate → Enrich
```

See [Search Architecture](search.md) for details.

| Step | Component | Output |
|---|---|---|
| 1 | Agent (LLM) | Enriched query (pronouns → names) |
| 2 | Claude Haiku | Auto-extracted entity list |
| 3a | SQLite FTS5 | BM25 results (~60%) |
| 3b | ChromaDB | Vector results (~16%) |
| 3c | FalkorDB | Graph results (~24%) |
| 4 | RRF Reranker | Fused top-N results |
| 5 | SQLite | Hydrated text (consistent) |
| 6 | FalkorDB | Graph context (nodes, evidence, paths) |

## Module Structure

```
src/kioku/
├── __init__.py
├── config.py          # Settings (Pydantic) — paths, ports, API keys
├── service.py         # KiokuService — all business logic
├── server.py          # MCP server (FastMCP) — 4 tools, 2 resources, 3 prompts
├── cli.py             # CLI (Typer) — 4 commands
│
├── pipeline/          # WRITE path (ingestion)
│   ├── extractor.py   # LLM entity extraction (Claude Haiku)
│   ├── embedder.py    # Embedding (Ollama nomic-embed-text)
│   ├── graph_writer.py # FalkorDB write (upsert entities + rels)
│   ├── vector_writer.py # ChromaDB write (embed + store)
│   └── keyword_writer.py # SQLite FTS5 write (index + store)
│
├── search/            # READ path (retrieval)
│   ├── bm25.py        # BM25 keyword search (SQLite FTS5)
│   ├── semantic.py    # Vector similarity search (ChromaDB)
│   ├── graph.py       # Graph traversal search (FalkorDB)
│   └── reranker.py    # RRF rank fusion (combine 3 legs)
│
└── storage/
    └── markdown.py    # Markdown file I/O (source of truth)
```

## Configuration

All settings via environment variables or `.env`:

| Variable | Default | Purpose |
|---|---|---|
| `KIOKU_USER_ID` | `default` | User isolation (multi-user) |
| `KIOKU_DATA_DIR` | `~/.kioku` | Root data directory |
| `KIOKU_ANTHROPIC_API_KEY` | — | Claude API for entity extraction |
| `KIOKU_CHROMA_HOST` | `localhost` | ChromaDB server |
| `KIOKU_CHROMA_PORT` | `8001` | ChromaDB port (Docker: kioku-chromadb) |
| `KIOKU_FALKORDB_HOST` | `localhost` | FalkorDB server |
| `KIOKU_FALKORDB_PORT` | `6381` | FalkorDB port (Docker: kioku-falkordb) |
| `KIOKU_OLLAMA_BASE_URL` | `http://localhost:11435` | Ollama for embeddings (Docker: kioku-ollama) |
| `KIOKU_OLLAMA_MODEL` | `bge-m3` | Embedding model (1024-dim) |

## Graceful Degradation

Kioku is designed to work with partial infrastructure:

| Config | Search Works? | What's Missing |
|---|---|---|
| SQLite only | ✅ BM25 | No semantic, no graph |
| + ChromaDB | ✅ BM25 + Vector | No graph |
| + FalkorDB | ✅ BM25 + Graph | No semantic |
| Full stack | ✅ BM25 + Vector + Graph | Nothing |

SQLite is the **only critical** dependency. All others fail gracefully.

## Multi-User Isolation

Each user gets isolated storage:

```
~/.kioku/users/
├── telegram/          # KIOKU_USER_ID=telegram
│   ├── kioku.db       # SQLite (private)
│   └── memory/        # Markdown files (private)
│       ├── 2026-02-24.md
│       └── ...
├── default/           # KIOKU_USER_ID=default
│   ├── kioku.db
│   └── memory/
└── ...
```

ChromaDB and FalkorDB collections are also namespaced: `memories_{user_id}` and `kioku_kg_{user_id}`.
