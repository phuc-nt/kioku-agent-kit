"""Kioku configuration and settings."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings, loaded from environment variables."""

    # User context for multi-tenant isolation
    user_id: str = "default"

    # Paths
    memory_dir: Path | None = None
    data_dir: Path | None = None

    # SQLite FTS5
    @property
    def sqlite_path(self) -> Path:
        return Path(str(self.data_dir)) / "kioku_fts.db"

    @property
    def chroma_collection(self) -> str:
        return "memories" if self.user_id == "default" else f"memories_{self.user_id}"

    @property
    def falkordb_graph(self) -> str:
        return "kioku_kg" if self.user_id == "default" else f"kioku_kg_{self.user_id}"

    # ChromaDB
    chroma_mode: str = "auto"  # "server", "embedded", or "auto" (try server → embedded → skip)
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    chroma_persist_dir: Path | None = None  # Default: ~/.kioku/data/chroma

    # FalkorDB (Phase 3)
    falkordb_host: str = "localhost"
    falkordb_port: int = 6379

    # Ollama (Phase 2)
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "bge-m3"

    # LLM (Phase 3)
    anthropic_api_key: str = ""

    model_config = {"env_prefix": "KIOKU_", "env_file": ".env", "extra": "ignore"}

    def model_post_init(self, __context) -> None:
        """Expand ~ in paths after loading from env."""
        base_dir = f"~/.kioku/users/{self.user_id}" if self.user_id != "default" else "~/.kioku"
        # Since pydantic might load "" or "." if we clear env vars, let's harden the check
        if not self.memory_dir or str(self.memory_dir) in ("", "."):
            object.__setattr__(self, "memory_dir", Path(os.path.expanduser(f"{base_dir}/memory")))
        else:
            object.__setattr__(self, "memory_dir", Path(os.path.expanduser(str(self.memory_dir))))

        if not self.data_dir or str(self.data_dir) in ("", "."):
            object.__setattr__(self, "data_dir", Path(os.path.expanduser(f"{base_dir}/data")))
        else:
            object.__setattr__(self, "data_dir", Path(os.path.expanduser(str(self.data_dir))))

        if not self.chroma_persist_dir or str(self.chroma_persist_dir) in ("", "."):
            object.__setattr__(
                self,
                "chroma_persist_dir",
                Path(os.path.expanduser(str(self.data_dir))) / "chroma",
            )
        else:
            object.__setattr__(
                self,
                "chroma_persist_dir",
                Path(os.path.expanduser(str(self.chroma_persist_dir))),
            )

    def ensure_dirs(self) -> None:
        """Create required directories if they don't exist."""
        if self.memory_dir:
            self.memory_dir.mkdir(parents=True, exist_ok=True)
        if self.data_dir:
            self.data_dir.mkdir(parents=True, exist_ok=True)


# Singleton
settings = Settings()
