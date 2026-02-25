# Kioku Architecture Evaluation & Comparison

> Drafted: 2026-02-25 | Based on real test data and industry research

---

## 1. Overall Architecture Assessment

### Kioku vs GraphRAG Solutions Comparison

| Dimension | Microsoft GraphRAG | LightRAG | nano-graphrag | **Kioku** |
|---|---|---|---|---|
| **Approach** | Hierarchical communities (Leiden) | Entity-relationship pairs + embeddings | Minimal (~1100 LOC) graph RAG | Tri-hybrid RRF fusion |
| **Graph Construction** | LLM extraction | LLM extraction | LLM + DSPy | LLM extraction (Claude Haiku) |
| **Search Strategy** | Local + Global + DRIFT | Naive/Local/Global/Hybrid | Naive/Local/Global | BM25 + Vector + Graph → RRF |
| **Incremental Updates** | ❌ Full rebuild required | ✅ Supported | Partial | ✅ Per-entry insert |
| **Graph Store** | NetworkX (in-memory) | Custom / various | Faiss + Neo4j | FalkorDB |
| **Vector Store** | Internal | Integrated | Faiss / custom | ChromaDB |
| **Multi-hop Reasoning** | ✅ Strong (community summaries) | Medium | Medium | ✅ 2-hop + shortest paths |
| **Indexing Cost** | 💰💰💰 Very high | 💰 Low | 💰 Low | 💰 Low (per-entry) |
| **Query Cost** | 💰💰 High (LLM for global) | 💰 Low | 💰 Low | 💰💰 Medium (auto-extract LLM) |
| **Lines of Code** | ~10,000+ | ~5,000 | ~1,100 | ~2,500 |
| **Target Use Case** | Enterprise analysis | General RAG | Hackable prototype | Personal memory agent |

### Kioku's Unique Strengths

1. **RRF Tri-Hybrid Fusion** — Unlike others that route to different search modes (Local vs Global), Kioku FUSES all three legs (BM25 + Vector + Graph) every query. This is more robust for personal memory where queries are unpredictable.

2. **Per-entry Incremental Insert** — Save a memory → instantly searchable. No batch rebuild needed. Most Graph RAG solutions (Microsoft) require full re-indexing.

3. **Auto-Extract on Both Sides** — Kioku extracts entities on save AND on search, using the same canonical vocabulary. This creates a consistent entity namespace.

4. **Content Hash Linking** — Universal dedup key across all stores. Graph edge evidence → hydrate from SQLite. This is simpler and more reliable than Microsoft's community-based approach.

5. **Budget System** — Explicit 20-entry heavyweight cap prevents context overflow. Most solutions don't have response budget management.

### Kioku's Weaknesses

1. **No Community Detection** — Microsoft GraphRAG's Leiden communities enable global summarization ("What are the main themes?"). Kioku can't answer corpus-level questions.

2. **Single-hop Dominant** — While Kioku does 2-hop traversal, it doesn't do deep multi-hop reasoning. For "How is A indirectly connected to C through B, D, E?", Microsoft GraphRAG excels.

3. **No Query Routing** — LightRAG has Naive/Local/Global/Hybrid modes. Kioku always runs all 3 legs, which is thorough but not efficient for simple queries.

4. **Auto-Extract Adds Latency** — ~3s per search for LLM extraction. LightRAG/nano-graphrag don't have this cost on the search side.

---

## 2. Component Evaluation

### 2.1 Entity Extraction: Claude Haiku 3 (claude-3-haiku-20240307)

**Current model:** `claude-3-haiku-20240307` (original Haiku)

| Benchmark | Claude Haiku 3 | Claude Haiku 4.5 | GPT-4o Mini |
|---|---|---|---|
| NER F1 (ProLLM) | ~0.79 | ~0.85 (est.) | 0.836 |
| Complex extraction | Good | Strong | Good |
| Latency | ~1.5s | ~1.2s | ~0.8s |
| Input cost / 1M tokens | $0.25 | $1.00 | $0.15 |
| Output cost / 1M tokens | $1.25 | $5.00 | $0.60 |

**⚠️ ISSUE: Kioku uses the OLD Haiku 3, not Haiku 4.5!**

**Recommendation:** 

| Option | Model | Benefit | Trade-off |
|---|---|---|---|
| 🏆 Best quality | `claude-haiku-4-5-20251001` | Better extraction, same format | ~4x cost increase |
| 💰 Best cost | `gpt-4o-mini` | Cheapest, fast | Slightly less nuanced |
| ⚖️ Balanced | `claude-haiku-4-5-20251001` | Best for Vietnamese text | Worth the cost for personal data |

**Verdict:** Upgrade to **Claude Haiku 4.5** is recommended. Vietnamese text extraction benefits from Claude's stronger multilingual handling. The cost increase (~4x) is negligible for personal use (~10-50 entries/day = <$0.01/day).

### 2.2 Embedding: Ollama nomic-embed-text (768d)

**Current model:** `nomic-embed-text` via Ollama (local)

| Model | Dims | MTEB Score | Multilingual | Local | Cost |
|---|---|---|---|---|---|
| **nomic-embed-text** | 768 | 62.4 | Weak | ✅ Ollama | Free |
| bge-m3 | 1024 | 72.0 | ✅ Strong | ✅ Ollama | Free |
| mxbai-embed-large | 1024 | 64.7 | Medium | ✅ Ollama | Free |
| text-embedding-3-large | 3072 | 64.6 | ✅ Strong | ❌ API | $0.13/1M |
| voyage-3-large | 1024 | ~68 | ✅ Strong | ❌ API | $0.06/1M |
| Qwen3-Embedding-8B | 4096 | 70.6 | ✅ Best | ❌ API/vLLM | Free/GPU |

**⚠️ ISSUE: nomic-embed-text is weak for Vietnamese!**

For a Vietnamese personal diary system, multilingual embedding is critical. nomic-embed-text was primarily trained on English text.

**Recommendation:**

| Option | Model | Benefit | How to use |
|---|---|---|---|
| 🏆 Best for Vietnamese | `bge-m3` | 72% MTEB, tri-modal (dense+sparse+multi-vec), strong multilingual | `ollama pull bge-m3` — drop-in replacement |
| ⚖️ Good balance | `mxbai-embed-large` | Higher accuracy than nomic, Ollama-native | `ollama pull mxbai-embed-large` |
| 💎 Premium | `voyage-3-large` | Best commercial, multilingual | API only |

**Verdict:** Switch to **bge-m3** via Ollama. It's a drop-in replacement (just change model name), free, local, and significantly better for Vietnamese + multilingual content. Expected vector search contribution to jump from 16% to ~30%+.

### 2.3 Vector Store: ChromaDB

| Database | Scalability | Latency | Hybrid Search | Maturity | Best For |
|---|---|---|---|---|---|
| **ChromaDB** | <1M vectors | Medium | ❌ No | Growing | Prototyping |
| Qdrant | 1M-100M | Very low | ❌ No | Production | Performance |
| Weaviate | 1M-100M | Medium | ✅ BM25+Vector | Mature | Hybrid search |
| Milvus | >100M | Low | ✅ Yes | Enterprise | Massive scale |

**Assessment:** ChromaDB is appropriate for Kioku's scale (~1000-10000 entries). Personal diary doesn't need enterprise vector DB. ChromaDB's simplicity and Python-first API is the right choice.

**Verdict:** ✅ **ChromaDB is fine for personal use.** If scaling to multi-user SaaS, consider Qdrant.

### 2.4 Graph Store: FalkorDB

| Database | Latency | GraphRAG Focus | Multi-tenancy | Community |
|---|---|---|---|---|
| **FalkorDB** | Ultra-low | ✅ Dedicated SDK | ✅ Multi-graph | Growing |
| Neo4j | Medium | ✅ Strong ecosystem | Via labels | Mature |
| Memgraph | Low | Growing | Via labels | Growing |

**Assessment:** FalkorDB is an excellent choice for Kioku:
- Ultra-low latency for traversals (GraphBLAS engine)
- Native multi-graph for user isolation (`kioku_{user_id}`)
- Designed specifically for AI/RAG workloads
- Redis-compatible protocol, simple deployment

**Verdict:** ✅ **FalkorDB is the optimal choice.** Better than Neo4j for this use case (lower latency, less overhead).

### 2.5 Keyword Index: SQLite FTS5

**Assessment:** Perfect for the use case. Zero deployment, embedded, fast BM25, and serves as primary document store for hydration. No alternatives needed.

**Verdict:** ✅ **Optimal.**

---

## 3. Model Optimization Roadmap

### Priority 1: Upgrade Embedding Model (HIGH IMPACT, LOW EFFORT)

```diff
- Current: nomic-embed-text (768d, English-focused)
+ Target:  bge-m3 (1024d, multilingual, 72% MTEB)
```

**Expected impact:** Vector search contribution 16% → ~30%+ (especially for Vietnamese queries)  
**Effort:** Change 1 config value + re-embed existing memories  
**Cost:** Free (Ollama)

### Priority 2: Upgrade Extraction Model (MEDIUM IMPACT, LOW EFFORT)

```diff
- Current: claude-3-haiku-20240307 (old Haiku 3)
+ Target:  claude-haiku-4-5-20251001 (Haiku 4.5)
```

**Expected impact:** Better entity extraction, relationship quality, event_time parsing  
**Effort:** Change 1 config value  
**Cost:** ~4x increase but still negligible ($0.01/day for personal use)

### Priority 3: Add Query Routing (MEDIUM IMPACT, MEDIUM EFFORT)

For simple queries ("Mẹ tôi tên gì?"), running all 3 search legs + auto-extract is overkill. Consider:
- Classify query complexity before search
- Simple → BM25 only (fast)
- Complex → full tri-hybrid (thorough)

**Expected impact:** Reduce latency from ~25s to ~8s for simple queries  
**Effort:** Add query classifier (could be rule-based)

### Priority 4: Cache Canonical Entities (LOW IMPACT, LOW EFFORT)

Auto-extract calls `get_canonical_entities(limit=50)` every search. Cache this for 5 minutes.

**Expected impact:** Save ~200ms per search  
**Effort:** Add simple TTL cache

---

## 4. Summary Scorecard

| Component | Current Choice | Rating | Action |
|---|---|---|---|
| **Architecture** (Tri-hybrid RRF) | Custom | ⭐⭐⭐⭐ | Good for personal memory |
| **Graph DB** (FalkorDB) | FalkorDB | ⭐⭐⭐⭐⭐ | Optimal |
| **Vector DB** (ChromaDB) | ChromaDB | ⭐⭐⭐⭐ | Fine for scale |
| **Keyword Index** (SQLite FTS5) | SQLite | ⭐⭐⭐⭐⭐ | Optimal |
| **Embedding** (nomic-embed-text) | nomic-embed-text | ⭐⭐ | **UPGRADE to bge-m3** 🔴 |
| **Extraction** (Claude Haiku 3) | claude-3-haiku | ⭐⭐⭐ | **UPGRADE to Haiku 4.5** 🟡 |
| **RRF Reranking** | Custom | ⭐⭐⭐⭐ | Good |
| **Auto-Extract** | Custom | ⭐⭐⭐⭐ | Novel approach |
| **Query Enrichment** | Agent-level | ⭐⭐⭐⭐ | Good |
| **Budget System** | Custom | ⭐⭐⭐⭐ | Good |

**Overall:** Kioku's architecture is solid and well-suited for personal memory. The two critical upgrades are the **embedding model** (bge-m3) and **extraction model** (Haiku 4.5), both of which are low-effort, high-impact changes.
