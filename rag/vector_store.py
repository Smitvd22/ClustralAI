# =============================================================================
# Vector Store — ChromaDB persistent storage
# =============================================================================
"""
ChromaDB vector store for document chunk storage and retrieval.

Uses ``PersistentClient`` to store data on disk (or mounted Azure File Share
in production).

SECURITY: The vector store is a local component — no network access
required. Data at rest is protected by filesystem permissions and
Azure File Share encryption.
"""
import logging
from typing import Any, Optional

import chromadb

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Wrapper around ChromaDB for document chunk storage and retrieval.

    Args:
        persist_dir: Directory path for persistent storage.
        collection_name: Name of the ChromaDB collection.
    """

    def __init__(
        self,
        persist_dir: str = "./chroma_data",
        collection_name: str = "rag_documents",
    ) -> None:
        self._persist_dir = persist_dir
        self._collection_name = collection_name
        self._client: Optional[chromadb.ClientAPI] = None
        self._collection: Optional[chromadb.Collection] = None

    def initialize(self) -> None:
        """
        Initialize the ChromaDB client and collection.

        Call this during application startup.
        """
        logger.info(
            "Initializing ChromaDB | persist_dir=%s collection=%s",
            self._persist_dir,
            self._collection_name,
        )
        self._client = chromadb.PersistentClient(path=self._persist_dir)
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},  # Use cosine similarity
        )
        logger.info(
            "ChromaDB initialized | existing_documents=%d",
            self._collection.count(),
        )

    @property
    def collection(self) -> chromadb.Collection:
        """Get the active collection, raising if not initialized."""
        if self._collection is None:
            raise RuntimeError("VectorStore not initialized. Call initialize() first.")
        return self._collection

    def add_documents(
        self,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> int:
        """
        Add document chunks to the vector store.

        Args:
            ids: Unique identifiers for each chunk.
            texts: The chunk text content.
            embeddings: Pre-computed embeddings for each chunk.
            metadatas: Metadata dicts (filename, page_number, chunk_index).

        Returns:
            Number of documents added.
        """
        if not ids:
            return 0

        # ChromaDB has a batch size limit; process in batches of 500
        batch_size = 500
        total_added = 0

        for i in range(0, len(ids), batch_size):
            batch_end = min(i + batch_size, len(ids))
            self.collection.add(
                ids=ids[i:batch_end],
                documents=texts[i:batch_end],
                embeddings=embeddings[i:batch_end],
                metadatas=metadatas[i:batch_end],
            )
            total_added += batch_end - i

        logger.info(
            "Documents added to vector store | count=%d total_in_collection=%d",
            total_added,
            self.collection.count(),
        )
        return total_added

    def query(
        self,
        query_embedding: list[float],
        top_k: int = 3,
    ) -> dict[str, Any]:
        """
        Query the vector store for similar documents.

        Args:
            query_embedding: The query embedding vector.
            top_k: Number of results to return.

        Returns:
            ChromaDB query result dict with keys:
            ``ids``, ``documents``, ``metadatas``, ``distances``.

        Note:
            Distances are cosine distances (0 = identical, 2 = opposite).
            Lower is more similar.
        """
        if self.collection.count() == 0:
            logger.warning("Query on empty collection — no documents ingested")
            return {
                "ids": [[]],
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[]],
            }

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self.collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        logger.debug(
            "Vector store query | top_k=%d results=%d",
            top_k,
            len(results["ids"][0]) if results["ids"] else 0,
        )
        return results

    def get_document_count(self) -> int:
        """Return the total number of chunks in the collection."""
        return self.collection.count()

    def is_healthy(self) -> bool:
        """Check if the vector store is operational."""
        try:
            _ = self.collection.count()
            return True
        except Exception:
            return False

    def clear(self) -> None:
        """
        Delete all documents from the collection.

        SECURITY: This is a destructive operation. Only used in testing
        and administrative contexts.
        """
        if self._client is not None:
            self._client.delete_collection(self._collection_name)
            self._collection = self._client.get_or_create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.warning("Vector store CLEARED — all documents deleted")
