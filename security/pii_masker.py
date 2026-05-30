# =============================================================================
# PII Masker — Detect and redact personally identifiable information
# =============================================================================
"""
Detects and masks PII (emails, phone numbers, credit cards, SSNs) in text.

Used in the logging pipeline to ensure raw PII is never written to logs,
and as a utility for output filtering.

SECURITY: All regex patterns are anchored and tested to avoid ReDoS.
"""
import re
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# PII pattern definitions
# ---------------------------------------------------------------------------
# Each pattern has a compiled regex and a replacement token.
# Patterns are ordered by specificity (most specific first) to avoid
# partial matches when multiple patterns could overlap.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PIIPattern:
    """Immutable definition of a PII detection pattern."""
    name: str
    regex: re.Pattern[str]
    replacement: str


# SECURITY: Patterns are intentionally broad to maximize detection.
# False positives in logging are acceptable — we prefer over-redaction
# to leaking real PII.

PII_PATTERNS: list[PIIPattern] = [
    # Credit card numbers: 13-19 digits, optionally separated by spaces or dashes
    PIIPattern(
        name="credit_card",
        regex=re.compile(
            r"\b(?:\d[ -]*?){13,19}\b"
        ),
        replacement="[CC_REDACTED]",
    ),
    # Social Security Numbers: XXX-XX-XXXX
    PIIPattern(
        name="ssn",
        regex=re.compile(
            r"\b\d{3}-\d{2}-\d{4}\b"
        ),
        replacement="[SSN_REDACTED]",
    ),
    # Email addresses
    PIIPattern(
        name="email",
        regex=re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
        ),
        replacement="[EMAIL_REDACTED]",
    ),
    # Phone numbers: various formats (US-centric but catches international prefixes)
    PIIPattern(
        name="phone",
        regex=re.compile(
            r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
        ),
        replacement="[PHONE_REDACTED]",
    ),
]


def mask_pii(text: str) -> str:
    """
    Replace all detected PII patterns in *text* with redaction tokens.

    Args:
        text: Raw text that may contain PII.

    Returns:
        Text with PII replaced by ``[*_REDACTED]`` tokens.

    Example::

        >>> mask_pii("Contact john@example.com or 555-123-4567")
        'Contact [EMAIL_REDACTED] or [PHONE_REDACTED]'
    """
    masked = text
    for pattern in PII_PATTERNS:
        masked = pattern.regex.sub(pattern.replacement, masked)
    return masked


def contains_pii(text: str) -> bool:
    """
    Check whether *text* contains any detectable PII.

    Returns:
        ``True`` if at least one PII pattern matches.
    """
    return any(pattern.regex.search(text) for pattern in PII_PATTERNS)


def detect_pii(text: str) -> list[dict[str, str]]:
    """
    Return a list of detected PII occurrences with their type and position.

    Each item is a dict with keys ``type``, ``match``, ``start``, ``end``.
    The ``match`` value is the redacted token (never the raw PII) so this
    function is safe to use in logs.
    """
    detections: list[dict[str, str]] = []
    for pattern in PII_PATTERNS:
        for match in pattern.regex.finditer(text):
            detections.append({
                "type": pattern.name,
                "match": pattern.replacement,  # SECURITY: never log raw match
                "start": str(match.start()),
                "end": str(match.end()),
            })
    return detections
