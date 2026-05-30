# =============================================================================
# Output Filter — Scan LLM responses for sensitive content leakage
# =============================================================================
"""
Scans LLM-generated responses before they are returned to the user.

Checks for:
    - API key patterns (OpenAI, Google, Azure, AWS, generic)
    - Credential / connection string patterns
    - System prompt leakage
    - Excessive raw document content (context dumping)
    - PII in output

SECURITY: This is the last line of defense before the response leaves
the system. Even if the LLM is tricked into producing sensitive content,
this filter catches and blocks it.
"""
import re
import logging
from dataclasses import dataclass, field

from security.pii_masker import mask_pii, contains_pii

logger = logging.getLogger(__name__)


@dataclass
class OutputFilterResult:
    """Result of output filtering."""
    is_safe: bool
    filtered_text: str
    violations: list[str] = field(default_factory=list)
    reason: str = ""


# ---------------------------------------------------------------------------
# Sensitive content patterns
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SensitivePattern:
    """A pattern that indicates sensitive content in LLM output."""
    name: str
    regex: re.Pattern[str]
    severity: str  # "block" or "redact"


SENSITIVE_PATTERNS: list[SensitivePattern] = [
    # API Keys
    SensitivePattern(
        name="openai_api_key",
        regex=re.compile(r"sk-[A-Za-z0-9]{20,}"),
        severity="block",
    ),
    SensitivePattern(
        name="google_api_key",
        regex=re.compile(r"AIza[A-Za-z0-9_-]{35}"),
        severity="block",
    ),
    SensitivePattern(
        name="azure_key",
        regex=re.compile(r"[A-Za-z0-9+/]{40,}=="),
        severity="block",
    ),
    SensitivePattern(
        name="aws_key",
        regex=re.compile(r"AKIA[A-Z0-9]{16}"),
        severity="block",
    ),
    SensitivePattern(
        name="generic_bearer_token",
        regex=re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
        severity="block",
    ),
    # Credentials
    SensitivePattern(
        name="password_assignment",
        regex=re.compile(r"password\s*[=:]\s*\S+", re.IGNORECASE),
        severity="block",
    ),
    SensitivePattern(
        name="secret_assignment",
        regex=re.compile(r"(secret|token|credential)\s*[=:]\s*\S+", re.IGNORECASE),
        severity="block",
    ),
    SensitivePattern(
        name="connection_string",
        regex=re.compile(
            r"(Server|Data\s+Source|Initial\s+Catalog|User\s+Id|Password)\s*=",
            re.IGNORECASE,
        ),
        severity="block",
    ),
    # System prompt leakage indicators
    SensitivePattern(
        name="system_prompt_leak",
        regex=re.compile(
            r"(my\s+system\s+prompt|my\s+instructions\s+are|I\s+was\s+told\s+to|"
            r"my\s+initial\s+prompt|here\s+(?:is|are)\s+my\s+(?:system\s+)?instructions)",
            re.IGNORECASE,
        ),
        severity="block",
    ),
]

# SECURITY: Maximum allowed response length before triggering a
# context-dump warning. Prevents the LLM from being tricked into
# dumping full document content.
MAX_SAFE_RESPONSE_LENGTH: int = 5000


def filter_output(llm_response: str) -> OutputFilterResult:
    """
    Scan an LLM response for sensitive content and policy violations.

    Args:
        llm_response: The raw response text from the LLM.

    Returns:
        An ``OutputFilterResult`` with the safe (or blocked) text.

    SECURITY: If ANY "block"-severity pattern matches, the entire
    response is replaced with a refusal message. We never partially
    return a response that contains secrets.
    """
    violations: list[str] = []
    filtered = llm_response

    # --- Check for sensitive patterns ---
    for pattern in SENSITIVE_PATTERNS:
        if pattern.regex.search(filtered):
            violations.append(f"{pattern.name} ({pattern.severity})")
            if pattern.severity == "block":
                logger.warning(
                    "Output filter BLOCKED response | violation=%s",
                    pattern.name,
                )
                return OutputFilterResult(
                    is_safe=False,
                    filtered_text=(
                        "I'm unable to provide that response as it may contain "
                        "sensitive information. Please rephrase your question."
                    ),
                    violations=violations,
                    reason=f"Blocked: {pattern.name} detected in output",
                )

    # --- Check for PII ---
    if contains_pii(filtered):
        # Redact PII rather than blocking entirely
        filtered = mask_pii(filtered)
        violations.append("pii_detected (redacted)")
        logger.info("Output filter redacted PII from response")

    # --- Check for excessive length (context dump) ---
    if len(filtered) > MAX_SAFE_RESPONSE_LENGTH:
        violations.append("excessive_length")
        logger.warning(
            "Output filter truncated excessive response | length=%d",
            len(filtered),
        )
        filtered = (
            filtered[:MAX_SAFE_RESPONSE_LENGTH]
            + "\n\n[Response truncated for security — excessive length detected]"
        )

    return OutputFilterResult(
        is_safe=len(violations) == 0 or all("redacted" in v or "length" in v for v in violations),
        filtered_text=filtered,
        violations=violations,
        reason="",
    )
