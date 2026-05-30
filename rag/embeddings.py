# =============================================================================
# Embeddings — sentence-transformers / all-MiniLM-L6-v2
# =============================================================================
"""
Embedding service using the ``all-MiniLM-L6-v2`` model from sentence-transformers.

The model is loaded once at application startup (singleton pattern) and
reused for all embedding requests.

Model details:
    - Dimensions: 384
    - Size: ~80 MB
    - Speed: Fast (suitable for free-tier CPU)
    - Quality: Good general-purpose semantic similarity

SECURITY: The model runs locally — no data is sent to external services
for embedding generation.
"""
import logging
from typing import Optional

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton model instance
# ---------------------------------------------------------------------------
_model: Optional[SentenceTransformer] = None

MODEL_NAME: str = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION: int = 384


def get_model() -> SentenceTransformer:
    """
    Get or lazily load the sentence-transformer model.

    Returns:
        The loaded ``SentenceTransformer`` model instance.

    Note:
        First call downloads/loads the model (~80 MB). Subsequent calls
        return the cached instance.
    """
    global _model
    if _model is None:
        logger.info("Loading embedding model: %s", MODEL_NAME)
        _model = SentenceTransformer(MODEL_NAME)
        logger.info("Embedding model loaded successfully | dim=%d", EMBEDDING_DIMENSION)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a batch of texts.

    Args:
        texts: List of text strings to embed.

    Returns:
        List of embedding vectors (each a list of floats with length 384).
    """
    if not texts:
        return []

    model = get_model()
    embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)

    # Convert numpy arrays to plain lists for JSON serialization / ChromaDB
    result = [emb.tolist() for emb in embeddings]

    logger.debug("Generated embeddings | count=%d dim=%d", len(result), len(result[0]))
    return result


def embed_query(query: str) -> list[float]:
    """
    Generate an embedding for a single query string.

    Args:
        query: The search query to embed.

    Returns:
        Embedding vector as a list of floats.
    """
    model = get_model()
    embedding = model.encode(query, show_progress_bar=False, convert_to_numpy=True)
    return embedding.tolist()


def warmup() -> None:
    """
    Pre-load the model at application startup.

    Call this during the FastAPI lifespan to avoid cold-start latency
    on the first request.
    """
    get_model()
    logger.info("Embedding model warmup complete")
