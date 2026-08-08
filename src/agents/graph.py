"""LangGraph workflow for the Austin site feasibility review."""

from langgraph.graph import END, START, StateGraph

from src.agents.nodes import (
    collect_site_context,
    drainage_review,
    historical_context_review,
    transportation_review,
    validate_input,
    water_wastewater_review,
    zoning_review,
)
from src.agents.state import AgentState
from src.agents.synthesis import synthesize_review
from src.guardrails.validate import apply_guardrails
from src.report.build import build_report


def route_after_validation(state: AgentState) -> str:
    """Stop invalid requests; continue valid requests."""

    if state.get("input_valid"):
        return "collect_site_context"

    return "apply_guardrails"


def build_review_graph():
    """Build and compile the Task 4–6 review workflow."""

    builder = StateGraph(AgentState)

    builder.add_node("validate_input", validate_input)
    builder.add_node("collect_site_context", collect_site_context)
    builder.add_node("zoning_review", zoning_review)
    builder.add_node("drainage_review", drainage_review)
    builder.add_node("transportation_review", transportation_review)
    builder.add_node("water_wastewater_review", water_wastewater_review)
    builder.add_node(
        "historical_context_review",
        historical_context_review,
    )
    builder.add_node("synthesize_review", synthesize_review)
    builder.add_node("apply_guardrails", apply_guardrails)
    builder.add_node("build_report", build_report)

    builder.add_edge(START, "validate_input")

    builder.add_conditional_edges(
        "validate_input",
        route_after_validation,
        {
            "collect_site_context": "collect_site_context",
            "apply_guardrails": "apply_guardrails",
        },
    )

    builder.add_edge("collect_site_context", "zoning_review")
    builder.add_edge("zoning_review", "drainage_review")
    builder.add_edge("drainage_review", "transportation_review")
    builder.add_edge("transportation_review", "water_wastewater_review")
    builder.add_edge(
        "water_wastewater_review",
        "historical_context_review",
    )
    builder.add_edge("historical_context_review", "synthesize_review")
    builder.add_edge("synthesize_review", "apply_guardrails")
    builder.add_edge("apply_guardrails", "build_report")
    builder.add_edge("build_report", END)

    return builder.compile()


review_graph = build_review_graph()
