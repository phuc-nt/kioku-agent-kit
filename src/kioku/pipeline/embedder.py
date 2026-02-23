"""Embedding provider — wraps Ollama for local vector embeddings."""

from __future__ import annotations

import hashlib
from typing import Protocol


class EmbeddingProvider(Protocol):
    """Protocol for embedding providers."""

    def embed(self, text: str) -> list[float]: ...


class OllamaEmbedder:
    """Ollama-based local embedding provider."""

    def __init__(self, host: str = "http://localhost:11434", model: str = "nomic-embed-text"):
        self.host = host
        self.model = model
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import ollama

            self._client = ollama.Client(host=self.host)
        return self._client

    def embed(self, text: str) -> list[float]:
        """Generate embedding vector for text."""
        response = self.client.embed(model=self.model, input=text)
        return response["embeddings"][0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        response = self.client.embed(model=self.model, input=texts)
        return response["embeddings"]


class FakeEmbedder:
    """Deterministic fake embedder for testing (no external dependencies).

    Generates a fixed-dimension vector from text hash.
    Same text always produces the same vector.
    """

    def __init__(self, dimensions: int = 128):
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        """Generate a deterministic pseudo-embedding from text hash."""
        h = hashlib.sha256(text.encode()).hexdigest()
        # Convert hex to float values between -1 and 1
        vector = []
        for i in range(self.dimensions):
            idx = i % len(h)
            val = (int(h[idx], 16) - 8) / 8.0  # Range: -1.0 to 0.875
            vector.append(val)
        return vector

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]
