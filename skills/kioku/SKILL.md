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

## Setup Check

Before using, verify Kioku is available:
```bash
kioku --version
echo $KIOKU_USER_ID   # should be set (e.g. "myproject" or "personal")
```

If not installed: `pip install kioku-agent-kit[full]` and start databases with `docker compose up -d` in the kioku-agent-kit directory.

---

## 4 Tools — Pick the Right One

### 1. `kioku search` — Main retrieval (use for 90% of queries)

**Mandatory step: ENRICH the query before searching.**

The engine auto-extracts entities from your query text — the richer the query, the more accurate the extraction.

| User says | ❌ Don't search | ✅ Do search |
|---|---|---|
| "what do you know about me?" | `"me who"` | `"[Name] profile family work hobbies interests"` |
| "tell me about my family" | `"family"` | `"[Name] family: [spouse] [children] [parents] relationships"` |
| "who is Alice?" | `"Alice"` | `"Alice who? colleague friend project relationship"` |
| "how's work going?" | `"work"` | `"[Name] work [company] current projects stress feelings"` |

**Enrichment rules:**
1. Replace pronouns ("I", "me", "my") with real names you know
2. Expand vague questions with known context
3. Add specific entity names when confident

```bash
# Basic search
kioku search "ENRICHED QUERY" --limit 10

# With explicit entities (skips auto-extraction, faster)
kioku search "QUERY" --entities "Alice,project-X,2024" --limit 10
```

**Response structure:**
```json
{
  "query": "...",
  "count": 8,
  "entities_used": ["Alice", "project-X"],
  "results": [
    { "source": "vector", "score": 0.92, "content": "...", "date": "2026-01-15", "mood": "excited" }
  ],
  "graph_context": {
    "nodes": [{ "name": "Alice", "type": "PERSON", "mention_count": 12 }],
    "evidence": ["Alice was promoted in Q1 2026..."]
  }
}
```

Use `results` for direct memory recall. Use `graph_context.evidence` for relationship context.

---

### 2. `kioku save` — Save new memories

Use **every time** the user shares something worth remembering.

```bash
# Basic save
kioku save "TEXT" --mood MOOD --tags "tag1,tag2"

# With specific event time (when the event actually happened)
kioku save "TEXT" --mood MOOD --tags "tag1" --event-time "2024-03-21"
```

**Critical rules:**
- ✅ Preserve the **full original text** — don't summarize
- ✅ If content is long (>300 chars) or covers multiple topics, **split into multiple saves**
- ✅ Choose mood from: `happy`, `sad`, `excited`, `anxious`, `grateful`, `proud`, `reflective`, `neutral`, `tender`, `analytical`
- ❌ Don't include your editorial comments in the saved text — save raw information only

**When the user shares a long story:**
```bash
# Split into focused chunks
kioku save "Alice joined our team last Monday as senior engineer..." --mood "excited" --tags "alice,team,hiring"
kioku save "The project deadline was moved to March — team is stressed..." --mood "anxious" --tags "project,deadline,stress"
```

**Mood + tags selection guide:**
- `mood`: reflects the emotional tone of the memory
- `tags`: 2-5 lowercase keywords, hyphenated for multi-word (`work-life-balance`, `ai-project`)

---

### 3. `kioku timeline` — Chronological recall only

Use **only** for "what happened on/around [date]" type queries.

```bash
kioku timeline --from 2026-01-01 --to 2026-01-31
kioku timeline --from 2026-02-24 --to 2026-02-24   # single day
```

For "last week", "yesterday" etc. — calculate the dates first, then call timeline.

---

### 4. `kioku entities` — Browse entity vocabulary

Use when user asks "what do you know?" or "what's in your memory database?"

```bash
kioku entities --limit 50
```

Returns canonical entity names with type (PERSON, PLACE, EVENT, TOPIC, EMOTION) and mention count.

---

## Decision Tree

```
User request?
│
├─ Search / recall / "what do you know about X?"
│   1. ENRICH query (replace pronouns, add context)
│   2. kioku search "enriched query" --limit 10
│
├─ "What happened yesterday/last week/in March?"
│   └─ kioku timeline --from DATE --to DATE
│
├─ "What's in your database?" / browse entities
│   └─ kioku entities
│
└─ User shares info / "remember this"
    └─ kioku save "text" --mood X --tags "a,b,c"
        (split if >300 chars or multiple topics)
```

---

## Environment Variables

```bash
KIOKU_USER_ID=myproject          # data namespace (required)
KIOKU_ANTHROPIC_API_KEY=sk-ant-  # for entity extraction in search
KIOKU_OLLAMA_BASE_URL=http://localhost:11434  # embedding server
KIOKU_OLLAMA_MODEL=bge-m3
KIOKU_CHROMA_HOST=localhost
KIOKU_CHROMA_PORT=8000
KIOKU_FALKORDB_HOST=localhost
KIOKU_FALKORDB_PORT=6379
```

Override in shell or set in `.env` at project root.

---

## Common Patterns

### New conversation — recall user context
```bash
kioku search "[UserName] profile background current projects goals"
```

### User mentions a person
```bash
# Search first
kioku search "[PersonName] who relationship colleagues"
# Then save the new info
kioku save "[PersonName] is Alice's manager, joined company in 2023..." --mood neutral --tags "alice,team,people"
```

### User shares an event
```bash
kioku save "Attended Tech-Verse 2025 conference as speaker, presented AI Coding session..." \
  --mood "proud" \
  --tags "conference,speaker,ai-coding" \
  --event-time "2025-12-31"
```

### Temporal query
```bash
# "What did I do in Q1 2025?"
kioku timeline --from 2025-01-01 --to 2025-03-31
# OR for semantic context
kioku search "[Name] Q1 2025 events work personal January February March"
```

### Entity relationship query
```bash
kioku search "Alice Bob project collaboration relationship history"
```

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `kioku: command not found` | `pip install kioku-agent-kit[full]` |
| `ChromaDB connection refused` | `docker compose up -d` in kioku-agent-kit dir |
| `0 results` | Enrich query, add more entity names |
| `ResponseError: Type mismatch` | FalkorDB schema issue — restart container |
| Slow search (~10s) | Normal for first call (model load). Subsequent calls ~2-3s |
