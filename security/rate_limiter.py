# =============================================================================
# Rate Limiter — Throttle API requests to prevent abuse
# =============================================================================
"""
Rate limiting middleware using ``slowapi`` (built on top of ``limits``).

Configuration:
    - ``/query``: 10 requests/minute per IP (configurable)
    - ``/ingest``: 5 requests/minute per IP (configurable)
    - Default: 30 requests/minute per IP

Uses in-memory storage, which is appropriate for a single-instance
free-tier deployment. For multi-instance deployments, switch to
Redis-backed storage.

SECURITY: Rate limiting protects against brute-force attacks, API abuse,
and resource exhaustion on the free tier.
"""
import logging

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Limiter instance — shared across the application
# ---------------------------------------------------------------------------
# SECURITY: Uses client IP as the rate-limit key. Behind a reverse proxy,
# ensure X-Forwarded-For is configured correctly.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["30/minute"],
    storage_uri="memory://",
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom handler for rate limit exceeded errors.

    Returns a 429 response with a human-readable message and Retry-After
    header as per HTTP spec.

    SECURITY: Logs the rate limit event for monitoring / alerting.
    """
    logger.warning(
        "Rate limit exceeded | ip=%s path=%s",
        get_remote_address(request),
        request.url.path,
    )
    # Extract retry-after from the exception detail if available
    retry_after = str(getattr(exc, "retry_after", 60))
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please slow down and try again later.",
            "retry_after_seconds": retry_after,
        },
        headers={"Retry-After": retry_after},
    )
