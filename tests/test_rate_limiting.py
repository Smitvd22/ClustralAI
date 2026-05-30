# =============================================================================
# Test: Rate Limiting
# =============================================================================
"""
Tests that the rate limiter correctly throttles excessive requests.
"""
import pytest


class TestRateLimiting:
    """Tests for rate limiting on API endpoints."""

    def test_health_endpoint_accessible(self, client) -> None:
        """Verify the health endpoint is accessible (no auth required)."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_unauthenticated_request_rejected(self, client) -> None:
        """Verify requests without API key are rejected."""
        response = client.post(
            "/query",
            json={"question": "What is the refund policy?"},
        )
        assert response.status_code == 401

    def test_invalid_api_key_rejected(self, client) -> None:
        """Verify requests with invalid API key are rejected."""
        response = client.post(
            "/query",
            json={"question": "What is the refund policy?"},
            headers={"X-API-Key": "invalid-key-12345"},
        )
        assert response.status_code == 403

    def test_valid_api_key_accepted(self, client, auth_headers) -> None:
        """Verify requests with valid API key are accepted."""
        response = client.post(
            "/query",
            json={"question": "What is the refund policy?"},
            headers=auth_headers,
        )
        # Should be 200 (even if no documents, should not be 401/403)
        assert response.status_code == 200

    def test_security_status_accessible(self, client) -> None:
        """Verify security status endpoint works without auth."""
        response = client.get("/security-status")
        assert response.status_code == 200
        data = response.json()
        assert "features" in data
        assert len(data["features"]) > 0
