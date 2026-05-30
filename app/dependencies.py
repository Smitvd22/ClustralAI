# =============================================================================
# Dependencies — Dependency injection for FastAPI
# =============================================================================
"""
Provides singleton service instances to FastAPI route handlers via
dependency injection.

Services are initialized at application startup (see ``app.main``)
and stored in module-level variables. FastAPI ``Depends()`` functions
return the pre-initialized instances.
"""
import logging
from typing import Optional

from app.config import Settings
from rag.vector_store import VectorStore
from rag.llm_client import LLMClient
from rag.rag_pipeline import RAGPipeline

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level singletons (set during app startup)
# ---------------------------------------------------------------------------
_settings: Optional[Settings] = None
_vector_store: Optional[VectorStore] = None
_llm_client: Optional[LLMClient] = None
_rag_pipeline: Optional[RAGPipeline] = None


def init_services(settings: Settings) -> None:
    """
    Initialize all service singletons.

    Called once during FastAPI lifespan startup.
    """
    global _settings, _vector_store, _llm_client, _rag_pipeline

    _settings = settings

    # Initialize vector store
    _vector_store = VectorStore(
        persist_dir=settings.chroma_persist_dir,
        collection_name=settings.chroma_collection_name,
    )
    _vector_store.initialize()

    # Initialize LLM client
    _llm_client = LLMClient(
        api_key=settings.gemini_api_key,
        model_name=settings.gemini_model,
    )

    # Initialize RAG pipeline
    _rag_pipeline = RAGPipeline(
        vector_store=_vector_store,
        llm_client=_llm_client,
        top_k=settings.top_k,
        similarity_threshold=settings.similarity_threshold,
    )

    logger.info("All services initialized successfully")


# ---------------------------------------------------------------------------
# FastAPI dependency functions
# ---------------------------------------------------------------------------

def get_settings() -> Settings:
    """Get the application settings."""
    if _settings is None:
        raise RuntimeError("Settings not initialized")
    return _settings


def get_vector_store() -> VectorStore:
    """Get the initialized vector store."""
    if _vector_store is None:
        raise RuntimeError("VectorStore not initialized")
    return _vector_store


def get_llm_client() -> LLMClient:
    """Get the initialized LLM client."""
    if _llm_client is None:
        raise RuntimeError("LLMClient not initialized")
    return _llm_client


def get_rag_pipeline() -> RAGPipeline:
    """Get the initialized RAG pipeline."""
    if _rag_pipeline is None:
        raise RuntimeError("RAGPipeline not initialized")
    return _rag_pipeline
