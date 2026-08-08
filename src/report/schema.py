"""Structured schema for the Preliminary Development Feasibility Report."""

from __future__ import annotations

from datetime import date
from typing import Any

from src.report.template import format_citation

REPORT_TITLE = "Preliminary Development Feasibility Report"

REQUIRED_SECTIONS = (
    "project_and_site",
    "sources_consulted",
    "zoning_and_land_use",
    "site_plan_considerations",
    "drainage_flood_environmental",
    "transportation_access",
    "water_wastewater",
    "historical_permit_case_context",
    "potential_constraints",
    "missing_information_and_verification",
    "source_citations",
    "disclaimer",
)


def build_report_document(final_report: dict[str, Any]) -> dict[str, Any]:
    """Normalize a guarded ``final_report`` into the export schema.

    The LLM/agent produces content; this function only structures it for
    deterministic templating and file export.
    """

    project = final_report.get("project") or {}
    site = final_report.get("site_summary") or {}
    reviews = final_report.get("review_sections") or {}
    findings = final_report.get("findings") or []
    citations = final_report.get("citations") or []
    sources = final_report.get("sources_consulted") or []

    zoning_review = reviews.get("zoning_site_plan") or {}
    drainage_review = reviews.get("drainage_environmental") or {}
    transport_review = reviews.get("transportation_access") or {}
    water_review = reviews.get("water_wastewater") or {}
    historical = reviews.get("historical_context") or {}

    document = {
        "title": REPORT_TITLE,
        "generated_date": date.today().isoformat(),
        "status": final_report.get("status", "validated"),
        "sections": {
            "project_and_site": {
                "heading": "Project and Site Description",
                "project": project,
                "site_summary": site,
                "llm_synthesis": final_report.get("llm_synthesis"),
            },
            "sources_consulted": {
                "heading": "Sources Consulted",
                "items": sources,
            },
            "zoning_and_land_use": {
                "heading": "Zoning and Land-Use Context",
                "reported_zoning": site.get("reported_zoning"),
                "zoning_status": site.get("zoning_status"),
                "review": _compact_review(zoning_review),
            },
            "site_plan_considerations": {
                "heading": "Site-Plan Considerations",
                "review": _compact_review(zoning_review),
                "note": (
                    "Site-plan applicability depends on proposed use, zoning, "
                    "and project characteristics; confirm with Development Services."
                ),
            },
            "drainage_flood_environmental": {
                "heading": "Drainage, Flood, and Environmental Considerations",
                "floodplain_intersection": site.get("floodplain_intersection"),
                "watershed": site.get("watershed"),
                "review": _compact_review(drainage_review),
            },
            "transportation_access": {
                "heading": "Transportation and Access Considerations",
                "review": _compact_review(transport_review),
            },
            "water_wastewater": {
                "heading": "General Water and Wastewater Considerations",
                "review": _compact_review(water_review),
                "note": water_review.get("note")
                or (
                    "Regulatory language does not establish utility service "
                    "availability or capacity."
                ),
            },
            "historical_permit_case_context": {
                "heading": "Historical Permit and Case Context",
                "review": {
                    "summary": historical.get("summary"),
                    "note": historical.get("note"),
                },
            },
            "potential_constraints": {
                "heading": "Potential Constraints",
                "items": final_report.get("potential_constraints")
                or [
                    f
                    for f in findings
                    if f.get("label") == "potential constraint"
                ],
            },
            "missing_information_and_verification": {
                "heading": "Missing Information and Required Verification",
                "missing_information": final_report.get("missing_information")
                or [],
                "required_verification": final_report.get("required_verification")
                or [
                    f
                    for f in findings
                    if f.get("label") == "verification required"
                ],
                "findings": findings,
                "warnings": final_report.get("warnings") or [],
            },
            "source_citations": {
                "heading": "Source Citations",
                "items": [format_citation(c) for c in citations],
                "raw": citations,
            },
            "disclaimer": {
                "heading": "Preliminary-Review Disclaimer",
                "text": final_report.get("disclaimer")
                or (
                    "This is a preliminary site-feasibility screening only."
                ),
            },
        },
        "metrics": {
            "verified_citation_count": final_report.get(
                "verified_citation_count", len(citations)
            ),
            "regulatory_evidence_count": final_report.get(
                "regulatory_evidence_count", 0
            ),
            "unsupported_claim_count": len(
                final_report.get("unsupported_claims") or []
            ),
        },
    }

    missing = [s for s in REQUIRED_SECTIONS if s not in document["sections"]]
    document["schema_complete"] = not missing
    document["missing_sections"] = missing
    return document


def _compact_review(review: dict[str, Any]) -> dict[str, Any]:
    if not review:
        return {}
    return {
        "query": review.get("query"),
        "note": review.get("note"),
        "retrieved_passage_count": review.get("retrieved_passage_count")
        or len(review.get("retrieved_passages") or []),
        "passages": review.get("retrieved_passages") or [],
    }
