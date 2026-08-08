"""Shared state definitions for the Task 4 LangGraph workflow."""

from typing import Any, TypedDict


class ProposalInput(TypedDict, total=False):
    """Information supplied by the user about the proposed development."""

    address: str
    proposed_land_use: str
    development_description: str
    units: int | None
    site_area_acres: float | None
    latitude: float | None
    longitude: float | None


class AgentState(TypedDict, total=False):
    """Shared state passed between all Task 4 workflow nodes."""

    proposal: ProposalInput

    input_valid: bool
    stop_reason: str | None

    site_context: dict[str, Any]
    reviews: dict[str, dict[str, Any]]

    evidence: list[dict[str, Any]]
    citations: list[dict[str, Any]]

    warnings: list[str]
    missing_information: list[str]

    execution_trace: list[str]

    final_report: dict[str, Any]
    guardrail_result: dict[str, Any]
    report_document: dict[str, Any]