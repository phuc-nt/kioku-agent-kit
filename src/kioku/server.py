"""Kioku MCP Server — Entry point."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone, timedelta

from fastmcp import FastMCP

from kioku.config import settings
from kioku.storage.markdown import save_entry, read_entries, list_dates
from kioku.pipeline.keyword_writer import KeywordIndex
from kioku.pipeline.embedder import OllamaEmbedder, FakeEmbedder
from kioku.pipeline.vector_writer import VectorStore
from kioku.search.bm25 import bm25_search
from kioku.search.semantic import vector_search
from kioku.search.reranker import rrf_rerank

log = logging.getLogger(__name__)

# Initialize
settings.ensure_dirs()
keyword_index = KeywordIndex(settings.sqlite_path)

# Vector store — try Ollama, fallback to FakeEmbedder
try:
    embedder = OllamaEmbedder(host=settings.ollama_host, model=settings.ollama_model)
    embedder.embed("test")  # Test connection
    log.info("Using Ollama embedder (%s)", settings.ollama_model)
except Exception:
    log.warning("Ollama not available, using FakeEmbedder (no semantic search quality)")
    embedder = FakeEmbedder()

vector_store = VectorStore(embedder=embedder)

# Create MCP server
mcp = FastMCP(
    "Kioku",
    instructions="Personal memory agent — save and search your life memories with tri-hybrid search.",
)

JST = timezone(timedelta(hours=7))


# ─── Tools ───────────────────────────────────────────────────────────────


@mcp.tool()
def save_memory(
    text: str,
    mood: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    """Save a memory entry. Stores text to markdown (source of truth) and indexes for search.

    Args:
        text: The memory text to save. Can be anything — thoughts, events, feelings, links.
        mood: Optional mood tag (e.g., "happy", "stressed", "neutral").
        tags: Optional list of tags for categorization.
    """
    # 1. Save to markdown (source of truth)
    entry = save_entry(settings.memory_dir, text, mood=mood, tags=tags)

    # 2. Index in SQLite FTS5 (keyword search)
    date = datetime.now(JST).strftime("%Y-%m-%d")
    content_hash = hashlib.sha256(text.encode()).hexdigest()
    keyword_index.index(
        content=text,
        date=date,
        timestamp=entry.timestamp,
        mood=mood or "",
        content_hash=content_hash,
    )

    # 3. Index in ChromaDB (vector search)
    try:
        vector_store.add(
            content=text,
            date=date,
            timestamp=entry.timestamp,
            mood=mood or "",
            tags=tags,
        )
    except Exception as e:
        log.warning("Vector indexing failed: %s", e)

    # Phase 3: extract entities + write to FalkorDB

    return {
        "status": "saved",
        "timestamp": entry.timestamp,
        "date": date,
        "mood": mood,
        "tags": tags,
        "indexed": True,
    }


@mcp.tool()
def search_memories(
    query: str,
    limit: int = 10,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """Search through all saved memories using hybrid BM25 + semantic vector search.

    Combines keyword matching (exact terms) with semantic similarity (meaning)
    using RRF reranking for best results.

    Args:
        query: What to search for. Can be a question or keywords.
        limit: Maximum number of results to return (default 10).
        date_from: Optional start date filter (YYYY-MM-DD).
        date_to: Optional end date filter (YYYY-MM-DD).
    """
    # BM25 keyword search
    bm25_results = bm25_search(keyword_index, query, limit=limit * 3)

    # Semantic vector search
    vec_results = vector_search(vector_store, query, limit=limit * 3)

    # Phase 3: add graph_results

    # RRF rerank — fuse BM25 + Vector
    results = rrf_rerank(bm25_results, vec_results, limit=limit)

    # Apply date filters if provided
    if date_from or date_to:
        filtered = []
        for r in results:
            if date_from and r.date < date_from:
                continue
            if date_to and r.date > date_to:
                continue
            filtered.append(r)
        results = filtered

    return {
        "query": query,
        "count": len(results),
        "results": [
            {
                "content": r.content,
                "date": r.date,
                "mood": r.mood,
                "score": round(r.score, 4),
                "source": r.source,
            }
            for r in results
        ],
    }


@mcp.tool()
def get_memories_by_date(date: str | None = None) -> dict:
    """Read all memory entries for a specific date.

    Args:
        date: Date in YYYY-MM-DD format. If not provided, returns today's entries.
    """
    entries = read_entries(settings.memory_dir, date=date)
    if date is None:
        date = datetime.now(JST).strftime("%Y-%m-%d")

    return {
        "date": date,
        "count": len(entries),
        "entries": [
            {
                "text": e.text,
                "timestamp": e.timestamp,
                "mood": e.mood,
                "tags": e.tags,
            }
            for e in entries
        ],
    }


@mcp.tool()
def list_memory_dates() -> dict:
    """List all dates that have memory entries."""
    dates = list_dates(settings.memory_dir)
    return {
        "count": len(dates),
        "dates": dates,
    }


# ─── Main ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
