"""Citation extraction and verification against the regulatory index."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Callable

from src import config
from src.guardrails.sources import (
    is_approved_regulatory_source,
    normalize_regulatory_source,
)


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


def _passage_citation(passage: dict[str, Any]) -> dict[str, Any]:
    """Normalize a retriever hit into a citation record."""

    source = (
        passage.get("doc_id")
        or passage.get("source")
        or passage.get("source_name")
        or ""
    )
    section_number = passage.get("section_number") or ""
    return {
        "source": source,
        "source_name": passage.get("source_name") or source,
        "source_url": passage.get("source_url") or "",
        "chapter": passage.get("chapter") or "",
        "section_number": section_number,
        "section_title": passage.get("section_title") or "",
        "breadcrumb": passage.get("breadcrumb") or "",
        "chunk_id": passage.get("chunk_id"),
        "claim_support": "retrieved_passage",
    }


def extract_citations_from_evidence(
    evidence: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build unique citation records from retrieved evidence passages."""

    citations: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    for item in evidence or []:
        cite = _passage_citation(item)
        doc_id = normalize_regulatory_source(str(cite["source"])) or str(
            cite["source"]
        )
        key = (doc_id, str(cite["section_number"]), str(cite.get("chunk_id")))
        if key in seen:
            continue
        seen.add(key)
        cite["source"] = doc_id
        citations.append(cite)

    return citations


def verify_citation(
    citation: dict[str, Any],
    get_section: Callable[[str, str], dict],
) -> dict[str, Any]:
    """Verify one citation against the approved source list and section index.

    Status values:
      - verified: approved source and exact section found
      - ambiguous: approved source but multiple section matches
      - unapproved_source: source not on whitelist
      - missing_section: no section number to verify
      - not_found: section number not in index
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
    result["verification_status"] = status
    result["supports_claim"] = status == "found"

    if status == "found":
        match = (lookup.get("matches") or [{}])[0]
        result["section_title"] = (
            result.get("section_title")
            or match.get("section_title")
            or ""
        )
        result["source_url"] = (
            result.get("source_url")
            or match.get("source_url")
            or ""
        )
        result["verification_detail"] = "Section verified in regulatory index."
    elif status == "ambiguous":
        result["verification_detail"] = (
            "Multiple sections matched; citation requires manual verification."
        )
    else:
        result["verification_detail"] = (
            f"Section {section_number} not found in {doc_id}."
        )

    return result


def verify_citations(
    citations: list[dict[str, Any]],
    get_section: Callable[[str, str], dict] | None = None,
) -> list[dict[str, Any]]:
    """Verify all citations against the approved section index."""

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
