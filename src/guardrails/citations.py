"""Citation extraction and verification against the regulatory index.

Existence in the index is necessary but not sufficient: a citation must also
be topically related to the claim or retrieval context it is offered to support.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any, Callable

from src import config
from src.guardrails.sources import (
    is_approved_regulatory_source,
    normalize_regulatory_source,
)

# Floor against wholly unrelated section pairings (aligned with Task 7).
MIN_SUPPORT_OVERLAP = 0.30

_STOPWORDS = {
    "a", "an", "and", "any", "are", "as", "at", "be", "been", "but", "by",
    "for", "from", "has", "have", "in", "is", "it", "its", "may", "must",
    "not", "of", "on", "or", "shall", "that", "the", "their", "there",
    "these", "this", "to", "was", "were", "which", "will", "with", "would",
    "austin", "development", "requirements", "proposed", "identify",
    "applicable", "general",
}


@lru_cache(maxsize=1)
def _load_sections() -> list[dict[str, Any]]:
    """Load section index without importing the heavy retriever stack."""

    return json.loads(config.REG_SECTIONS_JSON.read_text())


def lookup_section(source: str, section_number: str) -> dict[str, Any]:
    """Namespaced exact section lookup used by citation verification."""

    doc_id = normalize_regulatory_source(source) or source.strip().upper()
    num = section_number.strip().lstrip("§").strip()
    matches = [
        s
        for s in _load_sections()
        if s.get("doc_id") == doc_id and s.get("section_number") == num
    ]
    if not matches:
        return {
            "status": "not_found",
            "source": doc_id,
            "section_number": num,
            "matches": [],
        }
    status = "found" if len(matches) == 1 else "ambiguous"
    return {
        "status": status,
        "source": doc_id,
        "section_number": num,
        "matches": matches,
    }


def _content_terms(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9][a-z0-9\-./%]*", str(text or "").lower())
    return {t for t in tokens if t not in _STOPWORDS and len(t) > 2}


def term_overlap(claim: str, evidence: str) -> float:
    """Share of the claim's content terms that also occur in the evidence."""

    claim_terms = _content_terms(claim)
    if not claim_terms:
        return 0.0
    return len(claim_terms & _content_terms(evidence)) / len(claim_terms)


def numbers_in(text: str) -> set[str]:
    found = set()
    for raw in re.findall(r"\d+(?:\.\d+)?", str(text or "").lower()):
        value = float(raw)
        found.add(str(int(value)) if value.is_integer() else str(value))
    return found


def assess_claim_support(
    claim_or_context: str,
    section_text: str,
    section_title: str = "",
    *,
    require_number_agreement: bool = False,
) -> dict[str, Any]:
    """Deterministic claim-support check against authoritative section text.

    A cited section that exists but does not share enough content with the
    attached claim/context is treated as unsupported.
    """

    evidence = f"{section_title}\n{section_text}".strip()
    if not claim_or_context.strip() or not evidence:
        return {
            "supports_claim": False,
            "support_score": 0.0,
            "support_detail": "Missing claim/context or section text for support check.",
        }

    overlap = term_overlap(claim_or_context, evidence)

    if overlap < MIN_SUPPORT_OVERLAP:
        return {
            "supports_claim": False,
            "support_score": round(overlap, 3),
            "support_detail": (
                f"Claim/context and cited section share only {overlap:.0%} of "
                "content terms; citation does not adequately support the claim."
            ),
        }

    if require_number_agreement:
        missing = sorted(numbers_in(claim_or_context) - numbers_in(evidence))
        # Ignore lone section-style tokens; keep real quantities (e.g. 45%).
        missing = [n for n in missing if len(n) >= 2]
        if missing:
            return {
                "supports_claim": False,
                "support_score": round(overlap, 3),
                "support_detail": (
                    "Claim asserts numbers the cited section does not contain: "
                    f"{missing}"
                ),
            }

    return {
        "supports_claim": True,
        "support_score": round(overlap, 3),
        "support_detail": (
            f"Section text supports the attached claim/context "
            f"(term overlap {overlap:.0%})."
        ),
    }


def _passage_citation(passage: dict[str, Any]) -> dict[str, Any]:
    """Normalize a retriever hit into a citation record."""

    source = (
        passage.get("doc_id")
        or passage.get("source")
        or passage.get("source_name")
        or ""
    )
    section_number = passage.get("section_number") or ""
    # Prefer explicit claim, then retrieved passage body, then section title.
    # Avoid concatenating the full retrieval query — it dilutes overlap scores.
    context = (
        passage.get("claim")
        or passage.get("support_context")
        or passage.get("text")
        or passage.get("body")
        or passage.get("section_title")
        or passage.get("query")
        or ""
    )
    context = str(context).strip()

    return {
        "source": source,
        "source_name": passage.get("source_name") or source,
        "source_url": passage.get("source_url") or "",
        "chapter": passage.get("chapter") or "",
        "section_number": section_number,
        "section_title": passage.get("section_title") or "",
        "breadcrumb": passage.get("breadcrumb") or "",
        "chunk_id": passage.get("chunk_id"),
        "review_category": passage.get("review_category"),
        "query": passage.get("query"),
        "support_context": context,
        "claim_support": "pending_verification",
    }


def extract_citations_from_evidence(
    evidence: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build unique citation records from retrieved evidence passages."""

    citations: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for item in evidence or []:
        cite = _passage_citation(item)
        doc_id = normalize_regulatory_source(str(cite["source"])) or str(
            cite["source"]
        )
        key = (doc_id, str(cite["section_number"]))
        if key in seen:
            continue
        seen.add(key)
        cite["source"] = doc_id
        citations.append(cite)

    return citations


def attach_review_context_to_evidence(
    evidence: list[dict[str, Any]],
    reviews: dict[str, Any],
) -> list[dict[str, Any]]:
    """Copy review query/category onto evidence passages for support checks."""

    # Map chunk/section ids back to the review that retrieved them.
    passage_owner: dict[tuple[str, str], dict[str, str]] = {}
    for category, review in (reviews or {}).items():
        if not isinstance(review, dict):
            continue
        query = str(review.get("query") or "")
        for passage in review.get("retrieved_passages") or []:
            doc_id = str(passage.get("doc_id") or "")
            section = str(passage.get("section_number") or "")
            if doc_id and section:
                passage_owner[(doc_id, section)] = {
                    "review_category": category,
                    "query": query,
                }

    enriched = []
    for item in evidence or []:
        row = dict(item)
        key = (
            str(row.get("doc_id") or ""),
            str(row.get("section_number") or ""),
        )
        meta = passage_owner.get(key)
        if meta:
            row.setdefault("review_category", meta["review_category"])
            row.setdefault("query", meta["query"])
        enriched.append(row)
    return enriched


def verify_citation(
    citation: dict[str, Any],
    get_section: Callable[[str, str], dict],
) -> dict[str, Any]:
    """Verify one citation for approved source, existence, and claim support.

    Status values:
      - found: approved source, section exists, and support check passed
      - unsupported_claim: section exists but does not support the claim/context
      - ambiguous / unapproved_source / missing_section / not_found
    """

    result = dict(citation)
    source_raw = str(citation.get("source") or citation.get("source_name") or "")
    section_number = str(citation.get("section_number") or "").strip()

    if not is_approved_regulatory_source(source_raw):
        result["verification_status"] = "unapproved_source"
        result["supports_claim"] = False
        result["verification_detail"] = (
            f"Source '{source_raw}' is not on the approved regulatory source list."
        )
        return result

    doc_id = normalize_regulatory_source(source_raw) or source_raw.upper()
    result["source"] = doc_id

    if not section_number:
        result["verification_status"] = "missing_section"
        result["supports_claim"] = False
        result["verification_detail"] = "Citation is missing a section number."
        return result

    lookup = get_section(doc_id, section_number)
    status = lookup.get("status")

    if status != "found":
        result["verification_status"] = status
        result["supports_claim"] = False
        if status == "ambiguous":
            result["verification_detail"] = (
                "Multiple sections matched; citation requires manual verification."
            )
        else:
            result["verification_detail"] = (
                f"Section {section_number} not found in {doc_id}."
            )
        return result

    match = (lookup.get("matches") or [{}])[0]
    result["section_title"] = (
        result.get("section_title") or match.get("section_title") or ""
    )
    result["source_url"] = (
        result.get("source_url") or match.get("source_url") or ""
    )
    result["breadcrumb"] = (
        result.get("breadcrumb") or match.get("breadcrumb") or ""
    )
    section_text = str(match.get("text") or "")

    explicit_claim = str(citation.get("claim") or "").strip()
    support_context = explicit_claim or str(
        citation.get("support_context")
        or citation.get("query")
        or citation.get("section_title")
        or ""
    )
    # Use title + breadcrumb + first part of section when context is only a
    # broad retrieval query, so topical chapter/section matches can pass.
    support = assess_claim_support(
        support_context,
        section_text,
        section_title=str(
            result.get("section_title")
            or result.get("breadcrumb")
            or ""
        ),
        require_number_agreement=bool(explicit_claim),
    )
    result["support_score"] = support["support_score"]
    result["excerpt"] = section_text[:400]

    if support["supports_claim"]:
        result["verification_status"] = "found"
        result["supports_claim"] = True
        result["claim_support"] = "supported"
        result["verification_detail"] = support["support_detail"]
    else:
        result["verification_status"] = "unsupported_claim"
        result["supports_claim"] = False
        result["claim_support"] = "unsupported"
        result["verification_detail"] = support["support_detail"]

    return result


def verify_citations(
    citations: list[dict[str, Any]],
    get_section: Callable[[str, str], dict] | None = None,
) -> list[dict[str, Any]]:
    """Verify all citations against the approved section index and claim support."""

    checker = get_section or lookup_section
    return [verify_citation(c, checker) for c in citations]


def filter_supported_citations(
    citations: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split citations into supported vs rejected."""

    supported = []
    rejected = []
    for cite in citations:
        if cite.get("supports_claim") and cite.get("verification_status") == "found":
            supported.append(cite)
        else:
            rejected.append(cite)
    return supported, rejected


def citations_for_category(
    citations: list[dict[str, Any]],
    category: str,
    chapters: tuple[str, ...] | None = None,
    doc_ids: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    """Return citations belonging to a review category / chapter scope."""

    selected = []
    for cite in citations:
        if cite.get("review_category") == category:
            selected.append(cite)
            continue
        if chapters and cite.get("chapter") in chapters:
            selected.append(cite)
            continue
        if doc_ids and cite.get("source") in doc_ids and not chapters:
            selected.append(cite)
    # Preserve order, unique by section.
    seen: set[tuple[str, str]] = set()
    unique = []
    for cite in selected:
        key = (str(cite.get("source")), str(cite.get("section_number")))
        if key in seen:
            continue
        seen.add(key)
        unique.append(cite)
    return unique
