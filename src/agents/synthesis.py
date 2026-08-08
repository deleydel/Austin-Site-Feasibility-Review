"""Final synthesis for the Task 4 agentic workflow."""

import json
import os

from langchain_openai import ChatOpenAI

from src.agents.state import AgentState

def build_synthesis_prompt(state: AgentState) -> str:
    """Build a grounded prompt from the completed workflow evidence."""

    payload = {
        "proposal": state.get("proposal", {}),
        "site_context": state.get("site_context", {}),
        "reviews": state.get("reviews", {}),
    }

    return (
        "You are reviewing preliminary development feasibility in Austin, Texas.\n"
        "Use only the supplied site data and regulatory evidence.\n"
        "Do not invent requirements, approvals, utility capacity, or facts.\n"
        "Treat nearby permits and cases as historical context only, not precedent.\n"
        "Clearly distinguish confirmed facts from unknowns requiring verification.\n"
        "Summarize major feasibility considerations, constraints, unknowns, "
        "and recommended next steps.\n\n"
        f"WORKFLOW DATA:\n{json.dumps(payload, default=str, indent=2)}"
    )

def generate_llm_synthesis(state: AgentState) -> str | None:
    """Generate an optional LLM synthesis when explicitly enabled."""

    if os.getenv("ENABLE_LLM_SYNTHESIS", "").lower() not in {
        "1",
        "true",
        "yes",
    }:
        return None

    if not os.getenv("OPENAI_API_KEY"):
        return None

    # Defaults are unchanged; the env vars let evaluation point the same node
    # at a local OpenAI-compatible endpoint (Ollama) instead of OpenAI.
    model = ChatOpenAI(
        model=os.getenv("SYNTHESIS_MODEL", "gpt-5.4-mini"),
        base_url=os.getenv("OPENAI_BASE_URL") or None,
        temperature=0,
    )

    response = model.invoke(build_synthesis_prompt(state))

    return str(response.content).strip()


def synthesize_review(state: AgentState) -> dict:
    """Combine all completed review categories into one structured result."""

    proposal = state.get("proposal", {})
    site_context = state.get("site_context", {})
    reviews = state.get("reviews", {})
    warnings = list(state.get("warnings", []))
    evidence = state.get("evidence", [])
    llm_synthesis = generate_llm_synthesis(state)

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
        "llm_synthesis": llm_synthesis,
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