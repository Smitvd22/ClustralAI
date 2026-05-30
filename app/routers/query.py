# =============================================================================
# Query Router — POST /query
# =============================================================================
"""
Handles user queries through the secured RAG pipeline.

SECURITY: All queries pass through the full security pipeline:
    Prompt Guard → Exfiltration Guard → Retrieval → Indirect Injection Check
    → LLM Generation → Output Filter → Response

Rate limited and API key authenticated.
"""
import logging

from fastapi import APIRouter, Depends, Request
from starlette import status

from app.dependencies import get_rag_pipeline
from app.models import QueryRequest, QueryResponse, CitationModel
from security.api_auth import verify_api_key
from security.rate_limiter import limiter
from rag.rag_pipeline import RAGPipeline

logger = logging.getLogger(__name__)

router = APIRouter(tags=["query"])


@router.post(
    "/query",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Query the RAG system",
    description="Submit a question to be answered using the ingested documents.",
)
@limiter.limit("10/minute")
async def query_documents(
    request: Request,
    body: QueryRequest,
    api_key: str = Depends(verify_api_key),
    rag_pipeline: RAGPipeline = Depends(get_rag_pipeline),
) -> QueryResponse:
    """
    Submit a question and receive an answer with source citations.

    The query passes through multiple security layers before reaching
    the LLM. Malicious queries are blocked with an explanation.
    """
    result = rag_pipeline.query(body.question)

    citations = [
        CitationModel(
            filename=c.filename,
            page_number=c.page_number,
            chunk_preview=c.chunk_preview,
        )
        for c in result.citations
    ]

    return QueryResponse(
        answer=result.answer,
        citations=citations,
        blocked=result.blocked,
        block_reason=result.block_reason,
    )
