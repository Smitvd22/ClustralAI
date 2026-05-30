# =============================================================================
# Ingest Router — POST /ingest
# =============================================================================
"""
Handles PDF document ingestion:
    1. Validate uploaded files (PDF only, size limits)
    2. Extract text from each PDF
    3. Chunk text with metadata
    4. Generate embeddings
    5. Store in ChromaDB vector store

SECURITY:
    - File type validation (PDF only)
    - File size limits
    - Rate limited
    - API key required
"""
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Request
from starlette import status

from app.config import Settings
from app.dependencies import get_settings, get_vector_store
from app.models import IngestResponse
from security.api_auth import verify_api_key
from security.rate_limiter import limiter
from rag.pdf_processor import extract_text_from_pdf, PDFProcessingError
from rag.chunker import chunk_document_pages
from rag.embeddings import embed_texts
from rag.vector_store import VectorStore
from security.pii_masker import mask_pii

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ingestion"])


@router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest PDF documents",
    description="Upload PDF files to extract, chunk, embed, and store in the vector database.",
)
@limiter.limit("5/minute")
async def ingest_documents(
    request: Request,
    files: list[UploadFile] = File(..., description="PDF files to ingest (max 10)"),
    api_key: str = Depends(verify_api_key),
    settings: Settings = Depends(get_settings),
    vector_store: VectorStore = Depends(get_vector_store),
) -> IngestResponse:
    """
    Ingest one or more PDF documents into the RAG system.

    Processes each file through the pipeline:
    extract → chunk → embed → store.
    """
    # ---------------------------------------------------------------
    # Validate number of files
    # ---------------------------------------------------------------
    if len(files) > settings.max_files_per_upload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {settings.max_files_per_upload} files per upload. Got {len(files)}.",
        )

    if len(files) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one PDF file is required.",
        )

    total_chunks = 0
    details: list[dict] = []
    max_bytes = settings.max_upload_size_mb * 1024 * 1024

    for upload_file in files:
        filename = upload_file.filename or "unknown.pdf"

        # ---------------------------------------------------------------
        # Validate file type
        # ---------------------------------------------------------------
        if not filename.lower().endswith(".pdf"):
            logger.warning("Rejected non-PDF file | filename=%s", filename)
            details.append({
                "filename": filename,
                "status": "rejected",
                "reason": "Only PDF files are accepted.",
                "chunks": 0,
            })
            continue

        # ---------------------------------------------------------------
        # Validate content type
        # ---------------------------------------------------------------
        content_type = upload_file.content_type or ""
        if content_type and content_type != "application/pdf":
            logger.warning(
                "Rejected file with wrong content type | filename=%s type=%s",
                filename,
                content_type,
            )
            details.append({
                "filename": filename,
                "status": "rejected",
                "reason": f"Invalid content type: {content_type}. Expected application/pdf.",
                "chunks": 0,
            })
            continue

        # ---------------------------------------------------------------
        # Read file content with size check
        # ---------------------------------------------------------------
        try:
            content = await upload_file.read()
        except Exception as exc:
            logger.error("Failed to read uploaded file | filename=%s error=%s", filename, exc)
            details.append({
                "filename": filename,
                "status": "error",
                "reason": "Failed to read file.",
                "chunks": 0,
            })
            continue

        if len(content) > max_bytes:
            logger.warning(
                "Rejected oversized file | filename=%s size_mb=%.1f max_mb=%d",
                filename,
                len(content) / (1024 * 1024),
                settings.max_upload_size_mb,
            )
            details.append({
                "filename": filename,
                "status": "rejected",
                "reason": f"File exceeds {settings.max_upload_size_mb} MB limit.",
                "chunks": 0,
            })
            continue

        # ---------------------------------------------------------------
        # Extract text
        # ---------------------------------------------------------------
        try:
            pages = extract_text_from_pdf(content, filename)
        except PDFProcessingError as exc:
            logger.error("PDF processing failed | filename=%s error=%s", filename, exc)
            details.append({
                "filename": filename,
                "status": "error",
                "reason": str(exc),
                "chunks": 0,
            })
            continue

        # ---------------------------------------------------------------
        # Chunk
        # ---------------------------------------------------------------
        chunks = chunk_document_pages(
            pages,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )

        if not chunks:
            details.append({
                "filename": filename,
                "status": "warning",
                "reason": "No chunks generated from document.",
                "chunks": 0,
            })
            continue

        # ---------------------------------------------------------------
        # Embed
        # ---------------------------------------------------------------
        try:
            texts = [c.text for c in chunks]
            embeddings = embed_texts(texts)
        except Exception as exc:
            logger.error("Embedding generation failed | filename=%s error=%s", filename, exc)
            details.append({
                "filename": filename,
                "status": "error",
                "reason": "Embedding generation failed.",
                "chunks": 0,
            })
            continue

        # ---------------------------------------------------------------
        # Store in vector database
        # ---------------------------------------------------------------
        ids = [c.chunk_id for c in chunks]
        metadatas = [
            {
                "filename": c.metadata.filename,
                "page_number": c.metadata.page_number,
                "chunk_index": c.metadata.chunk_index,
            }
            for c in chunks
        ]

        try:
            added = vector_store.add_documents(
                ids=ids,
                texts=texts,
                embeddings=embeddings,
                metadatas=metadatas,
            )
        except Exception as exc:
            logger.error("Vector store insertion failed | filename=%s error=%s", filename, exc)
            details.append({
                "filename": filename,
                "status": "error",
                "reason": "Failed to store in vector database.",
                "chunks": 0,
            })
            continue

        total_chunks += added
        # SECURITY: Do not log file content, only metadata
        logger.info(
            "File ingested | filename=%s pages=%d chunks=%d",
            filename,
            len(pages),
            added,
        )
        details.append({
            "filename": filename,
            "status": "success",
            "pages": len(pages),
            "chunks": added,
        })

    files_processed = sum(1 for d in details if d.get("status") == "success")
    overall_status = "success" if files_processed > 0 else "no_files_processed"

    return IngestResponse(
        status=overall_status,
        files_processed=files_processed,
        total_chunks=total_chunks,
        details=details,
    )
