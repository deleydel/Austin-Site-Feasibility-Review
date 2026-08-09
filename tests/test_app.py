"""Tests for Task 8: Streamlit frontend logic (non-widget helpers)."""

from __future__ import annotations

from app.streamlit_app import WORKFLOW_STEPS, _export_bytes, _finding_text, run_review


def _sample_proposal() -> dict:
    return {
        "address": "301 W 2nd St, Austin, TX 78701",
        "proposed_land_use": "multifamily residential",
        "development_description": "A 4-story multifamily building with ground floor retail.",
        "units": 40,
        "site_area_acres": 0.75,
        "latitude": None,
        "longitude": None,
    }


def test_run_review_valid_proposal_produces_report_document():
    result = run_review(_sample_proposal())

    assert result.get("input_valid") is True
    document = result.get("report_document") or {}
    assert document.get("schema_complete") is True
    assert "sections" in document


def test_run_review_missing_fields_is_blocked():
    result = run_review({"address": "", "proposed_land_use": ""})

    assert result.get("input_valid") is False
    assert "address" in (result.get("missing_information") or [])
    assert "proposed_land_use" in (result.get("missing_information") or [])


def test_run_review_out_of_scope_location_is_blocked():
    result = run_review(
        {"address": "Dallas, TX", "proposed_land_use": "retail"}
    )

    assert result.get("input_valid") is False
    assert result.get("stop_reason")


def test_export_bytes_supports_docx_and_pdf():
    result = run_review(_sample_proposal())
    document = result["report_document"]

    docx_bytes = _export_bytes(document, "docx")
    pdf_bytes = _export_bytes(document, "pdf")

    assert docx_bytes.startswith(b"PK")  # docx is a zip archive
    assert pdf_bytes.startswith(b"%PDF")


def test_finding_text_handles_dict_and_plain_items():
    assert _finding_text({"text": "Confirm drainage easement"}) == (
        "Confirm drainage easement"
    )
    assert _finding_text({"description": "Verify utility capacity"}) == (
        "Verify utility capacity"
    )
    assert _finding_text("plain string finding") == "plain string finding"


def test_workflow_steps_cover_all_graph_nodes():
    labels = [key for key, _ in WORKFLOW_STEPS]
    assert labels == [
        "validate_input",
        "collect_site_context",
        "zoning_review",
        "drainage_review",
        "transportation_review",
        "water_wastewater_review",
        "historical_context_review",
        "synthesize_review",
        "apply_guardrails",
        "build_report",
    ]
