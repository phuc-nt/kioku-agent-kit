"""Kioku Service — Single source of truth for all business logic."""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timedelta, timezone

from kioku.config import Settings
from kioku.pipeline.embedder import FakeEmbedder, OllamaEmbedder
from kioku.pipeline.extractor import ClaudeExtractor, FakeExtractor
from kioku.pipeline.graph_writer import FalkorGraphStore, InMemoryGraphStore
from kioku.pipeline.keyword_writer import KeywordIndex
from kioku.pipeline.vector_writer import VectorStore
from kioku.search.bm25 import bm25_search
from kioku.search.graph import graph_search
from kioku.search.reranker import rrf_rerank
from kioku.search.semantic import vector_search
from kioku.storage.markdown import save_entry

log = logging.getLogger(__name__)

JST = timezone(timedelta(hours=7))


class KiokuService:
    """Core business logic for Kioku — shared by MCP server and CLI."""

    def __init__(self, settings: Settings | None = None) -> None:
        from kioku.config import settings as default_settings

        self.settings = settings or default_settings
        self.settings.ensure_dirs()

        # SQLite FTS5
        self.keyword_index = KeywordIndex(self.settings.sqlite_path)

        # Vector store — try Ollama, fallback to FakeEmbedder
        try:
            embedder = OllamaEmbedder(
                host=self.settings.ollama_host, model=self.settings.ollama_model
            )
            embedder.embed("test")
            log.info("Using Ollama embedder (%s)", self.settings.ollama_model)
        except Exception:
            log.warning("Ollama not available, using FakeEmbedder (no semantic search quality)")
            embedder = FakeEmbedder()

        self.vector_store = self._init_vector_store(embedder)

        # Knowledge graph — try FalkorDB, fallback to InMemoryGraphStore
        try:
            self.graph_store = FalkorGraphStore(
                host=self.settings.falkordb_host,
                port=self.settings.falkordb_port,
                graph_name=self.settings.falkordb_graph,
            )
            _ = self.graph_store.graph
            log.info("Using FalkorDB graph store")
        except Exception:
            log.warning("FalkorDB not available, using InMemoryGraphStore")
            self.graph_store = InMemoryGraphStore()

        # Entity extractor — try Claude, fallback to FakeExtractor
        if self.settings.anthropic_api_key:
            self.extractor = ClaudeExtractor(api_key=self.settings.anthropic_api_key)
            log.info("Using Claude extractor for entity extraction")
        else:
            log.warning("No Anthropic API key, using FakeExtractor (rule-based)")
            self.extractor = FakeExtractor()

    def _init_vector_store(self, embedder) -> VectorStore:
        """Initialize ChromaDB with mode: server, embedded, or auto-detect."""
        s = self.settings
        mode = s.chroma_mode

        if mode == "server":
            return VectorStore(
                embedder=embedder,
                collection_name=s.chroma_collection,
                host=s.chroma_host,
                port=s.chroma_port,
            )

        if mode == "embedded":
            log.info("Using ChromaDB embedded mode at %s", s.chroma_persist_dir)
            return VectorStore(
                embedder=embedder,
                collection_name=s.chroma_collection,
                persist_dir=s.chroma_persist_dir,
            )

        # auto mode: try server → embedded → ephemeral
        try:
            store = VectorStore(
                embedder=embedder,
                collection_name=s.chroma_collection,
                host=s.chroma_host,
                port=s.chroma_port,
            )
            store.count()  # test connection
            log.info(
                "ChromaDB auto-detect: using server mode (%s:%s)", s.chroma_host, s.chroma_port
            )
            return store
        except Exception:
            log.info("ChromaDB server not available, trying embedded mode")

        try:
            store = VectorStore(
                embedder=embedder,
                collection_name=s.chroma_collection,
                persist_dir=s.chroma_persist_dir,
            )
            log.info("ChromaDB auto-detect: using embedded mode at %s", s.chroma_persist_dir)
            return store
        except Exception:
            log.warning("ChromaDB embedded mode failed, using ephemeral (no persistence)")

        return VectorStore(
            embedder=embedder,
            collection_name=s.chroma_collection,
        )

    # ─── Tools ───────────────────────────────────────────────────────────

    def save_memory(
        self,
        text: str,
        mood: str | None = None,
        tags: list[str] | None = None,
    ) -> dict:
        """Save a memory entry. Stores text to markdown and indexes for search."""
        date = datetime.now(JST).strftime("%Y-%m-%d")
        content_hash = hashlib.sha256(text.encode()).hexdigest()

        # Phase 7: Context-aware entity extraction with event_time
        event_time: str | None = None
        try:
            # Get canonical entities for disambiguation
            canonical = self.graph_store.get_canonical_entities(limit=50)
            context_entities = [e["name"] for e in canonical]
            extraction = self.extractor.extract(
                text,
                context_entities=context_entities,
                processing_date=date,
            )
            event_time = extraction.event_time
            if extraction.entities:
                self.graph_store.upsert(
                    extraction,
                    date=date,
                    timestamp="",
                    source_hash=content_hash,
                )
                log.info(
                    "Extracted %d entities, %d relationships, event_time=%s",
                    len(extraction.entities),
                    len(extraction.relationships),
                    event_time,
                )
        except Exception as e:
            log.warning("Entity extraction/graph indexing failed: %s", e)

        # Save to markdown (source of truth)
        entry = save_entry(
            self.settings.memory_dir,
            text,
            mood=mood,
            tags=tags,
            event_time=event_time,
        )

        # Index in SQLite (primary document store)
        self.keyword_index.index(
            content=text,
            date=date,
            timestamp=entry.timestamp,
            mood=mood or "",
            content_hash=content_hash,
            event_time=event_time or "",
        )

        # Index in ChromaDB (vector similarity only)
        try:
            self.vector_store.add(
                content=text,
                date=date,
                timestamp=entry.timestamp,
                mood=mood or "",
                tags=tags,
                content_hash=content_hash,
                event_time=event_time or "",
            )
        except Exception as e:
            log.warning("Vector indexing failed: %s", e)

        return {
            "status": "saved",
            "timestamp": entry.timestamp,
            "date": date,
            "mood": mood,
            "tags": tags,
            "event_time": event_time,
            "indexed": True,
        }

    def search_memories(
        self,
        query: str,
        limit: int = 10,
        date_from: str | None = None,
        date_to: str | None = None,
        entities: list[str] | None = None,
    ) -> dict:
        """Search through all saved memories using tri-hybrid search.

        Phase 7: Hydrates results from SQLite via content_hash for consistent raw text.

        Args:
            entities: Optional list of entity names pre-extracted by Agent.
                      If provided, graph_search uses them as seeds directly
                      instead of tokenizing the query. Improves KG precision.
        """
        clean_query = re.sub(r"[^\w\s]", " ", query)

        if entities:
            # Entity-focused mode: all 3 legs target the same entities
            # BM25: search using entity names as keywords
            bm25_query = " ".join(entities)
            bm25_results = bm25_search(self.keyword_index, bm25_query, limit=limit * 3)

            # Vector: search with original query but filter to entity-relevant results
            vec_all = vector_search(self.vector_store, query, limit=limit * 5)
            entity_lower = [e.lower() for e in entities]
            vec_results = [
                r for r in vec_all
                if any(ent in r.content.lower() for ent in entity_lower)
            ]

            # Graph: use entities as seeds directly
            kg_results = graph_search(self.graph_store, query, limit=limit * 3, entities=entities)
        else:
            # Default mode: standard tri-hybrid
            bm25_results = bm25_search(self.keyword_index, clean_query, limit=limit * 3)
            vec_results = vector_search(self.vector_store, query, limit=limit * 3)
            kg_results = graph_search(self.graph_store, query, limit=limit * 3)

        results = rrf_rerank(bm25_results, vec_results, kg_results, limit=limit)

        if date_from or date_to:
            filtered = []
            for r in results:
                if date_from and r.date and r.date < date_from:
                    continue
                if date_to and r.date and r.date > date_to:
                    continue
                filtered.append(r)
            results = filtered

        # Phase 7: Hydrate from SQLite via content_hash (deduplicated)
        hashes = list({r.content_hash for r in results if r.content_hash})
        hydrated = {}
        if hashes:
            try:
                hydrated = self.keyword_index.get_by_hashes(hashes)
            except Exception as e:
                log.warning("Search hydration failed: %s", e)

        output_results = []
        for r in results:
            # If we have hydrated data, use it for authoritative content
            if r.content_hash and r.content_hash in hydrated:
                entry = hydrated[r.content_hash]
                output_results.append({
                    "content": entry["text"],
                    "date": entry.get("date", r.date),
                    "mood": entry.get("mood", r.mood),
                    "score": round(r.score, 4),
                    "source": r.source,
                })
            else:
                output_results.append({
                    "content": r.content,
                    "date": r.date,
                    "mood": r.mood,
                    "score": round(r.score, 4),
                    "source": r.source,
                })

        return {
            "query": query,
            "count": len(output_results),
            "results": output_results,
        }

    def recall_related(self, entity: str, max_hops: int = 2, limit: int = 10) -> dict:
        """Recall everything related to a person, place, topic, or event.

        Uses Graph traversal + SQLite hydration (Phase 7 Universal Identifier).
        """
        result = self.graph_store.traverse(entity, max_hops=max_hops, limit=limit)

        # Phase 7: Collect source_hashes from edges for O(1) hydration
        source_hashes = list({e.source_hash for e in result.edges if e.source_hash})
        hydrated = {}
        if source_hashes:
            try:
                hydrated = self.keyword_index.get_by_hashes(source_hashes)
            except Exception as e:
                log.warning("Hydration from SQLite failed: %s", e)

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
            "source_memories": [
                {
                    "content": entry["text"],
                    "date": entry.get("date", ""),
                    "mood": entry.get("mood", ""),
                }
                for entry in hydrated.values()
            ],
        }

    def explain_connection(self, entity_a: str, entity_b: str) -> dict:
        """Explain how two entities are connected through the knowledge graph.

        Phase 7: Hydrates source memories from SQLite via source_hash.
        """
        result = self.graph_store.find_path(entity_a, entity_b)

        # Phase 7: Collect source_hashes for hydration
        source_hashes = list({e.source_hash for e in result.edges if e.source_hash})
        hydrated = {}
        if source_hashes:
            try:
                hydrated = self.keyword_index.get_by_hashes(source_hashes)
            except Exception as e:
                log.warning("Explain hydration failed: %s", e)

        return {
            "from": entity_a,
            "to": entity_b,
            "connected": len(result.paths) > 0,
            "paths": result.paths,
            "nodes": [{"name": n.name, "type": n.type} for n in result.nodes],
            "evidence": [
                {
                    "source": e.source,
                    "target": e.target,
                    "type": e.rel_type,
                    "evidence": e.evidence,
                }
                for e in result.edges
            ],
            "source_memories": [
                {
                    "content": entry["text"],
                    "date": entry.get("date", ""),
                    "mood": entry.get("mood", ""),
                }
                for entry in hydrated.values()
            ],
        }

    def list_entities(self, limit: int = 50) -> dict:
        """List top canonical entities from the knowledge graph.

        Returns entities with their names, types, and mention counts.
        Agent should call this BEFORE search to know which entities exist,
        then extract matching entities from user's question for the entities parameter.
        """
        canonical = self.graph_store.get_canonical_entities(limit=limit)
        return {
            "count": len(canonical),
            "entities": canonical,
        }

    def list_memory_dates(self) -> dict:
        """List all dates that have memory entries."""
        dates = self.keyword_index.get_dates()
        return {
            "count": len(dates),
            "dates": dates,
        }

    def get_timeline(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 50,
        sort_by: str = "processing_time",
    ) -> dict:
        """Get a chronologically ordered sequence of memories.

        Args:
            sort_by: "processing_time" (when recorded) or "event_time" (when it happened).
        """
        entries = self.keyword_index.get_timeline(
            start_date,
            end_date,
            limit,
            sort_by=sort_by,
        )
        return {
            "count": len(entries),
            "sort_by": sort_by,
            "timeline": entries,
        }

    # ─── Resources ───────────────────────────────────────────────────────

    def read_memory_resource(self, date: str) -> str:
        """Read the raw markdown file for a specific date."""
        filepath = self.settings.memory_dir / f"{date}.md"
        if not filepath.exists():
            return f"No memories found for date {date}."
        return filepath.read_text()

    def read_entity_resource(self, entity: str) -> str:
        """Read a comprehensive profile of an entity from the knowledge graph."""
        result = self.graph_store.traverse(entity, max_hops=2, limit=50)

        if not result.nodes:
            return f"Entity '{entity}' not found in the knowledge graph."

        root_node = next(
            (n for n in result.nodes if n.name.lower() == entity.lower()), result.nodes[0]
        )

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
                strength = (
                    "Strongly" if e.weight >= 0.8 else "Moderately" if e.weight >= 0.5 else "Weakly"
                )
                out.append(f"- **{strength} {e.rel_type.lower()}** to `{e.target}`")
                if e.evidence:
                    out.append(f'  > *"{e.evidence}"*')

        out.append("")
        out.append("These details are generated from traversing the knowledge graph memory.")
        return "\n".join(out)

    # ─── Prompts ─────────────────────────────────────────────────────────

    def reflect_on_day(self) -> str:
        """Generate a prompt template for end-of-day reflection."""
        today = datetime.now(JST).strftime("%Y-%m-%d")
        return f"""Please review my memory entries for today ({today}) by reading the kioku://memories/{today} resource.
Then, provide a thoughtful end-of-day reflection that covers:
1. The overall emotional tone of my day.
2. The key events and entities I interacted with.
3. A positive takeaway or lesson for tomorrow.

Respond as a compassionate companion (my 'Kioku')."""

    def analyze_relationships(self, entity_name: str) -> str:
        """Generate a prompt template to analyze an entity's relationships."""
        return f"""Please use the kioku://entities/{entity_name} resource to read about '{entity_name}'.

Analyze this entity's role in my life based on the knowledge graph:
1. What is my primary emotional response surrounding this entity?
2. Who or what else is frequently connected to this entity?
3. What are some notable patterns in my memories involving {entity_name}?

Write the analysis in a helpful, introspective tone."""

    def weekly_review(self) -> str:
        """Generate a prompt template for weekly retrospective."""
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

    def close(self) -> None:
        """Clean up resources."""
        self.keyword_index.close()
