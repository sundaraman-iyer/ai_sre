"""Input guardrails for PII redaction and prompt-injection detection.

Provides pre-processing utilities for incoming API questions before
vector retrieval or LLM inference.
"""

from __future__ import annotations

import re

# Regular expressions for prompt injection / jailbreak patterns
INJECTION_PATTERNS: list[tuple[str, str]] = [
    (
        r"(?i)\b(ignore|disregard|override|forget)\s+(all\s+)?(previous|prior|above|system)\s+(instructions|directives|rules|prompts)\b",
        "Instruction override attempt",
    ),
    (
        r"(?i)\byou\s+are\s+now\s+(DAN|jailbroken|unrestricted|mode)\b",
        "Jailbreak persona attempt",
    ),
    (
        r"(?i)<\s*/?\s*(system|user|assistant|prompt|instructions)\s*>",
        "System tag injection attempt",
    ),
    (
        r"(?i)\b(reveal|show|print|output|display)\b.*?\b(system\s+prompt|instructions|initial\s+prompt|developer\s+mode)\b",
        "System prompt extraction attempt",
    ),
    (
        r"(?i)\bdo\s+anything\s+now\b",
        "Jailbreak phrase attempt",
    ),
]


# Regular expressions for PII (Personally Identifiable Information) patterns
# Note: Credit Card pattern (13-19 digits) comes BEFORE Aadhaar (12 digits) and Phone (10 digits).
PII_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Email addresses
    (
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        "[REDACTED_EMAIL]",
    ),
    # Credit Card Numbers (13-19 digits with optional spaces/dashes)
    (
        re.compile(r"\b(?:\d[- ]*){13,19}\b"),
        "[REDACTED_CARD]",
    ),
    # Indian PAN Card Number (5 letters + 4 digits + 1 letter, e.g. ABCDE1234F)
    (
        re.compile(r"\b[A-Za-z]{5}\d{4}[A-Za-z]\b"),
        "[REDACTED_PAN]",
    ),
    # US SSN (XXX-XX-XXXX or XXX XX XXXX)
    (
        re.compile(r"\b\d{3}[- ]\d{2}[- ]\d{4}\b"),
        "[REDACTED_SSN]",
    ),
    # Indian Aadhaar Number (12 digits, e.g. 1234 5678 9012 or 1234-5678-9012)
    (
        re.compile(r"\b[2-9]\d{3}[- ]\d{4}[- ]\d{4}\b"),
        "[REDACTED_AADHAAR]",
    ),
    # Phone numbers (US & Indian +91 formats)
    (
        re.compile(r"(?:\+?91[- ]?)?[6-9]\d{9}\b|(?:\+?1[- ]?)?\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}\b"),
        "[REDACTED_PHONE]",
    ),
]


def detect_prompt_injection(text: str) -> tuple[bool, str | None]:
    """Detect if the input text contains prompt injection or jailbreak attempts.

    Returns:
        tuple[bool, str | None]: (True, reason) if injection is detected, else (False, None).
    """
    for pattern, reason in INJECTION_PATTERNS:
        if re.search(pattern, text):
            return True, reason
    return False, None


def redact_pii(text: str) -> tuple[str, bool]:
    """Scrub Personally Identifiable Information (PII) from input text.

    Returns:
        tuple[str, bool]: (sanitized_text, was_redacted)
    """
    sanitized = text
    was_redacted = False

    for pattern, replacement in PII_PATTERNS:
        new_text, count = pattern.subn(replacement, sanitized)
        if count > 0:
            sanitized = new_text
            was_redacted = True

    return sanitized, was_redacted
