"""Tests for Task 6: report schema, formatting, and export."""

from __future__ import annotations

from pathlib import Path

from src.report.export import export_report, render_report_html
from src.report.schema import REQUIRED_SECTIONS, build_report_document
from src.report.template import format_citation, render_report_markdown


def _sample_final_report() -> dict:
    return {
        "status": "validated",
        "project": {
            "address": "1714 Madison Avenue, Austin, TX",
            "proposed_land_use": "Multifamily residential",
            "development_description": "Proposed 40-unit multifamily project",
            "units": 40,
            "site_area_acres": 1.2,
        },
        "site_summary": {
            "reported_zoning": "SF-3-NP",
            "zoning_status": "found",
            "floodplain_intersection": False,
            "watershed": "Waller Creek",
        },
        "sources_consulted": [
            {
                "id": "ldc_title_25",
                "name": "Austin Land Development Code, Title 25",
                "url": "https://example.com/ldc",
                "limitations": "Snapshot export",
            }
        ],
        "review_sections": {
            "zoning_site_plan": {
                "query": "zoning requirements",
                "retrieved_passages": [
                    {
                        "doc_id": "LDC",
                        "section_number": "25-2-492",
                        "section_title": "SITE DEVELOPMENT REGULATIONS",
                        "chapter": "Chapter 25-2",
                    }
                ],
                "retrieved_passage_count": 1,
            },
            "drainage_environmental": {
                "retrieved_passages": [],
                "retrieved_passage_count": 0,
            },
            "transportation_access": {
                "retrieved_passages": [],
                "retrieved_passage_count": 0,
            },
            "water_wastewater": {
                "note": "Utility capacity requires verification.",
                "retrieved_passages": [],
                "retrieved_passage_count": 0,
            },
            "historical_context": {
                "summary": {
                    "permit_count": 2,
                    "site_plan_count": 1,
                    "plan_review_count": 0,
                },
                "note": "Historical context only.",
            },
        },
        "findings": [
            {
                "category": "zoning",
                "label": "verification required",
                "detail": "Open Data zoning requires official verification.",
            }
        ],
        "potential_constraints": [],
        "missing_information": [],
        "required_verification": [
            {
                "category": "zoning",
                "label": "verification required",
                "detail": "Open Data zoning requires official verification.",
            }
        ],
        "citations": [
            {
                "source": "LDC",
                "section_number": "25-2-492",
                "section_title": "SITE DEVELOPMENT REGULATIONS",
                "chapter": "Chapter 25-2",
                "source_url": "https://example.com/ldc",
                "supports_claim": True,
                "verification_status": "found",
            }
        ],
        "warnings": ["Address does not explicitly mention Austin or Texas"],
        "verified_citation_count": 1,
        "regulatory_evidence_count": 1,
        "unsupported_claims": [],
        "disclaimer": (
            "This is a preliminary site-feasibility screening only."
        ),
    }


def test_build_report_has_required_sections():
    document = build_report_document(_sample_final_report())
    assert document["schema_complete"] is True
    assert document["missing_sections"] == []
    for key in REQUIRED_SECTIONS:
        assert key in document["sections"]
        assert document["sections"][key]["heading"]


def test_format_citation_and_markdown():
    cite = format_citation(
        {
            "source": "LDC",
            "section_number": "25-2-492",
            "section_title": "SITE DEVELOPMENT REGULATIONS",
            "chapter": "Chapter 25-2",
            "source_url": "https://example.com/ldc",
        }
    )
    assert "25-2-492" in cite
    assert "LDC" in cite

    document = build_report_document(_sample_final_report())
    md = render_report_markdown(document)
    assert "Preliminary Development Feasibility Report" in md
    assert "Source Citations" in md
    assert "Preliminary-Review Disclaimer" in md
    assert "1714 Madison Avenue" in md


def test_export_html_docx_pdf(tmp_path: Path):
    report = _sample_final_report()
    html_path = export_report(report, tmp_path / "report.html")
    docx_path = export_report(report, tmp_path / "report.docx")
    pdf_path = export_report(report, tmp_path / "report.pdf")
    md_path = export_report(report, tmp_path / "report.md")

    assert html_path.exists() and html_path.stat().st_size > 100
    assert docx_path.exists() and docx_path.stat().st_size > 1000
    assert pdf_path.exists() and pdf_path.stat().st_size > 500
    assert md_path.exists()

    html = render_report_html(build_report_document(report))
    assert "<!DOCTYPE html>" in html
    assert "1714 Madison Avenue" in html
