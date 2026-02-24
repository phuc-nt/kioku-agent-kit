"""Kioku MCP Server — Thin MCP wrapper delegating to KiokuService."""

from __future__ import annotations

try:
    from fastmcp import FastMCP
except ImportError:
    raise ImportError(
        "FastMCP is required to run the MCP server. Install it with: pip install kioku-mcp[mcp]"
    )

from kioku.service import KiokuService

# Initialize service (single source of truth for all business logic)
_svc = KiokuService()

# Create MCP server
mcp = FastMCP(
    "Kioku",
    instructions="Personal memory agent — save and search your life memories with tri-hybrid search.",
)


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
    return _svc.save_memory(text, mood=mood, tags=tags)


@mcp.tool()
def search_memories(
    query: str,
    limit: int = 10,
    date_from: str | None = None,
    date_to: str | None = None,
    entities: list[str] | None = None,
) -> dict:
    """Search through all saved memories using tri-hybrid search (BM25 + Vector + KG).

    Combines keyword matching, semantic similarity, and knowledge graph traversal
    using RRF reranking for comprehensive results.

    Args:
        query: What to search for. Can be a question or keywords.
        limit: Maximum number of results to return (default 10).
        date_from: Optional start date filter (YYYY-MM-DD).
        date_to: Optional end date filter (YYYY-MM-DD).
        entities: Optional list of entity names to focus KG search on.
                  If the user's question mentions specific people, places, or topics,
                  extract and pass them here for more precise KG results.
                  Example: ["Mẹ", "Hùng"] for "mẹ tôi và sếp Hùng ai khắt khe hơn?"
    """
    return _svc.search_memories(query, limit=limit, date_from=date_from, date_to=date_to, entities=entities)


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
    return _svc.recall_related(entity, max_hops=max_hops, limit=limit)


@mcp.tool()
def explain_connection(entity_a: str, entity_b: str) -> dict:
    """Explain how two entities are connected through the knowledge graph.

    Finds the shortest path between two people, places, events, or topics
    and shows the evidence that links them.

    Args:
        entity_a: First entity name.
        entity_b: Second entity name.
    """
    return _svc.explain_connection(entity_a, entity_b)


@mcp.tool()
def list_memory_dates() -> dict:
    """List all dates that have memory entries from SQLite Database."""
    return _svc.list_memory_dates()


@mcp.tool()
def get_timeline(
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 50,
    sort_by: str = "processing_time",
) -> dict:
    """Get a chronologically ordered sequence of memories from SQLite Database.

    Args:
        start_date: Start date (YYYY-MM-DD) inclusive.
        end_date: End date (YYYY-MM-DD) inclusive.
        limit: Max number of entries to return (default 50).
        sort_by: "processing_time" (default — when recorded) or "event_time" (when event actually happened).
    """
    return _svc.get_timeline(start_date=start_date, end_date=end_date, limit=limit, sort_by=sort_by)


# ─── Resources ─────────────────────────────────────────────────────────────


@mcp.resource("kioku://memories/{date}")
def read_memory_resource(date: str) -> str:
    """Read the raw markdown file containing all memories for a specific date."""
    return _svc.read_memory_resource(date)


@mcp.resource("kioku://entities/{entity}")
def read_entity_resource(entity: str) -> str:
    """Read a comprehensive profile of an entity based on the knowledge graph."""
    return _svc.read_entity_resource(entity)


# ─── Prompts ─────────────────────────────────────────────────────────────


@mcp.prompt()
def reflect_on_day() -> str:
    """A prompt template for doing an end-of-day reflection."""
    return _svc.reflect_on_day()


@mcp.prompt()
def analyze_relationships(entity_name: str) -> str:
    """A prompt template to deeply analyze a person or topic based on graph connections."""
    return _svc.analyze_relationships(entity_name)


@mcp.prompt()
def weekly_review() -> str:
    """A prompt template to do a weekly memory retrospective."""
    return _svc.weekly_review()


# ─── Main ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
