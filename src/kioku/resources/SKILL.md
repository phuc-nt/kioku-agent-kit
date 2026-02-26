---
name: kioku
description: >
  Long-term personal memory for AI agents. Use Kioku to save and retrieve memories,
  events, thoughts, people, and relationships across conversations. Backed by
  tri-hybrid search (BM25 + vector + knowledge graph). Use when: user asks you to
  remember something, retrieve past context, search memories, or explore connections
  between people/events. NOT for: code execution, web search, or file operations.
---

# Kioku — Agent Memory Skill

Kioku is your long-term memory engine. It stores what matters and retrieves it intelligently via tri-hybrid search (BM25 keyword + semantic vector + knowledge graph traversal).

---

## 1. Environment & Setup (CRITICAL FIRST STEP)

Because each bash tool call is isolated, you **MUST** load the environment variables (and virtual environment if present) on **EVERY SINGLE COMMAND**:

**Always use this prefix for every kioku command:**
```bash
source .venv/bin/activate && export $(grep -v '^#' ~/.kioku/config.env | xargs 2>/dev/null) && kioku <command>
```
*(If no `.venv` exists, omit the `source .venv/bin/activate &&` part).*

Before doing anything, verify Kioku is available:
```bash
source .venv/bin/activate && kioku --version
```

**If `kioku` is NOT installed or command fails:**
1. Check for `.venv`. The user might have installed it inside a virtual environment. Try activating it first!
2. If completely missing, create a venv (macOS blocks global installs). **CRITICAL:** Use Python 3.12 for ChromaDB compatibility:
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   pip install "kioku-agent-kit[full]"
   ```
3. Initialize it: `source .venv/bin/activate && kioku setup --user-id personal`
4. **Important:** Read `~/.kioku/config.env` and ask the User to provide an Anthropic API Key if `KIOKU_ANTHROPIC_API_KEY` is empty. You must save it to `~/.kioku/config.env` for entity extraction to work.

### ⚠️ DANGER: Preserving User Data
- **NEVER** run commands like `docker compose down -v` or `docker rm -f` on any existing Kioku, Redis, or ChromaDB containers without explicit user permission.
- **Ignore User DBs**: Do NOT assume a running `falkordb`, `chromadb`, or `redis` container belongs to Kioku unless it is explicitly named `kioku-agent-kit-...` or running on Kioku's isolated ports (8001, 6381, 11435). If you see other DBs, ignore them — they are the user's data. Run `kioku setup` to spin up Kioku's isolated DBs.
- **Port Conflicts**: If `kioku setup` fails because the default ports (8001, 6381, 11435) are already in use, **DO NOT STOP** the user's existing containers. Instead, dynamically find free ports, edit `docker-compose.yml` and `~/.kioku/config.env` to use the new ports, and run `docker compose up -d`.

---

## 2. The 4 Commands — Pick the Right One

| Command | When to use |
|---|---|
| `kioku search "QUERY"` | Any recall, lookup, context retrieval |
| `kioku save "TEXT"` | Any new information worth keeping |
| `kioku timeline --from DATE --to DATE` | Chronological "what happened on X date?" |
| `kioku entities` | Browse what's in the knowledge graph |

---

## 3. `kioku search` — Always Enrich First

**Mandatory step: ENRICH the query before searching.**
The engine auto-extracts entities from your query text — the richer the query, the more accurate the extraction.

**Enrichment rules:**
1. Replace pronouns ("I", "me", "my") with real names you know (`"[UserName]"`)
2. Expand vague questions with known context keywords
3. Add specific entity names when confident

**Examples:**
```bash
# General profiling
source .venv/bin/activate && export $(grep -v '^#' ~/.kioku/config.env | xargs 2>/dev/null) && kioku search "[Name] profile background work family hobbies interests goals"

# Context-specific
source .venv/bin/activate && export $(grep -v '^#' ~/.kioku/config.env | xargs 2>/dev/null) && kioku search "Alice [Name] colleague relationship project recent events"

# Explicit entity searching saves time
source .venv/bin/activate && export $(grep -v '^#' ~/.kioku/config.env | xargs 2>/dev/null) && kioku search "QUERY" --entities "Alice,ProjectX,2025" --limit 10
```

---

## 4. `kioku save` — Preserve Original Text

Use **every time** the user shares something worth remembering.

```bash
source .venv/bin/activate && export $(grep -v '^#' ~/.kioku/config.env | xargs 2>/dev/null) && kioku save "TEXT" --mood MOOD --tags "tag1,tag2"
```

**Critical rules:**
- ✅ Preserve the **full original text** — don't summarize what the user said
- ✅ If content is long (>300 chars) or covers multiple topics, **split into multiple saves**
- ✅ `--event-time` = when the event actually happened (not today), e.g. `"2024-03-21"`
- ✅ Choose mood from: `happy`, `sad`, `excited`, `anxious`, `grateful`, `proud`, `reflective`, `neutral`, `tender`, `analytical`
- ❌ Don't include your editorial comments in the saved text — save raw information only

---

## 5. `kioku timeline` — Chronological recall only

Use **only** for "what happened on/around [date]" type queries.

```bash
# "What happened last Monday?"
source .venv/bin/activate && export $(grep -v '^#' ~/.kioku/config.env | xargs 2>/dev/null) && kioku timeline --from 2026-02-24 --to 2026-02-24

# "Summary of last month"
source .venv/bin/activate && export $(grep -v '^#' ~/.kioku/config.env | xargs 2>/dev/null) && kioku timeline --from 2026-01-01 --to 2026-01-31
```
For "last week", "yesterday" etc. — calculate the dates first, then call timeline.

---

## 6. `kioku entities` — Browse entity vocabulary

Use when user asks "what do you know?" or "what's in your memory database?"
```bash
source .venv/bin/activate && export $(grep -v '^#' ~/.kioku/config.env | xargs 2>/dev/null) && kioku entities --limit 50
```
Returns canonical entity names with type (PERSON, PLACE, EVENT, TOPIC, EMOTION) and mention count.

---

## 7. Decision Tree & Start Pattern

```
User request?
│
├─ New Conversation / Session Start
│   → source .venv/bin/activate && export $(grep -v '^#' ~/.kioku/config.env | xargs 2>/dev/null) && kioku search "[UserName] profile background current focus goals"
│
├─ Search / recall / "who is X?"
│   → ENRICH → kioku search "enriched query"
│
├─ "What happened on [date] / last week?"
│   → kioku timeline --from DATE --to DATE
│
├─ "What's in your memory?"
│   → kioku entities
│
└─ User shares info / "remember this"
    → source .venv/bin/activate && export $(grep -v '^#' ~/.kioku/config.env | xargs 2>/dev/null) && kioku save "text" --mood X --tags "a,b,c"
```

- **Never invent memories.** If search returns 0 results, say so honestly.
- **Always save** when user shares something new — don't wait to be asked.
- **Graph context** in search results (`graph_context.evidence`) often contains richer relationship data than raw text results. Use both.
