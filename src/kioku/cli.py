"""Kioku CLI — Command-line interface for Kioku memory agent."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

try:
    import typer
except ImportError:
    raise ImportError(
        "Typer is required to run the CLI. Install it with: pip install kioku-agent-kit[cli]"
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
def entities(
    limit: int = typer.Option(50, "--limit", "-l", help="Max entities to return."),
) -> None:
    """List top canonical entities from the knowledge graph."""
    result = _get_svc().list_entities(limit=limit)
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


@app.command()
def setup(
    user_id: Optional[str] = typer.Option(
        None, "--user-id", "-u",
        help="Your Kioku user ID (e.g. 'personal', 'work'). Defaults to $KIOKU_USER_ID or 'personal'.",
    ),
    output_dir: Path = typer.Option(
        Path.cwd(), "--dir", "-d",
        help="Directory to generate docker-compose.yml into (default: current dir).",
    ),
    no_docker: bool = typer.Option(False, "--no-docker", help="Skip Docker database startup."),
    no_model: bool = typer.Option(False, "--no-model", help="Skip Ollama model pull."),
) -> None:
    """One-command setup: generate configs, start databases, pull embedding model.

    After running setup, use Kioku without cloning the repository:

    \b
    kioku setup --user-id personal
    kioku save "First memory" --mood happy
    kioku search "memory"

    To get template files for Claude Code / Cursor:

    \b
    kioku init    # sets up CLAUDE.md and .claude/skills/kioku/SKILL.md
    """
    import importlib.resources as pkg_resources

    RESOURCES = Path(__file__).parent / "resources"

    # ── Full setup ──
    resolved_user_id = user_id or os.environ.get("KIOKU_USER_ID", "personal")

    typer.echo("")
    typer.echo("╔══════════════════════════════════════╗")
    typer.echo("║     Kioku Agent Kit — Setup          ║")
    typer.echo("╚══════════════════════════════════════╝")
    typer.echo("")
    typer.echo(f"User ID   : {resolved_user_id}")
    typer.echo(f"Output dir: {output_dir}")
    typer.echo("")

    # Step 1: Generate docker-compose.yml
    typer.echo("── Step 1: Generating docker-compose.yml ──")
    dc_src = RESOURCES / "docker-compose.yml"
    dc_dst = output_dir / "docker-compose.yml"
    if dc_dst.exists():
        typer.echo(f"  ⚠️  {dc_dst} already exists — skipping (remove to regenerate)")
    else:
        shutil.copy(dc_src, dc_dst)
        typer.echo(f"  ✅ Written: {dc_dst}")

    # Step 2: Start databases
    if not no_docker:
        typer.echo("")
        typer.echo("── Step 2: Starting databases (Docker) ──")
        if shutil.which("docker") is None:
            typer.echo("  ⚠️  Docker not found — skipping. Install: https://docker.com")
        else:
            try:
                result = subprocess.run(
                    ["docker", "compose", "-f", str(dc_dst), "up", "-d", "kioku-chromadb", "kioku-falkordb"],
                    capture_output=True, text=True, timeout=60,
                )
                if result.returncode == 0:
                    typer.echo("  ✅ kioku-chromadb + kioku-falkordb started")
                else:
                    typer.echo(f"  ⚠️  Docker error: {result.stderr.strip()[:200]}")
            except subprocess.TimeoutExpired:
                typer.echo("  ⚠️  Docker timed out — databases may be starting in background")
            except Exception as e:
                typer.echo(f"  ⚠️  Docker failed: {e}")
    else:
        typer.echo("  ⏭️  Skipped Docker startup (--no-docker)")

    # Step 3: Pull embedding model
    if not no_model:
        typer.echo("")
        typer.echo("── Step 3: Embedding model (Ollama) ──")
        ollama_model = os.environ.get("KIOKU_OLLAMA_MODEL", "bge-m3")
        if shutil.which("ollama") is None:
            typer.echo("  ⚠️  Ollama not found — skipping. Install: https://ollama.com")
            typer.echo("      Kioku will use fake embeddings (BM25 still works).")
        else:
            check = subprocess.run(["ollama", "list"], capture_output=True, text=True)
            if ollama_model in check.stdout:
                typer.echo(f"  ✅ Model {ollama_model} already available")
            else:
                typer.echo(f"  Pulling {ollama_model} (may take a few minutes)...")
                result = subprocess.run(["ollama", "pull", ollama_model], timeout=600)
                if result.returncode == 0:
                    typer.echo(f"  ✅ Model {ollama_model} ready")
                else:
                    typer.echo(f"  ⚠️  Pull failed — run: ollama pull {ollama_model}")
    else:
        typer.echo("  ⏭️  Skipped model pull (--no-model)")

    # Step 4: Create config.env
    typer.echo("")
    typer.echo("── Step 4: Configuration ──")
    config_dir = Path.home() / ".kioku"
    config_dir.mkdir(exist_ok=True)
    config_file = config_dir / "config.env"

    if config_file.exists():
        typer.echo(f"  ✅ Config already exists: {config_file}")
    else:
        from datetime import date
        config_file.write_text(
            f"""# Kioku Agent Kit — Configuration
# Generated on {date.today()}

KIOKU_USER_ID={resolved_user_id}

# Anthropic API key (for entity extraction in search)
# Get it at: https://console.anthropic.com
KIOKU_ANTHROPIC_API_KEY=

# Database endpoints (match docker-compose defaults)
KIOKU_CHROMA_HOST=localhost
KIOKU_CHROMA_PORT=8001
KIOKU_FALKORDB_HOST=localhost
KIOKU_FALKORDB_PORT=6381

# Embedding
KIOKU_OLLAMA_BASE_URL=http://localhost:11434
KIOKU_OLLAMA_MODEL=bge-m3
""",
            encoding="utf-8",
        )
        typer.echo(f"  ✅ Created: {config_file}")
        typer.echo(f"  ⚠️  Edit {config_file} to add KIOKU_ANTHROPIC_API_KEY")

    # Done
    typer.echo("")
    typer.echo("╔══════════════════════════════════════╗")
    typer.echo("║         Setup Complete! 🎉           ║")
    typer.echo("╚══════════════════════════════════════╝")
    typer.echo("")
    typer.echo("Quick start:")
    typer.echo(f'  export KIOKU_USER_ID={resolved_user_id}')
    typer.echo('  kioku save "Your first memory" --mood happy')
    typer.echo('  kioku search "memory"')
    typer.echo("")
    typer.echo("For Claude Code / Cursor:")
    typer.echo("  kioku init    # automatically sets up CLAUDE.md and skills directory")
    typer.echo("")


@app.command()
def init() -> None:
    """Initialize Kioku in the current project for Claude Code / Cursor."""
    import importlib.resources as pkg_resources
    from pathlib import Path

    RESOURCES = Path(__file__).parent / "resources"

    # Write CLAUDE.md
    claude_dst = Path.cwd() / "CLAUDE.md"
    claude_dst.write_text((RESOURCES / "CLAUDE.agent.md").read_text(encoding="utf-8"))

    # Write SKILL
    skill_dir = Path.cwd() / ".claude" / "skills" / "kioku"
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_dst = skill_dir / "SKILL.md"
    skill_dst.write_text((RESOURCES / "SKILL.md").read_text(encoding="utf-8"))

    typer.echo("")
    typer.echo(f"✅ Created: {claude_dst}")
    typer.echo(f"✅ Created: {skill_dst}")
    typer.echo("")
    typer.echo("Claude Code and Cursor will now use Kioku automatically!")
    typer.echo("Simply type 'claude' and start asking it to remember things.")
    typer.echo("")


if __name__ == "__main__":
    app()
