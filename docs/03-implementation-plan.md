# Kioku MCP Server — Implementation Plan

## Project Structure

```
kioku-agent-kit/
├── docs/                           # Documentation (you are here)
├── docker-compose.yml              # FalkorDB + ChromaDB + Ollama + MCP server
├── Dockerfile                      # MCP server image
├── pyproject.toml                  # Python dependencies
├── .env.example                    # Environment variables template
│
├── src/kioku/
│   ├── __init__.py
│   ├── server.py                   # FastMCP entry point
│   ├── config.py                   # Settings, paths, DB connections
│   │
│   ├── tools/                      # MCP Tool handlers
│   │   ├── save.py                 # save_memory
│   │   ├── search.py               # search_memories (tri-hybrid)
│   │   ├── recall.py               # recall_related, explain_connection
│   │   ├── timeline.py             # get_timeline
│   │   └── patterns.py             # get_life_patterns
│   │
│   ├── resources/                  # MCP Resource handlers
│   │   └── memories.py             # kioku://memories/*, kioku://entities/*
│   │
│   ├── prompts/                    # MCP Prompt templates
│   │   └── templates.py
│   │
│   ├── pipeline/                   # Ingestion pipeline
│   │   ├── extractor.py            # LLM entity/relationship extraction
│   │   ├── embedder.py             # Ollama embedding
│   │   ├── graph_writer.py         # FalkorDB upsert (via Graphiti or raw Cypher)
│   │   ├── vector_writer.py        # ChromaDB upsert
│   │   └── keyword_writer.py       # SQLite FTS5 insert
│   │
│   ├── search/                     # Search engines
│   │   ├── bm25.py                 # SQLite FTS5 search
│   │   ├── semantic.py             # ChromaDB vector search
│   │   ├── graph.py                # FalkorDB traversal
│   │   └── reranker.py             # RRF fusion
│   │
│   └── storage/
│       └── markdown.py             # Read/write memory/*.md
│
└── tests/
    ├── test_pipeline.py
    ├── test_search.py
    └── test_tools.py
```

## Phased Implementation

### Phase 1 — Foundation (Skeleton + Save + Keyword Search)
> Mục tiêu: MCP server chạy được, save memory, tìm bằng keyword

**Tasks:**
1. Setup project: `pyproject.toml`, Dockerfile, docker-compose (FalkorDB + ChromaDB)
2. Implement `server.py` với FastMCP — register 1 tool `save_memory`
3. Implement `storage/markdown.py` — append entry vào `memory/{date}.md`
4. Implement `pipeline/keyword_writer.py` — SQLite FTS5 indexing
5. Implement `search/bm25.py` — keyword search
6. Implement tool `search_memories` (chỉ BM25 trước)
7. Test: save → search bằng keyword → verify kết quả

**Deliverable:** MCP server chạy qua stdio, save + keyword search hoạt động.

---

### Phase 2 — Vector Search (Semantic)
> Mục tiêu: Thêm semantic search, tìm theo ý nghĩa

**Tasks:**
1. Setup Ollama container (hoặc dùng Ollama trên host) + pull `nomic-embed-text`
2. Implement `pipeline/embedder.py` — gọi Ollama embed
3. Implement `pipeline/vector_writer.py` — ChromaDB upsert với metadata
4. Implement `search/semantic.py` — ChromaDB query
5. Implement `search/reranker.py` — RRF fusion (BM25 + Vector)
6. Update `search_memories` tool: hybrid 2 nguồn
7. Test: search câu đồng nghĩa → verify semantic match

**Deliverable:** Search bằng ý nghĩa hoạt động, RRF fusion BM25 + Vector.

---

### Phase 3 — Knowledge Graph (Entity Extraction + Graph Search)
> Mục tiêu: Extract entities, build graph, graph traversal search

**Tasks:**
1. Implement `pipeline/extractor.py` — gọi Claude Haiku extract entities + relationships
2. Implement `pipeline/graph_writer.py` — FalkorDB upsert nodes + edges
3. Implement `search/graph.py` — multi-hop traversal từ entity
4. Update `search/reranker.py` — RRF 3 nguồn (BM25 + Vector + Graph)
5. Implement tools: `recall_related`, `explain_connection`
6. Test: save nhiều entries → query graph → verify relationship chains

**Deliverable:** Full tri-hybrid search. Graph traversal hoạt động.

---

### Phase 4 — Resources, Prompts & Polish (DONE)
> Mục tiêu: Hoàn thiện MCP interface, thêm resources và prompts

**Tasks:**
1. Implement MCP Resources: `kioku://memories/{date}`, `kioku://entities/{type}`
2. Implement MCP Prompts: `reflect_on_day`, `weekly_review`, `find_why`
3. Implement tools: `get_timeline`, `get_life_patterns`
4. Error handling, logging, graceful degradation
5. Viết README.md với setup guide

**Deliverable:** MCP server feature-complete, sẵn sàng integrate vào OpenClaw.

---

### Phase 5 — OpenClaw Integration
> Mục tiêu: Gắn Kioku vào OpenClaw ecosystem

**Tasks:**
1. Tạo agent `kioku` trong OpenClaw (`openclaw.json`)
2. Cấu hình MCP server trong OpenClaw config
3. Viết `SOUL.md` cho Kioku agent (persona: người bạn lắng nghe)
4. Bind Kioku agent với một Telegram bot
5. Test end-to-end: Chat Telegram → Save → Search → Reply

**Deliverable:** Kioku hoạt động như một OpenClaw agent qua Telegram.

---

## Dependencies

```toml
[project]
dependencies = [
    "fastmcp>=2.0",
    "anthropic>=0.40",
    "chromadb>=0.6",
    "falkordb>=1.0",
    "ollama>=0.4",
    "pydantic>=2.0",
]
```

## Docker Compose

```yaml
services:
  falkordb:
    image: falkordb/falkordb:latest
    ports: ["6379:6379"]
    volumes: ["falkordb_data:/data"]

  chromadb:
    image: chromadb/chroma:latest
    ports: ["8000:8000"]
    volumes: ["chroma_data:/chroma/chroma"]

  ollama:
    image: ollama/ollama:latest
    ports: ["11434:11434"]
    volumes: ["ollama_data:/root/.ollama"]

volumes:
  falkordb_data:
  chroma_data:
  ollama_data:
```

MCP server chạy trên host (không Docker) để dùng stdio transport với OpenClaw.
Hoặc chạy trong Docker nhưng mount stdio qua wrapper script.

## Milestones

| Phase | Estimate | Depends on |
|---|---|---|
| Phase 1 | 2-3 ngày | — |
| Phase 2 | 2 ngày | Phase 1 |
| Phase 3 | 3-4 ngày | Phase 2 |
| Phase 4 | 2 ngày | Phase 3 |
| Phase 5 | 1 ngày | Phase 4 |
| **Tổng** | **~10-12 ngày** | |
