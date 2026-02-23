# Kioku MCP — Claude Assistant Guide

You are Claude Code, an AI agent working on the Kioku MCP server project. Your goal is to help implement feature restructuring and maintain code quality based on the requirements defined in the `docs` directory.

## Current Primary Task: Refactoring & CLI Support
The user might ask you to implement the phases outlined in `docs/06-restructure-plan.md`. 
**CRITICAL:**
1. **Always read `docs/06-restructure-plan.md`** first to understand the Phase and objective you are working on.
2. Read `src/kioku/server.py` — this file currently contains ALL business logic, FastMCP decorators, and tool coordination, and needs to be carefully refactored without breaking any functionality.
3. Be aware that the project uses 6 core tools: `save_memory`, `search_memories`, `recall_related`, `explain_connection`, `get_timeline`, and `list_memory_dates` (Note: `get_memories_by_date` and `get_life_patterns` were recently removed to adhere to the Minimalist architecture).

## Codebase Context
- Read `docs/01-requirements.md` and `docs/02-system-design.md` for architectural context.
- We use a **Minimalist RAG Architecture**: `SQLite FTS5` for BM25, `ChromaDB` for Vector Search, and `FalkorDB` for GraphDB Traversal. 
- Python 3.12 / 3.13 is used.
- Dependencies are managed by `uv`. Use `uv add` to add packages.

## Testing Strategy
1. **Integration Tests (`tests/`)**: Run `make test` to execute fast integration tests using mocks (FakeEmbedder, InMemoryGraphStore). Tests must maintain 100% pass rate.
2. **End-to-End Tests**: Run `export $(grep -v '^#' .env | xargs) && python tests/e2e_mcp_client.py`. This acts as a real MCP Client via stdio, executing all 6 tools, 2 resources, and 3 prompts against real Live DBs and Anthropic API. Ensure it passes without errors when logic is changed.

## Guidelines
- Write strict type hints (`-> dict`, `-> list`, etc.).
- Update integration tests in `/tests/` when modifying logic. Use `make test` to ensure 100% test pass.
- **Graceful degradation is a must:** Missing databases (ChromaDB, FalkorDB) or missing LLM parameters should gracefully fallback (e.g., FakeEmbedder, InMemoryGraphStore) and never crash the CLI/MCP app.
- Never write duplicate code logic. A `KiokuService` class should become the single source of truth for both MCP interfaces and future CLI interfaces.
- Any modifications to terminal output logic for CLI should display properly in Vietnamese (`ensure_ascii=False` when printing JSON).
