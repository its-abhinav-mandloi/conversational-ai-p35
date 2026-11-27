"""Environment-safe application configuration for Agricultural Knowledge Navigator."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Typed configuration loaded from environment variables or defaults.

    Never embeds or logs secrets. Optional LLM providers remain safely disabled
    unless explicitly enabled and backed by valid credentials/endpoints.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_mode: Literal["local-only", "openai", "ollama"] = Field(
        default="local-only",
        validation_alias="AGRI_LLM_MODE",
    )
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", validation_alias="OPENAI_MODEL")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias="OPENAI_BASE_URL",
    )
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        validation_alias="OLLAMA_BASE_URL",
    )
    ollama_model: str = Field(default="llama3.2", validation_alias="OLLAMA_MODEL")

    embedding_backend: Literal["sentence-transformers", "hashed-local"] = Field(
        default="sentence-transformers",
        validation_alias="AGRI_EMBEDDING_BACKEND",
    )
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        validation_alias="AGRI_EMBEDDING_MODEL",
    )
    chroma_dir: Path = Field(
        default=PROJECT_ROOT / "data" / "processed" / "chroma_db",
        validation_alias="AGRI_CHROMA_DIR",
    )
    sqlite_path: Path = Field(
        default=PROJECT_ROOT / "data" / "processed" / "agri_navigator.db",
        validation_alias="AGRI_SQLITE_PATH",
    )
    raw_docs_dir: Path = Field(
        default=PROJECT_ROOT / "data" / "raw",
        validation_alias="AGRI_RAW_DOCS_DIR",
    )
    top_k: int = Field(default=4, ge=1, le=10, validation_alias="AGRI_TOP_K")
    min_similarity: float = Field(
        default=0.32,
        ge=0.0,
        le=1.0,
        validation_alias="AGRI_MIN_SIMILARITY",
    )
    max_history_turns: int = Field(
        default=10,
        ge=1,
        le=50,
        validation_alias="AGRI_MAX_HISTORY_TURNS",
    )
    log_level: str = Field(default="INFO", validation_alias="AGRI_LOG_LEVEL")

    def resolved_path(self, path: Path) -> Path:
        """Resolve relative configured paths against the repository root."""
        return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def get_settings() -> Settings:
    """Return fresh settings instance reflecting current environment variables."""
    return Settings()
