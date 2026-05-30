# =============================================================================
# Retriever — Similarity search with threshold-based out-of-scope detection
# =============================================================================
"""
Retrieves relevant document chunks from the vector store and determines
whether the query is answerable from the available documents.

Key features:
    - Top-K retrieval (default K=3)
    - Cosine distance threshold for out-of-scope detection
    - Citation formatting from chunk metadata

SECURITY: The similarity threshold prevents hallucination by refusing
to answer when no relevant documents are found.
"""
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """A single retrieved chunk with its relevance score and metadata."""
    text: str
    filename: str
    page_number: int
    chunk_index: int
    distance: float  # Cosine distance (lower = more similar)


@dataclass
class RetrievalResult:
    """Result of a retrieval operation."""
    is_answerable: bool
    chunks: list[RetrievedChunk] = field(default_factory=list)
    reason: str = ""


# SECURITY: Cosine distance threshold. Chunks with distance above this
# are considered irrelevant. ChromaDB cosine distance range: [0, 2].
# 0 = identical, 1 = orthogonal, 2 = opposite.
# A threshold of 1.0 means we reject chunks that are orthogonal or worse.
# This value can be tuned based on the embedding model and domain.
DEFAULT_SIMILARITY_THRESHOLD: float = 1.0


def retrieve_relevant_chunks(
    vector_store: "VectorStore",  # type: ignore[name-defined]
    query_embedding: list[float],
    top_k: int = 3,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> RetrievalResult:
    """
    Retrieve the most relevant document chunks for a query.

    Args:
        vector_store: The initialized ``VectorStore`` instance.
        query_embedding: The query's embedding vector.
        top_k: Number of chunks to retrieve.
        similarity_threshold: Maximum cosine distance for relevance.

    Returns:
        A ``RetrievalResult`` indicating answerability and retrieved chunks.
    """
    results = vector_store.query(query_embedding, top_k=top_k)

    if not results["ids"][0]:
        logger.info("No documents in vector store — query is unanswerable")
        return RetrievalResult(
            is_answerable=False,
            reason="No documents have been ingested yet.",
        )

    chunks: list[RetrievedChunk] = []
    for idx, doc_id in enumerate(results["ids"][0]):
        distance = results["distances"][0][idx]
        metadata = results["metadatas"][0][idx]
        text = results["documents"][0][idx]

        # SECURITY: Skip chunks that are below the similarity threshold
        if distance > similarity_threshold:
            logger.debug(
                "Chunk below threshold | id=%s distance=%.4f threshold=%.4f",
                doc_id,
                distance,
                similarity_threshold,
            )
            continue

        chunks.append(
            RetrievedChunk(
                text=text,
                filename=metadata.get("filename", "unknown"),
                page_number=int(metadata.get("page_number", 0)),
                chunk_index=int(metadata.get("chunk_index", 0)),
                distance=distance,
            )
        )

    if not chunks:
        logger.info(
            "All retrieved chunks below similarity threshold — out of scope"
        )
        return RetrievalResult(
            is_answerable=False,
            reason="I cannot answer that based on the provided documents.",
        )

    logger.info(
        "Retrieved %d relevant chunks | best_distance=%.4f",
        len(chunks),
        chunks[0].distance if chunks else -1,
    )

    return RetrievalResult(is_answerable=True, chunks=chunks)


def format_context_for_llm(chunks: list[RetrievedChunk]) -> str:
    """
    Format retrieved chunks into a context string for the LLM prompt.

    Each chunk is wrapped in delimiters with source attribution to
    enable the LLM to produce accurate citations.
    """
    context_parts: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(
            f"[Source {i}: {chunk.filename}, Page {chunk.page_number}]\n"
            f"{chunk.text}\n"
            f"[End Source {i}]"
        )
    return "\n\n".join(context_parts)
