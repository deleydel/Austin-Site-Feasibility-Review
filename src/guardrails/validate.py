"""Task 5 orchestration: apply all guardrails to agent workflow state."""

from __future__ import annotations

from typing import Any

from src.guardrails.claims import (
    classify_site_findings,
    sanitize_text,
)
from src.guardrails.citations import (
    extract_citations_from_evidence,
    filter_supported_citations,
    verify_citations,
)
from src.guardrails.privacy import scrub_value
from src.guardrails.scope import validate_scope
from src.guardrails.sources import sources_consulted_entries


def apply_guardrails(state: dict[str, Any]) -> dict[str, Any]:
    """Validate synthesis outputs and produce a guarded final report payload.

    Intended as a LangGraph node after ``synthesize_review``.
    """

    proposal = state.get("proposal", {}) or {}
    scope = validate_scope(proposal)

    warnings = list(state.get("warnings", []) or [])
    warnings.extend(scope.get("warnings", []))

    if not state.get("input_valid", True) or not scope.get("ok", True):
        reason = state.get("stop_reason") or scope.get("reason") or (
            "Request failed scope or input validation."
        )
        guarded = {
            "status": "blocked",
            "stop_reason": reason,
            "project": {
                "address": proposal.get("address"),
                "proposed_land_use": proposal.get("proposed_land_use"),
            },
            "findings": [
                {
                    "category": "scope",
                    "label": "insufficient information",
                    "detail": reason,
                }
            ],
            "citations": [],
            "unsupported_claims": [],
            "sources_consulted": sources_consulted_entries(),
            "disclaimer": _disclaimer(),
        }
        return {
            "final_report": scrub_value(guarded),
            "citations": [],
            "warnings": warnings,
            "guardrail_result": {
                "status": "blocked",
                "scope_ok": scope.get("ok", False),
                "unsupported_request": scope.get("unsupported_request", False),
                "citations_verified": 0,
                "citations_rejected": 0,
                "unsupported_claim_count": 0,
            },
            "execution_trace": list(state.get("execution_trace", []))
            + ["apply_guardrails: blocked"],
        }

    final_report = dict(state.get("final_report", {}) or {})
    evidence = list(state.get("evidence", []) or [])
    site_context = state.get("site_context", {}) or {}

    raw_citations = extract_citations_from_evidence(evidence)
    verified = verify_citations(raw_citations)
    supported, rejected = filter_supported_citations(verified)

    unsupported_claims: list[dict[str, Any]] = []
    llm_text = final_report.get("llm_synthesis")
    if isinstance(llm_text, str) and llm_text.strip():
        cleaned, hits = sanitize_text(llm_text)
        unsupported_claims.extend(hits)
        final_report["llm_synthesis"] = cleaned
        if hits:
            warnings.append(
                "LLM synthesis contained unsupported definitive claims; "
                "those statements were revised or labeled for verification."
            )

    # Also sanitize free-text notes inside review sections.
    reviews = final_report.get("review_sections") or state.get("reviews") or {}
    sanitized_reviews = {}
    for key, review in (reviews or {}).items():
        if not isinstance(review, dict):
            sanitized_reviews[key] = review
            continue
        item = dict(review)
        for field in ("note", "summary_text", "narrative"):
            if isinstance(item.get(field), str):
                cleaned, hits = sanitize_text(item[field])
                item[field] = cleaned
                unsupported_claims.extend(hits)
        # Drop raw passage bodies from the export-facing report; keep citations.
        if "retrieved_passages" in item:
            item["retrieved_passage_count"] = len(item.get("retrieved_passages") or [])
            item["retrieved_passages"] = [
                {
                    "doc_id": p.get("doc_id"),
                    "section_number": p.get("section_number"),
                    "section_title": p.get("section_title"),
                    "chapter": p.get("chapter"),
                    "source_url": p.get("source_url"),
                    "breadcrumb": p.get("breadcrumb"),
                }
                for p in (item.get("retrieved_passages") or [])
                if is_passage_approved(p)
            ]
        sanitized_reviews[key] = item

    findings = classify_site_findings(site_context)
    if rejected:
        warnings.append(
            f"{len(rejected)} citation(s) failed verification and were "
            "excluded from supported regulatory citations."
        )
        findings.append(
            {
                "category": "citations",
                "label": "verification required",
                "detail": (
                    "One or more retrieved citations could not be verified "
                    "against the approved regulatory index."
                ),
            }
        )

    if not supported:
        findings.append(
            {
                "category": "regulatory_evidence",
                "label": "insufficient information",
                "detail": (
                    "No verified regulatory citations were available for "
                    "one or more review categories."
                ),
            }
        )

    guarded_report = {
        "status": "validated",
        "project": final_report.get("project")
        or {
            "address": proposal.get("address"),
            "proposed_land_use": proposal.get("proposed_land_use"),
            "development_description": proposal.get("development_description"),
            "units": proposal.get("units"),
            "site_area_acres": proposal.get("site_area_acres"),
        },
        "site_summary": final_report.get("site_summary")
        or _site_summary_from_context(site_context),
        "sources_consulted": sources_consulted_entries(),
        "review_sections": sanitized_reviews,
        "findings": findings,
        "potential_constraints": [
            f for f in findings if f.get("label") == "potential constraint"
        ],
        "missing_information": list(state.get("missing_information", []) or []),
        "required_verification": [
            f for f in findings if f.get("label") == "verification required"
        ],
        "citations": supported,
        "rejected_citations": rejected,
        "llm_synthesis": final_report.get("llm_synthesis"),
        "unsupported_claims": unsupported_claims,
        "warnings": warnings,
        "regulatory_evidence_count": len(evidence),
        "verified_citation_count": len(supported),
        "disclaimer": final_report.get("disclaimer") or _disclaimer(),
    }

    guarded_report = scrub_value(guarded_report)

    return {
        "final_report": guarded_report,
        "citations": supported,
        "warnings": warnings,
        "guardrail_result": {
            "status": "validated",
            "scope_ok": True,
            "unsupported_request": False,
            "citations_verified": len(supported),
            "citations_rejected": len(rejected),
            "unsupported_claim_count": len(unsupported_claims),
            "finding_count": len(findings),
        },
        "execution_trace": list(state.get("execution_trace", []))
        + ["apply_guardrails: completed"],
    }


def is_passage_approved(passage: dict[str, Any]) -> bool:
    """True when a retrieved passage cites an approved regulatory source."""

    from src.guardrails.sources import is_approved_regulatory_source

    source = passage.get("doc_id") or passage.get("source") or ""
    return is_approved_regulatory_source(str(source))


def _site_summary_from_context(site_context: dict[str, Any]) -> dict[str, Any]:
    zoning = site_context.get("zoning", {}) or {}
    floodplain = site_context.get("floodplain", {}) or {}
    watershed = site_context.get("watershed", {}) or {}
    return {
        "reported_zoning": zoning.get("zoning"),
        "zoning_status": zoning.get("status"),
        "floodplain_intersection": floodplain.get("intersects_floodplain"),
        "watershed": watershed.get("watershed"),
    }


def _disclaimer() -> str:
    return (
        "This is a preliminary site-feasibility screening only. "
        "It is not an official zoning determination, code-compliance "
        "decision, development approval, or guarantee of utility service. "
        "All findings require verification by qualified professionals and "
        "City of Austin authorities."
    )
