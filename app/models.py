# =============================================================================
# Pydantic Models — Request / Response schemas
# =============================================================================
"""
Request and response models for the API endpoints.

All models use Pydantic v2 for validation and serialization.
"""
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    """Request body for POST /query."""
    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The question to answer from ingested documents.",
        examples=["What is the refund policy?"],
    )


class CitationModel(BaseModel):
    """A source citation in a query response."""
    filename: str = Field(..., description="Source document filename.")
    page_number: int = Field(..., description="Page number in the source document.")
    chunk_preview: str = Field(
        default="",
        description="Preview of the relevant text chunk.",
    )


class QueryResponse(BaseModel):
    """Response body for POST /query."""
    answer: str = Field(..., description="The generated answer.")
    citations: list[CitationModel] = Field(
        default_factory=list,
        description="Source citations for the answer.",
    )
    blocked: bool = Field(
        default=False,
        description="Whether the request was blocked by security filters.",
    )
    block_reason: str = Field(
        default="",
        description="Reason for blocking, if applicable.",
    )


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------

class IngestResponse(BaseModel):
    """Response body for POST /ingest."""
    status: str = Field(..., description="Ingestion status.")
    files_processed: int = Field(..., description="Number of PDF files processed.")
    total_chunks: int = Field(..., description="Total chunks created and stored.")
    details: list[dict] = Field(
        default_factory=list,
        description="Per-file processing details.",
    )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class ComponentHealth(BaseModel):
    """Health status of a single component."""
    name: str
    status: str  # "healthy" or "unhealthy"
    details: str = ""


class HealthResponse(BaseModel):
    """Response body for GET /health."""
    status: str = Field(..., description="Overall system status.")
    components: list[ComponentHealth] = Field(
        default_factory=list,
        description="Individual component health statuses.",
    )


# ---------------------------------------------------------------------------
# Security Status
# ---------------------------------------------------------------------------

class SecurityFeature(BaseModel):
    """Status of a single security feature."""
    name: str
    enabled: bool
    description: str


class SecurityStatusResponse(BaseModel):
    """Response body for GET /security-status."""
    overall_status: str = Field(..., description="Overall security posture.")
    features: list[SecurityFeature] = Field(
        default_factory=list,
        description="Individual security feature statuses.",
    )
