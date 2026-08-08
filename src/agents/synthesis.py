"""Final synthesis for the Task 4 agentic workflow."""

from src.agents.state import AgentState


def synthesize_review(state: AgentState) -> dict:
    """Combine all completed review categories into one structured result."""

    proposal = state.get("proposal", {})
    site_context = state.get("site_context", {})
    reviews = state.get("reviews", {})
    warnings = list(state.get("warnings", []))
    evidence = state.get("evidence", [])

    zoning = site_context.get("zoning", {})
    floodplain = site_context.get("floodplain", {})
    watershed = site_context.get("watershed", {})

    final_report = {
        "project": {
            "address": proposal.get("address"),
            "proposed_land_use": proposal.get("proposed_land_use"),
            "development_description": proposal.get(
                "development_description"
            ),
            "units": proposal.get("units"),
            "site_area_acres": proposal.get("site_area_acres"),
        },
        "site_summary": {
            "reported_zoning": zoning.get("zoning"),
            "zoning_status": zoning.get("status"),
            "floodplain_intersection": floodplain.get(
                "intersects_floodplain"
            ),
            "watershed": watershed.get("watershed"),
        },
        "review_sections": reviews,
        "warnings": warnings,
        "regulatory_evidence_count": len(evidence),
        "disclaimer": (
            "This is a preliminary site-feasibility screening only. "
            "It is not an official zoning determination, code-compliance "
            "decision, development approval, or guarantee of utility service."
        ),
    }

    return {
        "final_report": final_report,
        "execution_trace": list(state.get("execution_trace", []))
        + ["synthesize_review: completed"],
    }