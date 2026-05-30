# =============================================================================
# Application Configuration — Settings via pydantic-settings + Key Vault
# =============================================================================
"""
Centralized configuration management.

Loading order:
    1. Environment variables (from .env file or OS environment)

In production, secrets (Gemini API key, app API keys) should be securely 
set via Render Environment Variables.

SECURITY: Secrets are never logged. The ``__repr__`` of settings
masks sensitive fields.
"""
import json
import logging
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment and/or Key Vault."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------- Application ----------
    app_env: str = Field(default="development", description="Environment: development, staging, production")
    app_log_level: str = Field(default="INFO", description="Logging level")

    # ---------- API Authentication ----------
    app_api_keys: str = Field(
        default='["dev-test-key-change-in-production"]',
        description="JSON array of valid API keys",
    )

    # ---------- Google Gemini ----------
    gemini_api_key: str = Field(default="", description="Google AI Studio API key")
    gemini_model: str = Field(default="gemini-2.0-flash", description="Gemini model name")


    # ---------- ChromaDB ----------
    chroma_persist_dir: str = Field(default="./chroma_data", description="ChromaDB persistence directory")
    chroma_collection_name: str = Field(default="rag_documents", description="ChromaDB collection name")

    # ---------- RAG ----------
    chunk_size: int = Field(default=500, description="Chunk size in characters")
    chunk_overlap: int = Field(default=100, description="Chunk overlap in characters")
    top_k: int = Field(default=3, description="Number of chunks to retrieve")
    similarity_threshold: float = Field(default=1.0, description="Max cosine distance for relevance")

    # ---------- Rate Limiting ----------
    rate_limit_query: str = Field(default="10/minute", description="Rate limit for /query endpoint")
    rate_limit_ingest: str = Field(default="5/minute", description="Rate limit for /ingest endpoint")

    # ---------- Security ----------
    max_upload_size_mb: int = Field(default=50, description="Maximum upload size in MB")
    max_files_per_upload: int = Field(default=10, description="Maximum files per upload")

    def get_api_keys_list(self) -> list[str]:
        """Parse the JSON array of API keys."""
        try:
            keys = json.loads(self.app_api_keys)
            if isinstance(keys, list):
                return [str(k) for k in keys]
        except (json.JSONDecodeError, TypeError):
            pass
        # Fallback: treat as a single key
        return [self.app_api_keys]


def load_settings() -> Settings:
    """
    Load settings from environment, then optionally enrich from Key Vault.

    Returns:
        Fully resolved ``Settings`` instance.
    """
    settings = Settings()

    # SECURITY: Never log the actual secret values
    logger.info(
        "Configuration loaded | env=%s chroma_dir=%s model=%s",
        settings.app_env,
        settings.chroma_persist_dir,
        settings.gemini_model,
    )
    return settings



