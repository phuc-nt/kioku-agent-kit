"""ChromaDB vector store writer — indexes memory chunks as embeddings."""

from __future__ import annotations

import hashlib
from pathlib import Path

from kioku.pipeline.embedder import EmbeddingProvider


class VectorStore:
    """ChromaDB-backed vector store for memory embeddings."""

    def __init__(
        self,
        embedder: EmbeddingProvider,
        collection_name: str = "memories",
        persist_dir: str | Path | None = None,
        host: str | None = None,
        port: int | None = None,
    ):
        import chromadb

        self.embedder = embedder
        self.collection_name = collection_name

        # Connect to ChromaDB
        if host and port:
            self.client = chromadb.HttpClient(host=host, port=port)
        elif persist_dir:
            self.client = chromadb.PersistentClient(path=str(persist_dir))
        else:
            self.client = chromadb.EphemeralClient()

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add(
        self,
        content: str,
        date: str,
        timestamp: str,
        mood: str = "",
        tags: list[str] | None = None,
        content_hash: str | None = None,
        event_time: str = "",
    ) -> str:
        """Add a memory chunk to the vector store.

        Returns the document ID (content_hash). Skips duplicates.
        Uses full content_hash as universal identifier for cross-store joins.
        """
        if not content_hash:
            content_hash = hashlib.sha256(content.encode()).hexdigest()
        doc_id = content_hash[:16]

        # Check if already exists
        existing = self.collection.get(ids=[doc_id])
        if existing["ids"]:
            return doc_id  # Already indexed

        # Generate embedding
        embedding = self.embedder.embed(content)

        # Upsert to ChromaDB — lightweight metadata only, raw text in SQLite
        self.collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[
                {
                    "date": date,
                    "timestamp": timestamp,
                    "mood": mood,
                    "tags": ",".join(tags) if tags else "",
                    "content_hash": content_hash,
                    "event_time": event_time,
                }
            ],
        )
        return doc_id

    def search(
        self,
        query: str,
        limit: int = 20,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict]:
        """Semantic search using vector similarity.

        Returns list of dicts with: content, date, mood, timestamp, distance.
        """
        query_embedding = self.embedder.embed(query)

        # Build where filter for date range
        where = None
        if date_from and date_to:
            where = {"$and": [{"date": {"$gte": date_from}}, {"date": {"$lte": date_to}}]}
        elif date_from:
            where = {"date": {"$gte": date_from}}
        elif date_to:
            where = {"date": {"$lte": date_to}}

        # Clamp limit to collection size
        total = self.collection.count()
        if total == 0:
            return []
        actual_limit = min(limit, total)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=actual_limit,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        output = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                output.append(
                    {
                        "content": results["documents"][0][i] if results["documents"] else "",
                        "date": meta.get("date", ""),
                        "mood": meta.get("mood", ""),
                        "timestamp": meta.get("timestamp", ""),
                        "distance": results["distances"][0][i] if results["distances"] else 0.0,
                    }
                )
        return output

    def count(self) -> int:
        """Return total number of indexed vectors."""
        return self.collection.count()
