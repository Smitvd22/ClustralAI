# =============================================================================
# PDF Processor — Extract text from PDF documents
# =============================================================================
"""
Extracts text from PDF files using PyMuPDF (fitz), preserving page numbers
and source filenames for citation tracking.

SECURITY: Only processes valid PDF files. Rejects non-PDF content
to prevent file-type confusion attacks.
"""
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


@dataclass
class DocumentPage:
    """A single page of extracted text with metadata."""
    text: str
    page_number: int  # 1-indexed for human-readable citations
    filename: str


class PDFProcessingError(Exception):
    """Raised when a PDF cannot be processed."""
    pass


def extract_text_from_pdf(
    file_content: bytes,
    filename: str,
) -> list[DocumentPage]:
    """
    Extract text from a PDF file, one ``DocumentPage`` per page.

    Args:
        file_content: Raw PDF bytes.
        filename: Original filename for metadata tracking.

    Returns:
        List of ``DocumentPage`` objects, one per non-empty page.

    Raises:
        PDFProcessingError: If the file is not a valid PDF or cannot be read.
    """
    pages: list[DocumentPage] = []

    try:
        doc = fitz.open(stream=file_content, filetype="pdf")
    except Exception as exc:
        logger.error("Failed to open PDF | filename=%s error=%s", filename, exc)
        raise PDFProcessingError(f"Cannot open '{filename}' as PDF: {exc}") from exc

    try:
        if doc.page_count == 0:
            logger.warning("PDF has zero pages | filename=%s", filename)
            raise PDFProcessingError(f"PDF '{filename}' contains no pages.")

        for page_idx in range(doc.page_count):
            page = doc.load_page(page_idx)
            text = page.get_text("text")

            # Skip pages with no extractable text
            cleaned = text.strip()
            if not cleaned:
                logger.debug(
                    "Skipping empty page | filename=%s page=%d",
                    filename,
                    page_idx + 1,
                )
                continue

            pages.append(
                DocumentPage(
                    text=cleaned,
                    page_number=page_idx + 1,  # 1-indexed
                    filename=filename,
                )
            )

        logger.info(
            "PDF processed | filename=%s total_pages=%d extracted_pages=%d",
            filename,
            doc.page_count,
            len(pages),
        )
    finally:
        doc.close()

    if not pages:
        raise PDFProcessingError(
            f"No extractable text found in '{filename}'. "
            "The PDF may contain only images or scanned content."
        )

    return pages


def extract_text_from_pdf_path(filepath: Path) -> list[DocumentPage]:
    """
    Convenience wrapper that reads a PDF from disk.

    Args:
        filepath: Path to the PDF file.

    Returns:
        List of ``DocumentPage`` objects.
    """
    if not filepath.exists():
        raise PDFProcessingError(f"File not found: {filepath}")
    if not filepath.suffix.lower() == ".pdf":
        raise PDFProcessingError(f"Not a PDF file: {filepath}")

    content = filepath.read_bytes()
    return extract_text_from_pdf(content, filepath.name)
