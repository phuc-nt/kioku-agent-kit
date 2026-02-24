"""Kioku CLI — Command-line interface for Kioku memory agent."""

from __future__ import annotations

import json
from typing import Optional

try:
    import typer
except ImportError:
    raise ImportError(
        "Typer is required to run the CLI. Install it with: pip install kioku-mcp[cli]"
    )

app = typer.Typer(
    name="kioku",
    help="Personal memory agent — save and search your life memories with tri-hybrid search.",
    no_args_is_help=True,
)

# Lazy-initialized service instance
_svc = None


def _get_svc():
    """Lazy-init KiokuService to avoid slow startup when just showing --help."""
    global _svc
    if _svc is None:
        from kioku.service import KiokuService

        _svc = KiokuService()
    return _svc


def _output(data: dict | str) -> None:
    """Print JSON output to stdout (ensure_ascii=False for Vietnamese)."""
    if isinstance(data, str):
        typer.echo(data)
    else:
        typer.echo(json.dumps(data, ensure_ascii=False, indent=2))


@app.command()
def save(
    text: str = typer.Argument(..., help="The memory text to save."),
    mood: Optional[str] = typer.Option(
        None, "--mood", "-m", help="Mood tag (e.g., happy, stressed)."
    ),
    tags: Optional[str] = typer.Option(
        None, "--tags", "-t", help="Comma-separated tags (e.g., work,meeting)."
    ),
) -> None:
    """Save a memory entry. Stores text to markdown and indexes for search."""
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    result = _get_svc().save_memory(text, mood=mood, tags=tag_list)
    _output(result)


@app.command()
def search(
    query: str = typer.Argument(..., help="What to search for."),
    limit: int = typer.Option(10, "--limit", "-l", help="Max results to return."),
    date_from: Optional[str] = typer.Option(None, "--from", help="Start date filter (YYYY-MM-DD)."),
    date_to: Optional[str] = typer.Option(None, "--to", help="End date filter (YYYY-MM-DD)."),
    entities: Optional[str] = typer.Option(None, "--entities", "-e", help="Comma-separated entity names for KG search (e.g. 'Mẹ,Hùng')."),
) -> None:
    """Search through all saved memories using tri-hybrid search (BM25 + Vector + KG)."""
    entity_list = [e.strip() for e in entities.split(",")] if entities else None
    result = _get_svc().search_memories(query, limit=limit, date_from=date_from, date_to=date_to, entities=entity_list)
    _output(result)


@app.command()
def recall(
    entity: str = typer.Argument(
        ..., help="Entity name to search for (e.g., person, place, topic)."
    ),
    max_hops: int = typer.Option(2, "--hops", "-h", help="Relationship hops to traverse."),
    limit: int = typer.Option(10, "--limit", "-l", help="Max connected entities to return."),
) -> None:
    """Recall everything related to a person, place, topic, or event via knowledge graph."""
    result = _get_svc().recall_related(entity, max_hops=max_hops, limit=limit)
    _output(result)


@app.command()
def explain(
    entity_a: str = typer.Argument(..., help="First entity name."),
    entity_b: str = typer.Argument(..., help="Second entity name."),
) -> None:
    """Explain how two entities are connected through the knowledge graph."""
    result = _get_svc().explain_connection(entity_a, entity_b)
    _output(result)


@app.command()
def entities(
    limit: int = typer.Option(50, "--limit", "-l", help="Max entities to return."),
) -> None:
    """List top canonical entities from the knowledge graph."""
    result = _get_svc().list_entities(limit=limit)
    _output(result)


@app.command()
def dates() -> None:
    """List all dates that have memory entries."""
    result = _get_svc().list_memory_dates()
    _output(result)


@app.command()
def timeline(
    start_date: Optional[str] = typer.Option(None, "--from", help="Start date (YYYY-MM-DD)."),
    end_date: Optional[str] = typer.Option(None, "--to", help="End date (YYYY-MM-DD)."),
    limit: int = typer.Option(50, "--limit", "-l", help="Max entries to return."),
    sort_by: str = typer.Option(
        "processing_time",
        "--sort-by",
        "-s",
        help="Sort by 'processing_time' (default) or 'event_time'.",
    ),
) -> None:
    """Get a chronologically ordered sequence of memories."""
    result = _get_svc().get_timeline(
        start_date=start_date, end_date=end_date, limit=limit, sort_by=sort_by
    )
    _output(result)


if __name__ == "__main__":
    app()
