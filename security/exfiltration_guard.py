# =============================================================================
# Exfiltration Guard — Detect data exfiltration attempts
# =============================================================================
"""
Detects user queries that attempt to extract bulk data, enumerate all
documents, export embeddings, or dump the database.

SECURITY: This guard works alongside the prompt guard but focuses
specifically on data exfiltration patterns rather than instruction
override attempts.
"""
import re
import logging
from dataclasses import dataclass, field

from security.pii_masker import mask_pii

logger = logging.getLogger(__name__)


@dataclass
class ExfiltrationResult:
    """Result of a data exfiltration check."""
    is_safe: bool
    score: float
    matched_patterns: list[str] = field(default_factory=list)
    reason: str = ""


@dataclass(frozen=True)
class ExfilPattern:
    """A data exfiltration detection pattern."""
    name: str
    regex: re.Pattern[str]
    weight: float


EXFILTRATION_PATTERNS: list[ExfilPattern] = [
    ExfilPattern(
        name="retrieve_all_documents",
        regex=re.compile(
            r"(retrieve|return|show|give|list|get|display|fetch)\s+"
            r"(me\s+)?(all|every|each|entire|complete|full)\s+"
            r"(the\s+)?(documents?|files?|pdfs?|records?|data|content|chunks?|pages?|texts?)",
            re.IGNORECASE,
        ),
        weight=0.9,
    ),
    ExfilPattern(
        name="export_embeddings",
        regex=re.compile(
            r"(export|extract|dump|download|save|output)\s+"
            r"(the\s+)?(all\s+|complete\s+|entire\s+)?(embeddings?|vectors?|vector\s*db|vector\s*database|indices|index)",
            re.IGNORECASE,
        ),
        weight=0.9,
    ),
    ExfilPattern(
        name="dump_database",
        regex=re.compile(
            r"(dump|export|backup|copy|clone|replicate)\s+"
            r"(the\s+)?(entire\s+|complete\s+)?(database|db|storage|store|collection|chroma)",
            re.IGNORECASE,
        ),
        weight=0.9,
    ),
    ExfilPattern(
        name="list_sources",
        regex=re.compile(
            r"(list|enumerate|show|tell|give)\s+(me\s+)?(all|every)\s+"
            r"(the\s+)?(source|original|uploaded|ingested)\s+"
            r"(files?|documents?|pdfs?|names?)",
            re.IGNORECASE,
        ),
        weight=0.8,
    ),
    ExfilPattern(
        name="count_exploitation",
        regex=re.compile(
            r"how\s+many\s+(documents?|files?|chunks?|records?|pdfs?)\s+"
            r"(are|do\s+you\s+have|exist|are\s+stored|are\s+in)",
            re.IGNORECASE,
        ),
        weight=0.5,
    ),
    ExfilPattern(
        name="bulk_content_request",
        regex=re.compile(
            r"(return|give|show|print|output)\s+(me\s+)?(everything|all\s+of\s+it|"
            r"the\s+entire\s+content|the\s+whole\s+thing|every\s+single)",
            re.IGNORECASE,
        ),
        weight=0.85,
    ),
    ExfilPattern(
        name="raw_data_request",
        regex=re.compile(
            r"(raw|unprocessed|original|verbatim|exact)\s+"
            r"(data|text|content|documents?|chunks?)",
            re.IGNORECASE,
        ),
        weight=0.6,
    ),
    ExfilPattern(
        name="metadata_enumeration",
        regex=re.compile(
            r"(list|show|enumerate|get)\s+(all\s+)?(metadata|properties|attributes|fields)\s+"
            r"(of|from|for|in)\s+(the\s+)?(documents?|collection|database)",
            re.IGNORECASE,
        ),
        weight=0.7,
    ),
]

EXFIL_BLOCK_THRESHOLD: float = 0.7


def check_exfiltration(user_input: str) -> ExfiltrationResult:
    """
    Check a user query for data exfiltration attempts.

    Args:
        user_input: The raw user query string.

    Returns:
        An ``ExfiltrationResult`` indicating safety and matched patterns.
    """
    cumulative_score: float = 0.0
    matched: list[str] = []

    for pattern in EXFILTRATION_PATTERNS:
        if pattern.regex.search(user_input):
            cumulative_score += pattern.weight
            matched.append(pattern.name)

    is_safe = cumulative_score < EXFIL_BLOCK_THRESHOLD

    if not is_safe:
        safe_text = mask_pii(user_input[:200])
        logger.warning(
            "Data exfiltration BLOCKED | score=%.2f patterns=%s input_preview='%s'",
            cumulative_score,
            matched,
            safe_text,
        )

    return ExfiltrationResult(
        is_safe=is_safe,
        score=cumulative_score,
        matched_patterns=matched,
        reason=(
            f"Blocked: data exfiltration attempt detected (score={cumulative_score:.2f})"
            if not is_safe
            else ""
        ),
    )
