# =============================================================================
# API Authentication — API Key-based access control
# =============================================================================
"""
API key authentication for all endpoints.

Keys are loaded from application configuration (which in production
pulls from Azure Key Vault). No anonymous access is allowed.

SECURITY: Uses ``hmac.compare_digest`` for constant-time comparison
to prevent timing attacks on API key validation.
"""
import hmac
import logging
from typing import Optional

from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# API Key header scheme
# ---------------------------------------------------------------------------
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# This will be set at startup from config
_valid_api_keys: list[str] = []


def configure_api_keys(keys: list[str]) -> None:
    """
    Set the valid API keys at application startup.

    Args:
        keys: List of valid API key strings loaded from config / Key Vault.

    SECURITY: Keys are stored in memory only. They are never logged.
    """
    global _valid_api_keys
    _valid_api_keys = list(keys)
    logger.info("API authentication configured with %d key(s)", len(keys))


def _validate_key(provided_key: str) -> bool:
    """
    Validate a provided API key against the configured keys.

    SECURITY: Uses constant-time comparison via ``hmac.compare_digest``
    to prevent timing side-channel attacks.
    """
    for valid_key in _valid_api_keys:
        if hmac.compare_digest(provided_key.encode("utf-8"), valid_key.encode("utf-8")):
            return True
    return False


async def verify_api_key(
    api_key: Optional[str] = Security(API_KEY_HEADER),
) -> str:
    """
    FastAPI dependency that enforces API key authentication.

    Raises:
        HTTPException(401): If no API key is provided.
        HTTPException(403): If the API key is invalid.

    Returns:
        The validated API key string.
    """
    if api_key is None:
        logger.warning("Authentication failed | reason=missing_api_key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "authentication_required",
                "message": "API key is required. Provide it via the X-API-Key header.",
            },
        )

    if not _validate_key(api_key):
        logger.warning("Authentication failed | reason=invalid_api_key")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "invalid_api_key",
                "message": "The provided API key is invalid.",
            },
        )

    return api_key
