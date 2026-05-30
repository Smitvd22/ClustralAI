# =============================================================================
# Test: Normal RAG Queries
# =============================================================================
"""
Tests for normal RAG query functionality:
    - PDF ingestion
    - Document retrieval quality
    - Citation accuracy

These tests verify the happy path — that the system correctly ingests
PDFs and returns accurate, cited answers.
"""
import pytest
from rag.pdf_processor import extract_text_from_pdf
from rag.chunker import chunk_document_pages, chunk_text
from rag.embeddings import embed_texts, embed_query


class TestPDFProcessing:
    """Tests for PDF text extraction."""

    def test_extracts_text_from_pdf(self, sample_pdf_bytes: bytes) -> None:
        """Verify text extraction from a valid PDF."""
        pages = extract_text_from_pdf(sample_pdf_bytes, "test.pdf")
        assert len(pages) >= 1
        assert all(page.filename == "test.pdf" for page in pages)
        assert all(page.page_number >= 1 for page in pages)
        assert any("refund" in page.text.lower() for page in pages)

    def test_rejects_invalid_pdf(self) -> None:
        """Verify that non-PDF content is rejected."""
        from rag.pdf_processor import PDFProcessingError
        with pytest.raises(PDFProcessingError):
            extract_text_from_pdf(b"This is not a PDF", "fake.pdf")

    def test_preserves_page_numbers(self, sample_pdf_bytes: bytes) -> None:
        """Verify that page numbers are correctly tracked."""
        pages = extract_text_from_pdf(sample_pdf_bytes, "test.pdf")
        page_numbers = [p.page_number for p in pages]
        assert page_numbers == sorted(page_numbers)
        assert page_numbers[0] == 1


class TestChunking:
    """Tests for text chunking."""

    def test_chunks_text_with_overlap(self) -> None:
        """Verify chunking with correct size and overlap."""
        long_text = "Word " * 200  # ~1000 characters
        chunks = chunk_text(
            text=long_text,
            filename="test.pdf",
            page_number=1,
            chunk_size=500,
            chunk_overlap=100,
        )
        assert len(chunks) >= 2
        # Verify metadata
        for chunk in chunks:
            assert chunk.metadata.filename == "test.pdf"
            assert chunk.metadata.page_number == 1
            assert len(chunk.text) <= 500

    def test_short_text_single_chunk(self) -> None:
        """Verify that short text produces a single chunk."""
        short_text = "This is a short sentence."
        chunks = chunk_text(
            text=short_text,
            filename="test.pdf",
            page_number=1,
        )
        assert len(chunks) == 1
        assert chunks[0].text == short_text

    def test_chunk_ids_are_unique(self) -> None:
        """Verify that chunk IDs are unique."""
        text = "Content " * 200
        chunks = chunk_text(text, "test.pdf", 1, chunk_size=100, chunk_overlap=20)
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_chunks_preserve_metadata(self, sample_pdf_bytes: bytes) -> None:
        """Verify metadata is preserved through the chunking pipeline."""
        pages = extract_text_from_pdf(sample_pdf_bytes, "handbook.pdf")
        chunks = chunk_document_pages(pages, chunk_size=500, chunk_overlap=100)
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.metadata.filename == "handbook.pdf"
            assert chunk.metadata.page_number >= 1


class TestEmbeddings:
    """Tests for embedding generation."""

    def test_embed_single_text(self) -> None:
        """Verify single text embedding has correct dimension."""
        embedding = embed_query("Test query")
        assert len(embedding) == 384
        assert all(isinstance(v, float) for v in embedding)

    def test_embed_batch(self) -> None:
        """Verify batch embedding produces correct number of vectors."""
        texts = ["First text", "Second text", "Third text"]
        embeddings = embed_texts(texts)
        assert len(embeddings) == 3
        assert all(len(e) == 384 for e in embeddings)

    def test_similar_texts_have_close_embeddings(self) -> None:
        """Verify semantically similar texts produce close embeddings."""
        import numpy as np

        e1 = embed_query("What is the refund policy?")
        e2 = embed_query("How do I get a refund?")
        e3 = embed_query("What is quantum physics?")

        # Cosine similarity
        sim_related = np.dot(e1, e2) / (np.linalg.norm(e1) * np.linalg.norm(e2))
        sim_unrelated = np.dot(e1, e3) / (np.linalg.norm(e1) * np.linalg.norm(e3))

        assert sim_related > sim_unrelated, (
            f"Related similarity ({sim_related:.4f}) should be > "
            f"unrelated similarity ({sim_unrelated:.4f})"
        )


class TestVectorStoreOperations:
    """Tests for vector store CRUD operations."""

    def test_add_and_query(self, temp_vector_store) -> None:
        """Verify documents can be added and queried."""
        texts = [
            "The refund policy allows returns within 30 days.",
            "Employees get 15 days of paid time off.",
            "Passwords must be at least 12 characters.",
        ]
        embeddings = embed_texts(texts)
        metadatas = [
            {"filename": "handbook.pdf", "page_number": 1, "chunk_index": 0},
            {"filename": "handbook.pdf", "page_number": 2, "chunk_index": 1},
            {"filename": "handbook.pdf", "page_number": 3, "chunk_index": 2},
        ]
        ids = ["chunk_0", "chunk_1", "chunk_2"]

        temp_vector_store.add_documents(ids, texts, embeddings, metadatas)
        assert temp_vector_store.get_document_count() == 3

        # Query for refund-related content
        query_emb = embed_query("What is the refund policy?")
        results = temp_vector_store.query(query_emb, top_k=1)

        assert len(results["ids"][0]) == 1
        assert "refund" in results["documents"][0][0].lower()


class TestIngestionEndpoint:
    """Tests for the /ingest API endpoint."""

    def test_ingest_pdf(
        self, client, auth_headers: dict, sample_pdf_bytes: bytes
    ) -> None:
        """Verify PDF ingestion via the API."""
        import io
        response = client.post(
            "/ingest",
            files=[("files", ("test_handbook.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf"))],
            headers=auth_headers,
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == "success"
        assert data["files_processed"] == 1
        assert data["total_chunks"] > 0

    def test_rejects_non_pdf(
        self, client, auth_headers: dict
    ) -> None:
        """Verify non-PDF files are rejected."""
        response = client.post(
            "/ingest",
            files=[("files", ("test.txt", b"Not a PDF", "text/plain"))],
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["files_processed"] == 0
