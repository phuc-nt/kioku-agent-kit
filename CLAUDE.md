# Kioku Agent Guide

You are an AI assistant with access to **Kioku**, a long-term personal memory engine.
This file tells you how to use it. Read it once at the start of each session.

---

## What is Kioku?

Kioku stores memories in a tri-hybrid index (BM25 keyword + semantic vector + knowledge graph).
You interact via CLI commands. All data is local, namespaced by `KIOKU_USER_ID`.

## Setup & Verification (CRITICAL FIRST STEP)

Before doing anything, verify Kioku is available:
```bash
kioku --version
```

**If `kioku` is NOT installed or command fails:**
1. Install it: `pip install kioku-agent-kit[full]`
2. Initialize it: `kioku setup --user-id personal`
   *(This starts ChromaDB & FalkorDB via Docker, downloads Ollama models, and creates `~/.kioku/config.env`)*
3. **Important:** Read `~/.kioku/config.env` and ask the User to provide an Anthropic API Key if `KIOKU_ANTHROPIC_API_KEY` is empty. You must export this key in your environment or save it to `.env` for entity extraction to work.

### ⚠️ DANGER: Preserving User Data
- **NEVER** run commands like `docker compose down -v` or `docker rm -f` on any existing Kioku, Redis, or ChromaDB containers without explicit user permission.
- The user might have existing containers (`kioku-mcp-falkordb-1`, `chromadb`, etc.) that hold their **actual data**.
- Only run `kioku setup` to initialize newly installed Kioku instances (it uses non-conflicting container names and ports).

If Docker or Ollama fails to start during setup, don't worry. Kioku has graceful degradation and works fine with BM25 keyword search only.

---

## 4 Commands

| Command | When to use |
|---|---|
| `kioku search "QUERY"` | Any recall, lookup, context retrieval |
| `kioku save "TEXT"` | Any new information worth keeping |
| `kioku timeline --from DATE --to DATE` | Chronological "what happened on X date?" |
| `kioku entities` | Browse what's in the knowledge graph |

---

## Search — Always Enrich First

Before calling `kioku search`, expand the query. The engine extracts entities from your query text — richer query = better extraction.

**Enrichment rules:**
1. Replace pronouns with real names (`"I"` → `"[UserName]"`)
2. Add relevant entity names you already know
3. Include context keywords

**Examples:**
```bash
# User: "what do you know about me?"
kioku search "[Name] profile background work family hobbies interests goals"

# User: "how's Alice doing?"
kioku search "Alice [Name] colleague relationship project recent events"

# User: "what happened last year at work?"
kioku search "[Name] work [company] 2025 projects achievements challenges"
```

**With explicit entities (faster, skip auto-extraction):**
```bash
kioku search "QUERY" --entities "Alice,ProjectX,2025" --limit 10
```

---

## Save — Preserve Original Text

```bash
kioku save "TEXT" --mood MOOD --tags "tag1,tag2"
kioku save "TEXT" --mood MOOD --tags "tag1" --event-time "YYYY-MM-DD"
```

**Rules:**
- ✅ Keep the **full text** — never summarize what the user said
- ✅ Split long content (>300 chars) into multiple focused saves
- ✅ `--event-time` = when the event happened (not today), e.g. `"2024-03-21"`
- ❌ Don't mix your commentary into the saved text

**Mood options:** `happy`, `sad`, `excited`, `anxious`, `grateful`, `proud`, `reflective`, `neutral`, `tender`, `analytical`

---

## Timeline

For date-based queries, use timeline instead of search:
```bash
# "What happened last Monday?"
kioku timeline --from 2026-02-24 --to 2026-02-24

# "Summary of last month"
kioku timeline --from 2026-01-01 --to 2026-01-31
```

---

## Decision Tree

```
User request?
│
├─ Recall / search / "who is X?" / "what do I know about Y?"
│   → ENRICH → kioku search "enriched query"
│
├─ "What happened on [date] / last week / in [month]?"
│   → kioku timeline --from DATE --to DATE
│
├─ "What's in your memory?" / browse
│   → kioku entities
│
└─ User shares new info / "remember this"
    → kioku save "text" --mood X --tags "a,b"
      (split if >300 chars)
```

---

## Session Start Pattern

At the start of a new conversation, proactively recall user context:
```bash
kioku search "[UserName] profile background current focus goals"
```

This gives you context before the user even asks.

---

## Important

- **Never invent memories.** If search returns 0 results, say so honestly.
- **Always save** when user shares something new — don't wait to be asked.
- **Graph context** in search results (`graph_context.evidence`) often contains richer relationship data than raw text results. Use both.

---

## Data Storage

All data stored at `~/.kioku/users/$KIOKU_USER_ID/`:
- `memory/YYYY-MM-DD.md` — human-readable markdown (source of truth)
- SQLite FTS5 — keyword index
- ChromaDB — vector embeddings
- FalkorDB — knowledge graph

The `.md` files are always readable. If DBs fail, memories aren't lost.
