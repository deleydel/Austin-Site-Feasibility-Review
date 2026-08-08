"""LangGraph node: build the export-ready report document after guardrails."""

from __future__ import annotations

from typing import Any

from src.report.schema import build_report_document


def build_report(state: dict[str, Any]) -> dict[str, Any]:
    """Create the structured report document from the guarded final_report."""

    final_report = state.get("final_report") or {}
    document = build_report_document(final_report)

    return {
        "report_document": document,
        "execution_trace": list(state.get("execution_trace", []))
        + ["build_report: completed"],
    }
