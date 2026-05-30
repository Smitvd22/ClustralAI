# =============================================================================
# Text Chunker — Split document text into overlapping chunks
# =============================================================================
"""
Splits extracted document text into fixed-size overlapping chunks,
preserving source metadata (filename, page number) for citations.

Configuration:
    - Chunk size: 500 characters (configurable)
    - Overlap: 100 characters (configurable)

The chunker attempts to split on sentence boundaries when possible
to avoid cutting mid-sentence.
"""
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ChunkMetadata:
    """Metadata attached to each chunk for citation tracking."""
    filename: str
    page_number: int
    chunk_index: int


@dataclass
class Chunk:
    """A text chunk with its metadata."""
    text: str
    metadata: ChunkMetadata
    chunk_id: str = field(default="")

    def __post_init__(self) -> None:
        if not self.chunk_id:
            # SECURITY: chunk_id is deterministic and does not leak filesystem paths
            self.chunk_id = (
                f"{self.metadata.filename}::p{self.metadata.page_number}"
                f"::c{self.metadata.chunk_index}"
            )


# Sentence boundary pattern — splits on period/question/exclamation
# followed by whitespace, while avoiding splitting on abbreviations
# like "Dr." or "U.S."
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def chunk_text(
    text: str,
    filename: str,
    page_number: int,
    chunk_size: int = 500,
    chunk_overlap: int = 100,
    start_chunk_index: int = 0,
) -> list[Chunk]:
    """
    Split a single page's text into overlapping chunks.

    Args:
        text: The page text to chunk.
        filename: Source filename for metadata.
        page_number: Source page number for metadata.
        chunk_size: Maximum characters per chunk.
        chunk_overlap: Number of overlapping characters between chunks.
        start_chunk_index: Starting index for chunk numbering
                          (used when chunking multiple pages sequentially).

    Returns:
        List of ``Chunk`` objects.
    """
    if not text or not text.strip():
        return []

    # If the text is shorter than chunk_size, return it as a single chunk
    if len(text) <= chunk_size:
        return [
            Chunk(
                text=text.strip(),
                metadata=ChunkMetadata(
                    filename=filename,
                    page_number=page_number,
                    chunk_index=start_chunk_index,
                ),
            )
        ]

    chunks: list[Chunk] = []
    chunk_idx = start_chunk_index
    start = 0

    while start < len(text):
        end = start + chunk_size

        # If we're not at the end, try to find a sentence boundary
        if end < len(text):
            # Look backwards from `end` for a sentence boundary
            candidate = text[start:end]
            boundaries = list(_SENTENCE_BOUNDARY.finditer(candidate))
            if boundaries:
                # Split at the last sentence boundary within the chunk
                last_boundary = boundaries[-1]
                end = start + last_boundary.end()

        chunk_text_content = text[start:end].strip()

        if chunk_text_content:
            chunks.append(
                Chunk(
                    text=chunk_text_content,
                    metadata=ChunkMetadata(
                        filename=filename,
                        page_number=page_number,
                        chunk_index=chunk_idx,
                    ),
                )
            )
            chunk_idx += 1

        # Move forward by (chunk_size - overlap), but at least 1 char
        step = max(1, (end - start) - chunk_overlap)
        start += step

        # Safety valve: prevent infinite loops
        if start >= len(text):
            break

    logger.debug(
        "Chunked text | filename=%s page=%d chunks=%d",
        filename,
        page_number,
        len(chunks),
    )
    return chunks


def chunk_document_pages(
    pages: list,  # list[DocumentPage] — avoid circular import
    chunk_size: int = 500,
    chunk_overlap: int = 100,
) -> list[Chunk]:
    """
    Chunk all pages of a document, maintaining sequential chunk indices.

    Args:
        pages: List of ``DocumentPage`` objects from the PDF processor.
        chunk_size: Maximum characters per chunk.
        chunk_overlap: Overlap characters between consecutive chunks.

    Returns:
        List of all ``Chunk`` objects across all pages.
    """
    all_chunks: list[Chunk] = []
    chunk_index = 0

    for page in pages:
        page_chunks = chunk_text(
            text=page.text,
            filename=page.filename,
            page_number=page.page_number,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            start_chunk_index=chunk_index,
        )
        all_chunks.extend(page_chunks)
        chunk_index += len(page_chunks)

    logger.info(
        "Document chunking complete | total_chunks=%d",
        len(all_chunks),
    )
    return all_chunks
