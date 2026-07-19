"""Application settings, loaded from environment / .env.

All settings are prefixed with ``MAESTRO_`` (see .env.example).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MAESTRO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Async SQLAlchemy URL. Default is a file-based SQLite DB in the backend dir.
    database_url: str = "sqlite+aiosqlite:///./maestro.db"

    # Ollama server the agents talk to.
    ollama_host: str = "http://localhost:11434"

    # Sandbox root for the shared filesystem tool. Confines all read/write ops.
    workspace_dir: Path = BACKEND_DIR / "workspace"

    # Max agents running concurrently (README: 2 concurrent Ollama models).
    max_concurrent_runs: int = 2

    # Allowed CORS origins for the local frontend.
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    # Create tables via SQLModel metadata on startup (dev convenience; use Alembic in prod).
    auto_create_tables: bool = True

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
