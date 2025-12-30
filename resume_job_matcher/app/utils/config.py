from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env file path relative to this file's directory
_ENV_FILE = Path(__file__).parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_prefix: str = ""
    data_dir: Path = Path("data")
    embeddings_dir: Path = Path("embeddings")

    gemini_api_key: str | None = None
    gemini_base_url: str = "https://generativelanguage.googleapis.com"
    gemini_embedding_model: str = "text-embedding-004"
    # Generation model: switched to gemini-1.5-flash for better quota availability.
    # Can be overridden via GEMINI_GENERATION_MODEL env variable.
    # Options: gemini-1.5-flash, gemini-1.5-pro, gemini-2.0-flash-lite, gemini-2.5-flash-lite
    gemini_generation_model: str = "gemini-1.5-flash"

    # Scoring weights (must sum to 1.0)
    semantic_weight: float = 0.65
    skill_weight: float = 0.35


settings = Settings()


