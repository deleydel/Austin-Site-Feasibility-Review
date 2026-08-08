"""Privacy filtering for generated report text."""

from __future__ import annotations

import re
from typing import Any

_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)
_PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}(?!\d)"
)
# Common contact-field labels that should never appear in outputs.
_CONTACT_LABEL_RE = re.compile(
    r"\b(applicant(?:_name)?|owner(?:_name)?|contact(?:_name|_email|_phone)?|"
    r"phone(?:_number)?|email(?:_address)?|mailing_address)\b\s*[:=]\s*[^\n;|]+",
    re.I,
)

_REDACTED = "[REDACTED]"


def scrub_text(text: str) -> str:
    """Remove emails, phone numbers, and labeled contact fields."""

    if not text:
        return text
    cleaned = _EMAIL_RE.sub(_REDACTED, text)
    cleaned = _PHONE_RE.sub(_REDACTED, cleaned)
    cleaned = _CONTACT_LABEL_RE.sub(_REDACTED, cleaned)
    return cleaned


def scrub_value(value: Any) -> Any:
    """Recursively scrub strings inside nested dict/list structures."""

    if isinstance(value, str):
        return scrub_text(value)
    if isinstance(value, list):
        return [scrub_value(v) for v in value]
    if isinstance(value, dict):
        return {k: scrub_value(v) for k, v in value.items()}
    return value
