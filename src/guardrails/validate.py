"""Task 5 orchestration: apply all guardrails to agent workflow state."""

from __future__ import annotations

import re
from typing import Any

from src.guardrails.claims import (
    HISTORICAL_CONTEXT_NOTE,
    classify_site_findings,
    sanitize_text,
)
from src.guardrails.citations import (
    assess_claim_support,
    attach_review_context_to_evidence,
    extract_citations_from_evidence,
    filter_supported_citations,
    lookup_section,
    verify_citations,
)
from src.guardrails.privacy import scrub_value
from src.guardrails.scope import validate_scope
from src.guardrails.sources import (
    is_approved_regulatory_source,
    sources_consulted_entries,
)


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
    reviews = final_report.get("review_sections") or state.get("reviews") or {}

    enriched_evidence = attach_review_context_to_evidence(evidence, reviews)
    raw_citations = extract_citations_from_evidence(enriched_evidence)
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

    sanitized_reviews = {}
    for key, review in (reviews or {}).items():
        if not isinstance(review, dict):
            sanitized_reviews[key] = review
            continue
        item = dict(review)
        if key == "historical_context":
            # Always use the authored caution; never let model/user text replace it.
            item["note"] = HISTORICAL_CONTEXT_NOTE
        for field in ("note", "summary_text", "narrative", "query"):
            if key == "historical_context" and field == "note":
                continue
            if isinstance(item.get(field), str):
                cleaned, hits = sanitize_text(
                    item[field], append_revision_note=False
                )
                item[field] = cleaned
                unsupported_claims.extend(hits)
        # Retrieval queries echo applicant text (including injection attempts).
        # Keep them out of the reader-facing report payload.
        item.pop("query", None)
        if "retrieved_passages" in item:
            category_citations = [
                c for c in supported if c.get("review_category") == key
            ]
            # Fall back to chapter-scoped supported citations for this review.
            if not category_citations:
                category_citations = _passages_as_citations(
                    item.get("retrieved_passages") or [], supported
                )
            item["retrieved_passage_count"] = len(category_citations)
            item["retrieved_passages"] = [
                {
                    "doc_id": c.get("source") or c.get("doc_id"),
                    "section_number": c.get("section_number"),
                    "section_title": c.get("section_title"),
                    "chapter": c.get("chapter"),
                    "source_url": c.get("source_url"),
                    "breadcrumb": c.get("breadcrumb"),
                    "support_score": c.get("support_score"),
                }
                for c in category_citations[:5]
            ]
        sanitized_reviews[key] = item

    # Prefer citations that actually support sentences in the synthesis text.
    if isinstance(final_report.get("llm_synthesis"), str):
        linked = _citations_supporting_text(
            final_report["llm_synthesis"], supported
        )
        if linked:
            supported = linked

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
                    "as supporting the associated claim or retrieval context."
                ),
            }
        )

    if not supported:
        findings.append(
            {
                "category": "regulatory_evidence",
                "label": "insufficient information",
                "detail": (
                    "No verified, claim-supporting regulatory citations were "
                    "available for one or more review categories."
                ),
            }
        )

    site_summary = _site_summary_from_context(site_context)

    # Sanitize synthesis again after any residual phrases; also scrub project
    # description echoes of injection only in asserted narrative fields.
    if isinstance(final_report.get("llm_synthesis"), str):
        cleaned, hits = sanitize_text(final_report["llm_synthesis"])
        final_report["llm_synthesis"] = cleaned
        unsupported_claims.extend(hits)

    # Drop internal retrieval/support fields that can re-assert banned phrases.
    export_citations = [_export_citation(c) for c in supported]
    export_rejected = [_export_citation(c) for c in rejected]

    guarded_report = {
        "status": "validated",
        "project": {
            "address": proposal.get("address"),
            "proposed_land_use": proposal.get("proposed_land_use"),
            "development_description": proposal.get("development_description"),
            "units": proposal.get("units"),
            "site_area_acres": proposal.get("site_area_acres"),
        },
        "site_summary": site_summary,
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
        "citations": export_citations,
        "rejected_citations": export_rejected,
        "llm_synthesis": final_report.get("llm_synthesis"),
        # Never echo the forbidden phrase text back into the report payload;
        # that alone fails Task 7 forbidden-phrase checks.
        "unsupported_claims": _redact_unsupported_claims(unsupported_claims),
        "warnings": _dedupe(warnings),
        "regulatory_evidence_count": len(evidence),
        "verified_citation_count": len(supported),
        "disclaimer": _disclaimer(),
    }

    # Final whole-report pass so LLM paraphrases in nested fields are caught.
    guarded_report, more_hits = _sanitize_report_strings(guarded_report)
    if more_hits:
        warnings.append(
            "Additional unsupported definitive phrasing was removed from "
            "report text after validation."
        )
        guarded_report["warnings"] = _dedupe(warnings)
        existing = list(guarded_report.get("unsupported_claims") or [])
        existing.extend(_redact_unsupported_claims(more_hits))
        guarded_report["unsupported_claims"] = existing
    guarded_report = scrub_value(guarded_report)

    return {
        "final_report": guarded_report,
        "citations": supported,
        "warnings": guarded_report.get("warnings") or warnings,
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


def _passages_as_citations(
    passages: list[dict[str, Any]],
    supported: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_key = {
        (str(c.get("source")), str(c.get("section_number"))): c for c in supported
    }
    out = []
    for p in passages:
        if not is_approved_regulatory_source(str(p.get("doc_id") or "")):
            continue
        key = (str(p.get("doc_id")), str(p.get("section_number")))
        if key in by_key:
            out.append(by_key[key])
    return out


def _citations_supporting_text(
    text: str,
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Keep citations that support at least one sentence in ``text``."""

    if not text or not candidates:
        return candidates

    sentences = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", text)
        if len(s.strip()) >= 40
    ]
    if not sentences:
        return candidates

    kept: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for sentence in sentences[:12]:
        best = None
        best_score = 0.0
        for cite in candidates:
            section = lookup_section(
                str(cite.get("source") or ""),
                str(cite.get("section_number") or ""),
            )
            if section.get("status") != "found":
                continue
            match = (section.get("matches") or [{}])[0]
            support = assess_claim_support(
                sentence,
                str(match.get("text") or ""),
                section_title=str(
                    cite.get("section_title") or match.get("section_title") or ""
                ),
                require_number_agreement=True,
            )
            score = float(support.get("support_score") or 0.0)
            if support.get("supports_claim") and score > best_score:
                best = dict(cite)
                best["support_score"] = score
                best["supported_claim"] = sentence
                best["claim_support"] = "supported"
                best_score = score
        if best:
            key = (str(best.get("source")), str(best.get("section_number")))
            if key not in seen:
                seen.add(key)
                kept.append(best)

    # Fall back to original supported list if linking found nothing usable.
    return kept or candidates


def _sanitize_report_strings(
    report: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Sanitize free-text fields while leaving structured ids untouched."""

    hits: list[dict[str, str]] = []
    skip_keys = {
        "address",
        "proposed_land_use",
        "development_description",
        "source_url",
        "url",
        "id",
        "status",
        "label",
        "category",
        "section_number",
        "chunk_id",
        "doc_id",
        "source",
        "chapter",
        "breadcrumb",
        "generated",
        "snapshot_date",
    }

    def walk(value: Any, key: str | None = None) -> Any:
        nonlocal hits
        if isinstance(value, str):
            if key in skip_keys:
                return value
            # Preserve authored historical caution and disclaimer.
            if value == HISTORICAL_CONTEXT_NOTE or key == "disclaimer":
                return value
            cleaned, found = sanitize_text(
                value, append_revision_note=False
            )
            hits.extend(found)
            return cleaned
        if isinstance(value, list):
            return [walk(v, key) for v in value]
        if isinstance(value, dict):
            return {k: walk(v, k) for k, v in value.items()}
        return value

    return walk(report), hits


def _site_summary_from_context(site_context: dict[str, Any]) -> dict[str, Any]:
    """Build site summary without unsupported single-zoning claims."""

    zoning = site_context.get("zoning", {}) or {}
    floodplain = site_context.get("floodplain", {}) or {}
    watershed = site_context.get("watershed", {}) or {}
    z_status = zoning.get("status")

    # Only an exact single match may populate reported_zoning.
    reported_zoning = zoning.get("zoning") if z_status == "found" else None

    summary = {
        "reported_zoning": reported_zoning,
        "zoning_status": z_status,
        "zoning_note": (
            "Preliminary Open Data zoning only; not an official determination."
            if z_status == "found"
            else (
                "No single zoning designation is stated because the lookup was "
                f"'{z_status}'."
                if z_status
                else "Zoning could not be confirmed."
            )
        ),
        "floodplain_intersection": floodplain.get("intersects_floodplain"),
        "watershed": watershed.get("watershed"),
    }
    if z_status == "multiple_records":
        summary["zoning_designations"] = zoning.get("zoning_designations") or []
    return summary


def _disclaimer() -> str:
    return (
        "This is a preliminary site-feasibility screening only. "
        "It is not an official zoning determination, code-compliance "
        "decision, development approval, or guarantee of utility service. "
        "Nearby permits and cases are historical context only and are not "
        "approval precedent. All findings require verification by qualified "
        "professionals and City of Austin authorities."
    )


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _redact_unsupported_claims(
    hits: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Keep claim-type metadata without repeating the banned phrase text."""

    redacted = []
    seen: set[str] = set()
    for hit in hits:
        claim_type = str(hit.get("claim_type") or "unsupported_claim")
        if claim_type in seen:
            continue
        seen.add(claim_type)
        redacted.append(
            {
                "claim_type": claim_type,
                "action": "removed_or_revised",
                "match": "[REDACTED]",
            }
        )
    return redacted


def _export_citation(citation: dict[str, Any]) -> dict[str, Any]:
    """Strip internal support-context fields from export-facing citations."""

    return {
        "source": citation.get("source"),
        "source_name": citation.get("source_name"),
        "source_url": citation.get("source_url"),
        "chapter": citation.get("chapter"),
        "section_number": citation.get("section_number"),
        "section_title": citation.get("section_title"),
        "breadcrumb": citation.get("breadcrumb"),
        "verification_status": citation.get("verification_status"),
        "supports_claim": citation.get("supports_claim"),
        "claim_support": citation.get("claim_support"),
        "support_score": citation.get("support_score"),
        "review_category": citation.get("review_category"),
    }
