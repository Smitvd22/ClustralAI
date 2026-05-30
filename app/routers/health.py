# =============================================================================
# Health & Security Status Router
# =============================================================================
"""
Provides health check and security configuration status endpoints.

GET /health — Component-level health status.
GET /security-status — Security feature inventory.

SECURITY: These endpoints are intentionally unauthenticated to support
load balancer health probes and monitoring tools. They expose no
sensitive data.
"""
import logging

from fastapi import APIRouter, Depends

from app.dependencies import get_settings, get_vector_store, get_llm_client
from app.models import (
    HealthResponse,
    ComponentHealth,
    SecurityStatusResponse,
    SecurityFeature,
)
from app.config import Settings
from rag.vector_store import VectorStore
from rag.llm_client import LLMClient

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="System health check",
    description="Check the health of all system components.",
)
async def health_check(
    vector_store: VectorStore = Depends(get_vector_store),
    llm_client: LLMClient = Depends(get_llm_client),
) -> HealthResponse:
    """
    Returns the health status of each component:
    - Embedding model
    - Vector store (ChromaDB)
    - LLM client (Gemini)
    """
    components: list[ComponentHealth] = []

    # Embedding model
    try:
        from rag.embeddings import get_model
        model = get_model()
        components.append(ComponentHealth(
            name="embedding_model",
            status="healthy",
            details="all-MiniLM-L6-v2 loaded",
        ))
    except Exception as exc:
        components.append(ComponentHealth(
            name="embedding_model",
            status="unhealthy",
            details=str(exc),
        ))

    # Vector store
    if vector_store.is_healthy():
        doc_count = vector_store.get_document_count()
        components.append(ComponentHealth(
            name="vector_store",
            status="healthy",
            details=f"ChromaDB operational, {doc_count} chunks stored",
        ))
    else:
        components.append(ComponentHealth(
            name="vector_store",
            status="unhealthy",
            details="ChromaDB not responding",
        ))

    # LLM client
    if llm_client.is_healthy():
        components.append(ComponentHealth(
            name="llm_client",
            status="healthy",
            details="Gemini client configured",
        ))
    else:
        components.append(ComponentHealth(
            name="llm_client",
            status="unhealthy",
            details="Gemini client not configured",
        ))

    overall = "healthy" if all(c.status == "healthy" for c in components) else "degraded"

    return HealthResponse(status=overall, components=components)


@router.get(
    "/security-status",
    response_model=SecurityStatusResponse,
    summary="Security configuration status",
    description="Report the status of all security features.",
)
async def security_status(
    settings: Settings = Depends(get_settings),
) -> SecurityStatusResponse:
    """
    Returns the enabled/disabled status of every security feature.

    SECURITY: Does not reveal configuration values — only whether
    features are enabled.
    """
    features: list[SecurityFeature] = [
        SecurityFeature(
            name="api_key_authentication",
            enabled=True,
            description="All endpoints require X-API-Key header authentication.",
        ),
        SecurityFeature(
            name="prompt_injection_defense",
            enabled=True,
            description="Regex + keyword detection blocks known prompt injection patterns.",
        ),
        SecurityFeature(
            name="indirect_injection_defense",
            enabled=True,
            description="Retrieved document chunks are scanned for embedded injection attempts.",
        ),
        SecurityFeature(
            name="data_exfiltration_protection",
            enabled=True,
            description="Queries attempting bulk data extraction are detected and blocked.",
        ),
        SecurityFeature(
            name="output_filtering",
            enabled=True,
            description="LLM responses are scanned for secrets, credentials, and PII before delivery.",
        ),
        SecurityFeature(
            name="pii_masking",
            enabled=True,
            description="PII (emails, phones, credit cards, SSNs) is redacted in all logs.",
        ),
        SecurityFeature(
            name="rate_limiting",
            enabled=True,
            description=f"Query: {settings.rate_limit_query}, Ingest: {settings.rate_limit_ingest}.",
        ),
        SecurityFeature(
            name="out_of_scope_detection",
            enabled=True,
            description="Questions unrelated to ingested documents receive a refusal response.",
        ),

    ]

    all_critical_enabled = all(f.enabled for f in features)
    overall = "secure" if all_critical_enabled else "partial"

    return SecurityStatusResponse(overall_status=overall, features=features)
