"""Structured schema for the Preliminary Development Feasibility Report."""

from __future__ import annotations

from datetime import date
from typing import Any

from src.guardrails.claims import HISTORICAL_CONTEXT_NOTE
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

_ZONING_CHAPTERS = ("Chapter 25-1", "Chapter 25-2")
_SITE_PLAN_CHAPTERS = ("Chapter 25-5",)
_DRAINAGE_CHAPTERS = ("Chapter 25-7", "Chapter 25-8", "Section 1", "Section 2",
                      "Section 8", "Appendix E")
_TRANSPORT_CHAPTERS = ("Chapter 25-6", "Section 1", "Section 7", "Section 9",
                       "Section 10")
_WATER_CHAPTERS = ("Chapter 25-9",)


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

    zoning_passages = _section_passages(
        zoning_review, citations, chapters=_ZONING_CHAPTERS,
        category="zoning_site_plan",
    )
    site_plan_passages = _section_passages(
        zoning_review, citations, chapters=_SITE_PLAN_CHAPTERS,
        category="zoning_site_plan",
    )
    drainage_passages = _section_passages(
        drainage_review, citations, chapters=_DRAINAGE_CHAPTERS,
        category="drainage_environmental",
    )
    transport_passages = _section_passages(
        transport_review, citations, chapters=_TRANSPORT_CHAPTERS,
        category="transportation_access",
    )
    water_passages = _section_passages(
        water_review, citations, chapters=_WATER_CHAPTERS,
        category="water_wastewater",
    )

    document = {
        "title": REPORT_TITLE,
        "generated_date": date.today().isoformat(),
        "status": final_report.get("status", "validated"),
        "sections": {
            "project_and_site": {
                "heading": "Project and Site Description",
                "project": {
                    "address": project.get("address"),
                    "proposed_land_use": project.get("proposed_land_use"),
                    "development_description": project.get(
                        "development_description"
                    ),
                    "units": project.get("units"),
                    "site_area_acres": project.get("site_area_acres"),
                },
                "site_summary": site,
                # Keep synthesis only here; do not repeat it in later sections.
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
                "zoning_note": site.get("zoning_note")
                or (
                    "Preliminary Open Data zoning only; not an official "
                    "determination."
                ),
                "review": {
                    "note": (
                        "Zoning context is preliminary. Designations are stated "
                        "only when the lookup returns an exact single match."
                    ),
                    "retrieved_passage_count": len(zoning_passages),
                    "passages": zoning_passages,
                },
            },
            "site_plan_considerations": {
                "heading": "Site-Plan Considerations",
                "review": {
                    "note": (
                        "Site-plan applicability depends on proposed use, zoning, "
                        "and project characteristics; confirm with Development "
                        "Services. Citations below are limited to site-plan "
                        "provisions (LDC Chapter 25-5) when available."
                    ),
                    "retrieved_passage_count": len(site_plan_passages),
                    "passages": site_plan_passages,
                },
            },
            "drainage_flood_environmental": {
                "heading": "Drainage, Flood, and Environmental Considerations",
                "floodplain_intersection": site.get("floodplain_intersection"),
                "watershed": site.get("watershed"),
                "review": {
                    "note": drainage_review.get("note"),
                    "retrieved_passage_count": len(drainage_passages),
                    "passages": drainage_passages,
                },
            },
            "transportation_access": {
                "heading": "Transportation and Access Considerations",
                "review": {
                    "note": transport_review.get("note"),
                    "retrieved_passage_count": len(transport_passages),
                    "passages": transport_passages,
                },
            },
            "water_wastewater": {
                "heading": "General Water and Wastewater Considerations",
                "review": {
                    "retrieved_passage_count": len(water_passages),
                    "passages": water_passages,
                },
                "note": (
                    "Regulatory language does not establish utility service "
                    "availability or capacity. Verification with the appropriate "
                    "utility authority is required."
                ),
            },
            "historical_permit_case_context": {
                "heading": "Historical Permit and Case Context",
                "review": {
                    "summary": historical.get("summary"),
                    "note": HISTORICAL_CONTEXT_NOTE,
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
                # Avoid repeating the full findings list already shown above.
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
                    "This is a preliminary site-feasibility screening only. "
                    "It is not an official zoning determination, code-compliance "
                    "decision, development approval, or guarantee of utility "
                    "service. Nearby permits and cases are historical context "
                    "only and are not approval precedent."
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


def _section_passages(
    review: dict[str, Any],
    citations: list[dict[str, Any]],
    *,
    chapters: tuple[str, ...],
    category: str,
) -> list[dict[str, Any]]:
    """Citations for one report section only — no cross-section reuse."""

    selected: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def add(cite: dict[str, Any]) -> None:
        key = (
            str(cite.get("source") or cite.get("doc_id") or ""),
            str(cite.get("section_number") or ""),
        )
        if not key[0] or not key[1] or key in seen:
            return
        seen.add(key)
        selected.append(
            {
                "doc_id": cite.get("source") or cite.get("doc_id"),
                "section_number": cite.get("section_number"),
                "section_title": cite.get("section_title"),
                "chapter": cite.get("chapter"),
                "source_url": cite.get("source_url"),
                "breadcrumb": cite.get("breadcrumb"),
            }
        )

    for cite in citations:
        if cite.get("review_category") == category and cite.get("chapter") in chapters:
            add(cite)
    if not selected:
        for cite in citations:
            if cite.get("chapter") in chapters:
                add(cite)
    if not selected:
        for passage in review.get("retrieved_passages") or []:
            if passage.get("chapter") in chapters:
                add(passage)

    return selected[:5]
