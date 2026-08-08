"""Code-side enforcement of judge verdicts.

A small local model will assert that unrelated evidence supports a claim, which
would silently inflate every grounding metric. Support verdicts are therefore
only accepted when the judge can point at text that really exists in the
evidence, and when claim and evidence share enough content to be about the same
subject. Both checks run in Python; the model never has the final word.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

VERDICTS = ("supported", "partially_supported", "unsupported")

# Minimum share of the claim's content words that must also appear in the
# evidence before a support verdict is believable. Deliberately low: it is a
# floor against wholly unrelated evidence, not a similarity score.
MIN_TERM_OVERLAP = 0.30

# Coverage at which the evidence demonstrably contains the claim's substance,
# so a support verdict stands even when the model quoted badly.
STRONG_TERM_OVERLAP = 0.75

# Shortest quote that counts as the judge pointing at something specific.
# Small models often answer with a section marker such as "(A)", which is
# present in the evidence but proves nothing.
MIN_QUOTE_CHARS = 20

_STOPWORDS = {
    "a", "an", "and", "any", "are", "as", "at", "be", "been", "but", "by",
    "for", "from", "has", "have", "in", "is", "it", "its", "may", "must",
    "not", "of", "on", "or", "shall", "that", "the", "their", "there",
    "these", "this", "to", "was", "were", "which", "will", "with", "would",
}


def normalize(text: str) -> str:
    """Fold Unicode punctuation and whitespace for literal comparison."""

    text = unicodedata.normalize("NFKC", str(text or ""))
    text = (
        text.replace("‘", "'").replace("’", "'")
        .replace("“", '"').replace("”", '"')
        .replace("–", "-").replace("—", "-")
        .replace(" ", " ")
    )
    return " ".join(text.lower().split())


def content_terms(text: str) -> set[str]:
    """Content words and numbers, stopwords removed."""

    tokens = re.findall(r"[a-z0-9][a-z0-9\-./%]*", normalize(text))
    return {t for t in tokens if t not in _STOPWORDS and len(t) > 2}


def term_overlap(claim: str, evidence: str) -> float:
    """Share of the claim's content terms that also occur in the evidence."""

    claim_terms = content_terms(claim)
    if not claim_terms:
        return 0.0
    return len(claim_terms & content_terms(evidence)) / len(claim_terms)


def numbers_in(text: str) -> set[str]:
    """Numeric literals in the text, normalized so 45 and 45.0 compare equal."""

    found = set()
    for raw in re.findall(r"\d+(?:\.\d+)?", normalize(text)):
        value = float(raw)
        found.add(str(int(value)) if value.is_integer() else str(value))
    return found


def distinctive_terms(text: str) -> set[str]:
    """Specific identifiers a claim names: proper nouns and coded tokens.

    Generic regulatory vocabulary ("watershed", "drainage", "requirements")
    overlaps between almost any claim and any section, so term overlap alone
    lets a claim about Shoal Creek be "supported" by text that never mentions
    it. Named entities and codes are what actually pin a claim to a subject.
    """

    raw = unicodedata.normalize("NFKC", str(text or ""))
    terms: set[str] = set()

    # Coded identifiers: SF-3-NP, 25-8-341, 9.8.2 - anything mixing letters or
    # dots with digits and separators. Plain numbers are excluded: they are
    # already handled by the number check, which compares them numerically.
    for token in re.findall(r"\b[A-Za-z]*\d[\w\-.]*\b|\b[A-Z]{2,}-[\w\-]+\b", raw):
        cleaned = token.strip(".,;:").lower()
        if len(cleaned) > 1 and not re.fullmatch(r"\d+(\.\d+)?", cleaned):
            terms.add(cleaned)

    # Multi-word proper nouns, ignoring the first word of each sentence so an
    # ordinary sentence opener is not mistaken for a name.
    for sentence in re.split(r"(?<=[.!?])\s+", raw):
        words = sentence.split()
        for index, word in enumerate(words):
            if index == 0:
                continue
            bare = word.strip(".,;:()")
            if len(bare) > 2 and bare[0].isupper() and bare[1:].islower():
                terms.add(bare.lower())

    return {t for t in terms if t not in _STOPWORDS}


def quote_in_evidence(quote: str, evidence: str) -> bool:
    """True when the quoted span really occurs in the evidence."""

    q = normalize(quote)
    if len(q) < MIN_QUOTE_CHARS:
        return False
    return q in normalize(evidence)


def enforce_support_verdict(
    verdict: dict[str, Any], claim: str, evidence: str
) -> dict[str, Any]:
    """Downgrade an unbelievable support verdict to ``unsupported``.

    Returns the verdict with ``verdict``, ``enforced`` (True when code
    overrode the model) and ``enforcement`` (why) filled in.
    """

    result = dict(verdict)
    raw = str(result.get("verdict", "")).strip().lower().replace(" ", "_")
    if raw not in VERDICTS:
        raw = "unsupported"
        result["enforcement"] = "verdict value not recognized"
        result["verdict"] = raw
        result["enforced"] = True
        return result

    result["verdict"] = raw
    result["enforced"] = False
    result["enforcement"] = None

    if raw == "unsupported":
        return result

    overlap = round(term_overlap(claim, evidence), 3)
    result["term_overlap"] = overlap
    if overlap < MIN_TERM_OVERLAP:
        result["verdict"] = "unsupported"
        result["enforced"] = True
        result["enforcement"] = (
            f"claim and evidence share only {overlap:.0%} of the claim's "
            f"content terms (floor {MIN_TERM_OVERLAP:.0%})"
        )
        return result

    missing = numbers_in(claim) - numbers_in(evidence)
    if missing:
        result["missing_numbers"] = sorted(missing)
        result["verdict"] = "unsupported"
        result["enforced"] = True
        result["enforcement"] = (
            f"claim asserts numbers absent from the evidence: {sorted(missing)}"
        )
        return result

    # Substring match against the normalized evidence, not the tokenized term
    # set, so short or punctuated identifiers are not lost to tokenization.
    normalized_evidence = normalize(evidence)
    unnamed = {t for t in distinctive_terms(claim) if t not in normalized_evidence}
    if unnamed:
        result["missing_identifiers"] = sorted(unnamed)
        result["verdict"] = "unsupported"
        result["enforced"] = True
        result["enforcement"] = (
            "claim names identifiers the evidence never mentions: "
            f"{sorted(unnamed)}"
        )
        return result

    quote = str(result.get("quote", ""))
    result["quote_verified"] = quote_in_evidence(quote, evidence)
    if result["quote_verified"]:
        return result

    # The model quoted badly. Code can still confirm support on its own when
    # the evidence covers essentially all of the claim's substance.
    if overlap >= STRONG_TERM_OVERLAP:
        result["support_basis"] = "lexical_coverage"
        result["enforcement"] = (
            f"model quote unusable; support confirmed by {overlap:.0%} term "
            "coverage and no unmatched numbers"
        )
        return result

    result["verdict"] = "unsupported"
    result["enforced"] = True
    if not quote.strip():
        result["enforcement"] = "no supporting quote was given"
    elif len(normalize(quote)) < MIN_QUOTE_CHARS:
        result["enforcement"] = (
            f"supporting quote too short to be meaningful: {quote.strip()!r}"
        )
    else:
        result["enforcement"] = (
            "the quoted supporting text does not occur in the evidence"
        )
    return result
