# DEVLOG — Agent Setup and Stability Fixes

**Date:** 2026-02-26  
**Author:** phucnt (with AI pair programming)

---

## Overview

This development session focused on refining the Kioku Agent Kit installation and integration experience, specifically ensuring robust operation for Claude Code and Cursor across isolated shell sessions. We uncovered and resolved critical "amnesia" bugs where agents lost context of their virtual environments, and hardened the Docker setup to prevent interference with existing user databases.

## Key Challenges Identified

1. **The "Session Amnesia" Bug:** Claude Code executes each bash tool call in an isolated subshell. While it successfully installed Kioku into a `.venv` during initial setup, subsequent tool calls in new sessions failed with `command not found` because the `.venv` was not active. This caused the agent to repeatedly attempt reinstallation.
2. **Configuration Loss:** Similarly, environment variables from `~/.kioku/config.env` (crucially, `KIOKU_ANTHROPIC_API_KEY`) were lost between subshells, causing Kioku to fall back to the naive `FakeExtractor` instead of the LLM-powered entity extractor.
3. **Docker Collision Risk:** The default `kioku setup` behavior risked colliding with or overwriting a user's existing Redis, ChromaDB, or Ollama containers if they happened to be running on the host.
4. **SQLite FTS5 Parsing Errors:** When users queried terms containing hyphens (e.g., `Tech-Verse`), the FTS5 engine intercepted the hyphen as a column exclusion syntax (e.g., `NOT column Verse`), crashing the search with an `OperationalError`.

## Solutions Implemented

### 1. Isolated Execution Prefix in `SKILL.md`

We completely restructured `SKILL.md` (the primary instruction file read by the agent) to enforce a strict command prefix. The agent is now instructed that **every single Kioku command** must activate the environment and load the configuration simultaneously:

```bash
source .venv/bin/activate && export $(grep -v '^#' ~/.kioku/config.env | xargs 2>/dev/null) && kioku <command>
```

This ensures the CLI, the correct Python runtime, and the API keys are all present in the ephemeral subshell.

### 2. Streamlined `CLAUDE.md`

`CLAUDE.md` was bloated with redundant execution rules. It has been stripped down to a minimal "Identity Document" that simply points the agent to read `.claude/skills/kioku/SKILL.md` for operational instructions.

### 3. Docker Isolation & Ollama Fixes

- **Enforced Prefixing**: All `docker-compose.yml` services are uniquely prefixed (`kioku-chromadb`, `kioku-falkordb`, `kioku-ollama`).
- **Port Shifting**: Kioku services map to non-standard host ports (`8001`, `6381`, `11435`) to avoid hijacking standard user ports.
- **Ollama Pull Isolation**: Fixed a bug in `kioku setup` where the setup script pulled the Ollama model using the host's `ollama` CLI (polluting the host). It now correctly executes `docker exec kioku_ollama ollama pull ...`.
- **Ignore User DBs Rule**: Added a strict rule in `SKILL.md` instructing the agent to never touch running DB containers unless they have the `kioku-agent-kit-` prefix.

### 4. FTS5 Safe Query Handling

Patched `src/kioku/pipeline/keyword_writer.py` to wrap all user queries in double quotes before passing them to the SQLite `MATCH` clause.
This completely escapes FTS syntax, treating the input strictly as a string literal.

```python
safe_query = '"' + query.replace('"', '""') + '"'
```

### 5. Python 3.12 Enforcement

Updated both `README.md` and `SKILL.md` to mandate the use of `python3.12 -m venv .venv` during setup to ensure compatibility with ChromaDB, sidestepping issues we encountered with Python 3.14 on macOS Homebrew.

## Version Bumps

These fixes were sequentially published to PyPI:
- `v0.2.6`: `SKILL.md` shell isolation prefix.
- `v0.2.7`: `SKILL.md` fixes included in package resources.
- `v0.2.8`: Docker `ollama` execution and port isolation configs.
- `v0.2.9`: Isolated model pull fix.
- `v0.2.10`: FTS5 safe query patch.

## Next Steps

Monitor agent behavior in fresh projects to ensure the new `bootstrap.sh` and `kioku init` flows result in zero-intervention, fully automated setups.
