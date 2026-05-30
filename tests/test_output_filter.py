# =============================================================================
# Test: Output Filtering
# =============================================================================
"""
Tests that the output filter catches sensitive content in LLM responses
before they reach the user.
"""
import pytest
from security.output_filter import filter_output


class TestSecretDetection:
    """Tests for API key and credential detection in output."""

    @pytest.mark.parametrize("dangerous_output", [
        "The API key is sk-abc123456789abcdef01234567890abcdef",
        "Use this key: AIzaSyB1234567890abcdefghijklmnopqrstuv",
        "AWS access key: AKIAIOSFODNN7EXAMPLE",
        "password = SuperSecret123!",
        "token = eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2Vy",
        "secret: my_app_secret_value_12345",
        "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc",
        "Server=myserver;Database=mydb;User Id=admin;Password=p@ss",
    ])
    def test_blocks_secrets_in_output(self, dangerous_output: str) -> None:
        """Verify that responses containing secrets are blocked entirely."""
        result = filter_output(dangerous_output)
        assert not result.is_safe or "REDACTED" in result.filtered_text or \
            "unable to provide" in result.filtered_text.lower(), (
                f"Secret not caught in output: '{dangerous_output[:50]}...'"
            )
        assert len(result.violations) > 0

    def test_blocks_system_prompt_leakage(self) -> None:
        """Verify that system prompt leakage attempts are blocked."""
        output = "My system prompt is: You are a helpful assistant that..."
        result = filter_output(output)
        assert not result.is_safe
        assert "system_prompt_leak" in str(result.violations)


class TestPIIRedactionInOutput:
    """Tests for PII redaction in LLM output."""

    def test_redacts_pii_in_output(self) -> None:
        """Verify that PII in output is redacted (not blocked)."""
        output = "The customer email is john@example.com and phone is 555-123-4567."
        result = filter_output(output)
        assert "[EMAIL_REDACTED]" in result.filtered_text
        assert "[PHONE_REDACTED]" in result.filtered_text
        assert "john@example.com" not in result.filtered_text

    def test_clean_output_passes(self) -> None:
        """Verify clean output passes without modification."""
        output = "The refund policy allows returns within 30 days."
        result = filter_output(output)
        assert result.is_safe
        assert result.filtered_text == output
        assert len(result.violations) == 0


class TestExcessiveLength:
    """Tests for context dump detection via excessive length."""

    def test_truncates_excessive_output(self) -> None:
        """Verify that excessively long responses are truncated."""
        long_output = "x" * 10000
        result = filter_output(long_output)
        assert len(result.filtered_text) < len(long_output)
        assert "truncated" in result.filtered_text.lower()
        assert "excessive_length" in result.violations
