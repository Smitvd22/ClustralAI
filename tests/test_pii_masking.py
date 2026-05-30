# =============================================================================
# Test: PII Masking
# =============================================================================
"""
Tests that the PII masker correctly detects and redacts:
    - Email addresses
    - Phone numbers
    - Credit card numbers
    - Social Security Numbers (SSNs)
"""
import pytest
from security.pii_masker import mask_pii, contains_pii, detect_pii


class TestEmailMasking:
    """Tests for email address detection and masking."""

    @pytest.mark.parametrize("text,expected", [
        (
            "Contact john@example.com for help",
            "Contact [EMAIL_REDACTED] for help",
        ),
        (
            "Emails: alice@corp.co.uk and bob.smith@company.org",
            "Emails: [EMAIL_REDACTED] and [EMAIL_REDACTED]",
        ),
        (
            "Send to user+tag@gmail.com",
            "Send to [EMAIL_REDACTED]",
        ),
    ])
    def test_masks_emails(self, text: str, expected: str) -> None:
        """Verify email addresses are replaced with [EMAIL_REDACTED]."""
        result = mask_pii(text)
        assert "[EMAIL_REDACTED]" in result
        assert "@" not in result.replace("[EMAIL_REDACTED]", "")

    def test_no_email_no_change(self) -> None:
        """Verify text without emails is unchanged."""
        text = "This text has no personal information."
        assert mask_pii(text) == text


class TestPhoneMasking:
    """Tests for phone number detection and masking."""

    @pytest.mark.parametrize("text", [
        "Call 555-123-4567 for support",
        "Phone: (555) 123-4567",
        "Reach us at +1-555-123-4567",
        "Cell: 555.123.4567",
    ])
    def test_masks_phone_numbers(self, text: str) -> None:
        """Verify phone numbers are replaced with [PHONE_REDACTED]."""
        result = mask_pii(text)
        assert "[PHONE_REDACTED]" in result


class TestCreditCardMasking:
    """Tests for credit card number detection and masking."""

    @pytest.mark.parametrize("text", [
        "Card: 4111 1111 1111 1111",
        "CC: 4111-1111-1111-1111",
        "Payment with 5500000000000004",
    ])
    def test_masks_credit_cards(self, text: str) -> None:
        """Verify credit card numbers are replaced with [CC_REDACTED]."""
        result = mask_pii(text)
        assert "[CC_REDACTED]" in result


class TestSSNMasking:
    """Tests for SSN detection and masking."""

    @pytest.mark.parametrize("text", [
        "SSN: 123-45-6789",
        "Social Security Number is 987-65-4321",
    ])
    def test_masks_ssns(self, text: str) -> None:
        """Verify SSNs are replaced with [SSN_REDACTED]."""
        result = mask_pii(text)
        assert "[SSN_REDACTED]" in result


class TestContainsPII:
    """Tests for the PII detection utility."""

    def test_detects_pii_present(self) -> None:
        """Verify contains_pii returns True when PII exists."""
        assert contains_pii("Email: test@example.com")
        assert contains_pii("Phone: 555-123-4567")

    def test_no_pii_detected(self) -> None:
        """Verify contains_pii returns False for clean text."""
        assert not contains_pii("This is a normal sentence without PII.")


class TestDetectPII:
    """Tests for the PII detection detail function."""

    def test_returns_detection_details(self) -> None:
        """Verify detect_pii returns structured detection info."""
        detections = detect_pii("Contact admin@corp.com or 555-123-4567")
        assert len(detections) >= 2
        types = {d["type"] for d in detections}
        assert "email" in types
        assert "phone" in types
        # SECURITY: Verify the actual PII value is NOT in the output
        for detection in detections:
            assert "admin@corp.com" not in detection["match"]
            assert "555-123-4567" not in detection["match"]

    def test_empty_text_no_detections(self) -> None:
        """Verify empty text returns no detections."""
        assert detect_pii("") == []
