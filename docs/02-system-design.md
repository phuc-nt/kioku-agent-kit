# Kioku MCP Server — System Design & Tech Stack

## Architecture Overview

```
MCP Clients (OpenClaw / Claude Desktop / Cursor)
        │
        │  JSON-RPC 2.0 (stdio)
        ▼
┌─────────────────────────────────┐
│     Kioku MCP Server            │
│     (Python + FastMCP)          │
│                                 │
│  Tools ← search/save/recall     │
│  Resources ← memories/entities  │
│  Prompts ← reflect/review       │
│                                 │
│  ┌─────────────────────────┐    │
│  │   Processing Pipeline   │    │
│  │                         │    │
│  │  Text → Markdown save   │    │
│  │       → LLM extract     │    │
│  │       → Embed + Index   │    │
│  │       → Graph upsert    │    │
│  └─────────────────────────┘    │
│                                 │
│  ┌─────────────────────────┐    │
│  │   Tri-Hybrid Retrieval  │    │
│  │                         │    │
│  │  BM25 (SQLite FTS5)     │    │
│  │  + Semantic (ChromaDB)  │    │
│  │  + Graph (FalkorDB)     │    │
│  │  → RRF Reranker         │    │
│  └─────────────────────────┘    │
└────────┬──────────┬─────────────┘
         │          │
    ┌────▼───┐ ┌────▼─────┐
    │ChromaDB│ │ FalkorDB │
    │(Docker)│ │ (Docker) │
    └────────┘ └──────────┘

SQLite FTS5: file trong MCP server container
Markdown files: mount từ host filesystem
```

## Tech Stack

| Layer | Technology | Deployment |
|---|---|---|
| MCP Server | Python 3.12 + FastMCP | Docker container |
| Graph DB | FalkorDB 4.x | Docker container |
| Vector DB | ChromaDB (server mode) | Docker container |
| Keyword Index | SQLite FTS5 | File trong MCP container |
| Embedding | Ollama (`nomic-embed-text`) | Docker container (hoặc host) |
| Entity Extraction | Claude Haiku 4.5 (API) | Remote API call |
| Source of Truth | Markdown files | Host filesystem, mount vào container |

## Data Model

### Markdown (Source of Truth)
```
~/.kioku/memory/
├── 2026-02-22.md     # Raw entries, append-only
├── 2026-02-23.md
└── ...
```

Mỗi entry trong file:
```markdown
---
time: "2026-02-22T15:30:00+07:00"
mood: "stressed"
---
Hôm nay họp với sếp Hùng về dự án X. Bị chê tiến độ chậm.
Tối về ăn phở với Linh, cảm thấy đỡ hơn.
```

### Knowledge Graph (FalkorDB)
```
Entity Node:
  - id, name, type (PERSON|PLACE|EVENT|EMOTION|TOPIC)
  - first_seen, last_seen
  - mention_count

Relationship Edge:
  - from_entity → to_entity
  - type (CAUSAL|EMOTIONAL|TEMPORAL|TOPICAL|INVOLVES)
  - weight (0.0-1.0)
  - evidence (text trích dẫn)
  - event_time, created_at
```

### Vector Store (ChromaDB)
```
Collection: "memories"
  - id: chunk hash (SHA-256)
  - embedding: vector from Ollama
  - document: chunk text
  - metadata: {date, mood, entities[], source_file}
```

### Keyword Index (SQLite FTS5)
```sql
CREATE VIRTUAL TABLE memory_fts USING fts5(
  content,
  date,
  mood,
  entities
);
```

## MCP Interface

### Tools
| Tool | Mô tả | Params |
|---|---|---|
| `save_memory` | Lưu ký ức mới | `text`, `mood?`, `tags?` |
| `search_memories` | Tri-hybrid search | `query`, `limit?`, `date_from?`, `date_to?` |
| `get_timeline` | Xem sự kiện theo timeline | `start_date`, `end_date`, `limit?` |
| `list_memory_dates` | Liệt kê các ngày có nhật ký | |
| `recall_related` | Graph traversal từ entity | `entity`, `max_hops?`, `limit?` |
| `explain_connection` | Giải thích liên kết A↔B | `entity_a`, `entity_b` |

### Resources
| URI | Mô tả |
|---|---|
| `kioku://memories/today` | Nhật ký hôm nay |
| `kioku://memories/{date}` | Nhật ký theo ngày |
| `kioku://entities/{type}` | Entities theo loại |
| `kioku://stats/summary` | Thống kê tổng quan |

### Prompts
| Prompt | Mô tả |
|---|---|
| `reflect_on_day` | Hồi tưởng cuối ngày |
| `weekly_review` | Tổng kết tuần |
| `find_why` | Truy tìm nguyên nhân cảm xúc |

## Tri-Hybrid Search Flow

```python
def search_memories(query, limit=10):
    # 1. Keyword (BM25)
    bm25_results = sqlite_fts5.search(query, top_k=30)

    # 2. Semantic (Vector)
    query_vector = ollama.embed(query)
    vector_results = chromadb.query(query_vector, top_k=30)

    # 3. Graph (Traversal)
    entities = llm.extract_entities(query)
    graph_results = falkordb.traverse(entities, max_hops=2)

    # 4. RRF Fusion
    fused = rrf_rerank(bm25_results, vector_results, graph_results)
    return fused[:limit]
```

## Docker Compose Services

```yaml
services:
  kioku-mcp:        # FastMCP server
  falkordb:          # Graph DB, port 6379
  chromadb:          # Vector DB, port 8000
  ollama:            # Embedding model (optional, có thể dùng host)
```
