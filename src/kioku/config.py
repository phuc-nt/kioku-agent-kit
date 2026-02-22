"""Kioku configuration and settings."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings, loaded from environment variables."""

    # Paths
    memory_dir: Path = Path(os.path.expanduser("~/.kioku/memory"))
    data_dir: Path = Path(os.path.expanduser("~/.kioku/data"))

    # SQLite FTS5
    @property
    def sqlite_path(self) -> Path:
        return self.data_dir / "kioku_fts.db"

    # ChromaDB (Phase 2)
    chroma_host: str = "localhost"
    chroma_port: int = 8000

    # FalkorDB (Phase 3)
    falkordb_host: str = "localhost"
    falkordb_port: int = 6379

    # Ollama (Phase 2)
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "nomic-embed-text"

    # LLM (Phase 3)
    anthropic_api_key: str = ""

    model_config = {"env_prefix": "KIOKU_", "env_file": ".env", "extra": "ignore"}

    def model_post_init(self, __context) -> None:
        """Expand ~ in paths after loading from env."""
        object.__setattr__(self, "memory_dir", Path(os.path.expanduser(str(self.memory_dir))))
        object.__setattr__(self, "data_dir", Path(os.path.expanduser(str(self.data_dir))))

    def ensure_dirs(self) -> None:
        """Create required directories if they don't exist."""
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)


# Singleton
settings = Settings()
