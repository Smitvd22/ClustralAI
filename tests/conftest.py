# =============================================================================
# Test Configuration — Fixtures and helpers
# =============================================================================
"""
Shared pytest fixtures for the Security-First RAG test suite.

Provides:
    - FastAPI TestClient with mocked dependencies
    - Sample PDF generation
    - Temporary ChromaDB instances
    - Mock LLM responses
"""
import io
import os
import tempfile
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Set test environment before importing app modules
os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("GEMINI_API_KEY", "test-key-not-real")
os.environ.setdefault("APP_API_KEYS", '["test-api-key-12345"]')
os.environ.setdefault("CHROMA_PERSIST_DIR", "./test_chroma_data")
os.environ.setdefault("RATE_LIMIT_QUERY", "1000/minute")
os.environ.setdefault("RATE_LIMIT_INGEST", "1000/minute")

from app.main import app
from app.dependencies import init_services, _vector_store
from app.config import Settings
from security.api_auth import configure_api_keys
from rag.vector_store import VectorStore


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TEST_API_KEY = "test-api-key-12345"
AUTH_HEADER = {"X-API-Key": TEST_API_KEY}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def _setup_api_keys() -> None:
    """Configure test API keys once for the entire test session."""
    configure_api_keys([TEST_API_KEY])


@pytest.fixture()
def client(_setup_api_keys: None) -> Generator[TestClient, None, None]:
    """
    FastAPI test client with the application fully initialized.

    Uses a temporary ChromaDB directory for test isolation.
    """
    from security.rate_limiter import limiter
    limiter.enabled = False
    with TestClient(app) as test_client:
        yield test_client
    limiter.enabled = True


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    """Standard authentication headers for test requests."""
    return AUTH_HEADER.copy()


@pytest.fixture()
def sample_pdf_bytes() -> bytes:
    """
    Generate a simple PDF in memory for testing.

    Uses fpdf2 to create a PDF with known content that can be
    used to verify retrieval quality.
    """
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Page 1: Company policies
    pdf.add_page()
    pdf.set_font("Helvetica", size=16)
    pdf.cell(0, 10, "Acme Corp Employee Handbook", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 8, (
        "Chapter 1: Refund Policy\n\n"
        "All products purchased from Acme Corp are eligible for a full refund "
        "within 30 days of purchase. To request a refund, customers must provide "
        "their original receipt and the product must be in its original packaging. "
        "Refunds are processed within 5-7 business days after approval. "
        "Digital products are non-refundable after download. "
        "Subscription services can be cancelled at any time with a prorated refund."
    ))

    # Page 2: Security policies
    pdf.add_page()
    pdf.set_font("Helvetica", size=16)
    pdf.cell(0, 10, "Chapter 2: Data Security Policy", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 8, (
        "All employee data must be encrypted at rest and in transit. "
        "Access to customer data requires manager approval and is logged. "
        "Passwords must be at least 12 characters with uppercase, lowercase, "
        "numbers, and special characters. Multi-factor authentication is required "
        "for all systems. Data retention period is 7 years for financial records "
        "and 3 years for general correspondence."
    ))

    # Page 3: Leave policy
    pdf.add_page()
    pdf.set_font("Helvetica", size=16)
    pdf.cell(0, 10, "Chapter 3: Leave Policy", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 8, (
        "Full-time employees receive 15 days of paid time off per year. "
        "Sick leave is provided at 10 days per year and does not roll over. "
        "Parental leave is 12 weeks paid for primary caregivers and 4 weeks "
        "for secondary caregivers. Employees must submit leave requests at "
        "least 2 weeks in advance for planned absences."
    ))

    return pdf.output()


@pytest.fixture()
def sample_pdf_file(sample_pdf_bytes: bytes) -> io.BytesIO:
    """Return sample PDF as a file-like object for upload testing."""
    file = io.BytesIO(sample_pdf_bytes)
    file.name = "test_handbook.pdf"
    return file


@pytest.fixture()
def temp_vector_store() -> Generator[VectorStore, None, None]:
    """Create a temporary vector store for isolated testing."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        store = VectorStore(
            persist_dir=tmpdir,
            collection_name="test_collection",
        )
        store.initialize()
        yield store
