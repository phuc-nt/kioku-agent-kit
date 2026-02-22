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
from kioku.pipeline.extractor import ClaudeExtractor, FakeExtractor
from kioku.pipeline.graph_writer import FalkorGraphStore, InMemoryGraphStore
from kioku.search.bm25 import bm25_search
from kioku.search.semantic import vector_search
from kioku.search.graph import graph_search
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

vector_store = VectorStore(
    embedder=embedder,
    host=settings.chroma_host,
    port=settings.chroma_port,
)

# Knowledge graph — try FalkorDB, fallback to InMemoryGraphStore
try:
    graph_store = FalkorGraphStore(
        host=settings.falkordb_host, port=settings.falkordb_port
    )
    # Test connection by accessing the graph property
    _ = graph_store.graph
    log.info("Using FalkorDB graph store")
except Exception:
    log.warning("FalkorDB not available, using InMemoryGraphStore")
    graph_store = InMemoryGraphStore()

# Entity extractor — try Claude, fallback to FakeExtractor
if settings.anthropic_api_key:
    extractor = ClaudeExtractor(api_key=settings.anthropic_api_key)
    log.info("Using Claude extractor for entity extraction")
else:
    log.warning("No Anthropic API key, using FakeExtractor (rule-based)")
    extractor = FakeExtractor()

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

    # 4. Extract entities + write to knowledge graph
    try:
        extraction = extractor.extract(text)
        if extraction.entities:
            graph_store.upsert(extraction, date=date, timestamp=entry.timestamp)
            log.info(
                "Extracted %d entities, %d relationships",
                len(extraction.entities),
                len(extraction.relationships),
            )
    except Exception as e:
        log.warning("Entity extraction/graph indexing failed: %s", e)

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
    """Search through all saved memories using tri-hybrid search (BM25 + Vector + KG).

    Combines keyword matching, semantic similarity, and knowledge graph traversal
    using RRF reranking for comprehensive results.

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

    # Knowledge graph search
    kg_results = graph_search(graph_store, query, limit=limit * 3)

    # RRF rerank — fuse all three sources
    results = rrf_rerank(bm25_results, vec_results, kg_results, limit=limit)

    # Apply date filters if provided
    if date_from or date_to:
        filtered = []
        for r in results:
            if date_from and r.date and r.date < date_from:
                continue
            if date_to and r.date and r.date > date_to:
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
def recall_related(entity: str, max_hops: int = 2, limit: int = 10) -> dict:
    """Recall everything related to a person, place, topic, or event.

    Traverses the knowledge graph to find connected entities and the evidence
    (memory text) that links them.

    Args:
        entity: The entity name to search for (e.g., "Hùng", "dự án X", "gym").
        max_hops: How many relationship hops to traverse (default 2).
        limit: Maximum number of connected entities to return.
    """
    result = graph_store.traverse(entity, max_hops=max_hops, limit=limit)

    return {
        "entity": entity,
        "connected_count": len(result.nodes),
        "nodes": [
            {
                "name": n.name,
                "type": n.type,
                "mention_count": n.mention_count,
                "first_seen": n.first_seen,
                "last_seen": n.last_seen,
            }
            for n in result.nodes
        ],
        "relationships": [
            {
                "source": e.source,
                "target": e.target,
                "type": e.rel_type,
                "weight": round(e.weight, 2),
                "evidence": e.evidence,
            }
            for e in result.edges
        ],
    }


@mcp.tool()
def explain_connection(entity_a: str, entity_b: str) -> dict:
    """Explain how two entities are connected through the knowledge graph.

    Finds the shortest path between two people, places, events, or topics
    and shows the evidence that links them.

    Args:
        entity_a: First entity name.
        entity_b: Second entity name.
    """
    result = graph_store.find_path(entity_a, entity_b)

    return {
        "from": entity_a,
        "to": entity_b,
        "connected": len(result.paths) > 0,
        "paths": result.paths,
        "nodes": [
            {"name": n.name, "type": n.type}
            for n in result.nodes
        ],
        "evidence": [
            {
                "source": e.source,
                "target": e.target,
                "type": e.rel_type,
                "evidence": e.evidence,
            }
            for e in result.edges
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


@mcp.tool()
def get_timeline(start_date: str | None = None, end_date: str | None = None, limit: int = 50) -> dict:
    """Get a chronologically ordered sequence of memories.

    Args:
        start_date: Start date (YYYY-MM-DD) inclusive.
        end_date: End date (YYYY-MM-DD) inclusive.
        limit: Max number of entries to return (default 50).
    """
    dates = list_dates(settings.memory_dir)
    if start_date:
        dates = [d for d in dates if d >= start_date]
    if end_date:
        dates = [d for d in dates if d <= end_date]

    # Read from most recent backward, or oldest forward? Timeline usually means chronological.
    # Let's read chronologically but limit to recent (so we slice at the end).
    all_entries = []
    # Read backward to easily apply limit to most recent ones inside that range
    for d in reversed(dates):
        entries = read_entries(settings.memory_dir, date=d)
        for e in reversed(entries):
            all_entries.append({
                "date": d,
                "timestamp": e.timestamp,
                "mood": e.mood,
                "tags": e.tags,
                "text": e.text
            })
            if len(all_entries) >= limit:
                break
        if len(all_entries) >= limit:
            break

    # Reverse back to chronological
    all_entries.reverse()

    return {
        "count": len(all_entries),
        "timeline": all_entries
    }


@mcp.tool()
def get_life_patterns(days_back: int = 30) -> dict:
    """Analyze memory entries over recent days to find patterns in mood and tags.
    
    Args:
        days_back: Number of days to look back for pattern extraction.
    """
    dates = list_dates(settings.memory_dir)[-days_back:]
    
    mood_counts = {}
    tag_counts = {}
    total_entries = 0
    
    for d in dates:
        entries = read_entries(settings.memory_dir, date=d)
        for e in entries:
            total_entries += 1
            if e.mood:
                mood_counts[e.mood] = mood_counts.get(e.mood, 0) + 1
            if e.tags:
                for t in e.tags:
                    tag_counts[t] = tag_counts.get(t, 0) + 1
                    
    # Sort by frequency
    sorted_moods = sorted(mood_counts.items(), key=lambda x: x[1], reverse=True)
    sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
    
    return {
        "analyzed_days": len(dates),
        "total_entries": total_entries,
        "frequent_moods": [{"mood": m, "count": c} for m, c in sorted_moods[:5]],
        "frequent_topics": [{"tag": t, "count": c} for t, c in sorted_tags[:10]]
    }


# ─── Resources ─────────────────────────────────────────────────────────────

@mcp.resource("kioku://memories/{date}")
def read_memory_resource(date: str) -> str:
    """Read the raw markdown file containing all memories for a specific date."""
    filepath = settings.memory_dir / f"{date}.md"
    if not filepath.exists():
        return f"No memories found for date {date}."
    return filepath.read_text()


@mcp.resource("kioku://entities/{entity}")
def read_entity_resource(entity: str) -> str:
    """Read a comprehensive profile of an entity based on the knowledge graph."""
    result = graph_store.traverse(entity, max_hops=2, limit=50)
    
    if not result.nodes:
        return f"Entity '{entity}' not found in the knowledge graph."
        
    # Get the root node
    root_node = next((n for n in result.nodes if n.name.lower() == entity.lower()), result.nodes[0])
    
    out = [
        f"# Entity Profile: {root_node.name} ({root_node.type})",
        f"- **First mentioned:** {root_node.first_seen}",
        f"- **Last mentioned:** {root_node.last_seen}",
        f"- **Total mentions:** {root_node.mention_count}",
        "",
        "## Known Relationships",
    ]
    
    if not result.edges:
        out.append("No known relationships.")
    else:
        for e in result.edges:
            # Emphasize the connection based on weight
            strength = "Strongly" if e.weight >= 0.8 else "Moderately" if e.weight >= 0.5 else "Weakly"
            out.append(f"- **{strength} {e.rel_type.lower()}** to `{e.target}`")
            if e.evidence:
                out.append(f"  > *\"{e.evidence}\"*")
                
    out.append("")
    out.append("These details are generated from traversing the knowledge graph memory.")
    return "\n".join(out)


# ─── Prompts ─────────────────────────────────────────────────────────────

@mcp.prompt()
def reflect_on_day() -> str:
    """A prompt template for doing an end-of-day reflection."""
    today = datetime.now(JST).strftime("%Y-%m-%d")
    return f"""Please review my memory entries for today ({today}) by reading the kioku://memories/{today} resource. 
Then, provide a thoughtful end-of-day reflection that covers:
1. The overall emotional tone of my day.
2. The key events and entities I interacted with.
3. A positive takeaway or lesson for tomorrow.

Respond as a compassionate companion (my 'Kioku')."""


@mcp.prompt()
def analyze_relationships(entity_name: str) -> str:
    """A prompt template to deeply analyze a person or topic based on graph connections."""
    return f"""Please use the kioku://entities/{entity_name} resource to read about '{entity_name}'.
    
Analyze this entity's role in my life based on the knowledge graph:
1. What is my primary emotional response surrounding this entity?
2. Who or what else is frequently connected to this entity?
3. What are some notable patterns in my memories involving {entity_name}?

Write the analysis in a helpful, introspective tone."""


@mcp.prompt()
def weekly_review() -> str:
    """A prompt template to do a weekly memory retrospective."""
    today = datetime.now(JST)
    days = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    dates_list = ", ".join(days)
    
    return f"""Please perform a weekly retrospective of my life over the past 7 days:
    
Dates to check (using tools to read memory dates if resources aren't mapped):
{dates_list}

Please synthesize:
- The highs and lows of the week based on 'mood' and events.
- An overview of who I spent the most time with or thought about often.
- Recommended focus areas for next week based on lingering tasks or stress points mentioned."""


# ─── Main ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
