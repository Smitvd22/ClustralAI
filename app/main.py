# =============================================================================
# Application Entry Point — FastAPI with Security Middleware
# =============================================================================
"""
Main FastAPI application with:
    - Lifespan handler for startup/shutdown
    - Security middleware (rate limiting, CORS)
    - Structured logging with PII masking
    - Azure Monitor integration (when configured)
    - Router mounting

SECURITY: The application is configured with restrictive defaults:
    - CORS: No origins allowed by default (configure per deployment)
    - Rate limiting: Enabled on all mutable endpoints
    - Authentication: Required on /ingest and /query
    - Logging: PII is always masked
"""
import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler as _default_handler
from slowapi.errors import RateLimitExceeded

from app.config import load_settings, Settings
from app.dependencies import init_services
from app.routers import ingest, query, health
from security.api_auth import configure_api_keys
from security.rate_limiter import limiter, rate_limit_exceeded_handler
from security.pii_masker import mask_pii

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

class PIIMaskingFilter(logging.Filter):
    """
    Logging filter that masks PII in all log messages.

    SECURITY: Applied globally to prevent accidental PII leakage in logs.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = mask_pii(record.msg)
        return True


def setup_logging(settings: Settings) -> None:
    """Configure structured logging with PII masking."""
    level = getattr(logging, settings.app_log_level.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(PIIMaskingFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Suppress noisy third-party loggers
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)



# ---------------------------------------------------------------------------
# Lifespan handler
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler.

    Startup:
        1. Load configuration
        2. Setup logging and monitoring
        3. Configure API authentication
        4. Initialize services (embedding model, ChromaDB, LLM)

    Shutdown:
        1. Log clean shutdown
    """
    # --- Startup ---
    settings = load_settings()
    setup_logging(settings)

    logger.info("=" * 60)
    logger.info("Security-First RAG System starting")
    logger.info("=" * 60)

    # Configure API authentication
    api_keys = settings.get_api_keys_list()
    configure_api_keys(api_keys)

    # (Skipping embedding model warmup to prevent memory spikes before port binding)

    # Initialize all services
    init_services(settings)

    logger.info("=" * 60)
    logger.info("System ready — all security layers active")
    logger.info("=" * 60)

    yield

    # --- Shutdown ---
    logger.info("System shutting down gracefully")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Security-First RAG System",
    description=(
        "A security-hardened Retrieval-Augmented Generation API. "
        "Ingests PDF documents and answers questions with citations. "
        "Protected by multiple security layers including prompt injection "
        "defense, data exfiltration protection, PII masking, rate limiting, "
        "and output filtering."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# --- Rate limiter ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# --- CORS ---
# SECURITY: Restrictive CORS by default. Configure allowed origins
# per deployment environment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],  # No origins allowed by default
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Content-Type"],
)

# --- Routers ---
app.include_router(ingest.router)
app.include_router(query.router)
app.include_router(health.router)
