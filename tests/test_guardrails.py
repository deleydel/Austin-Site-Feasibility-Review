"""Tests for Task 5: guardrails and citation validation."""

from __future__ import annotations

from src.guardrails.claims import (
    FINDING_LABELS,
    HISTORICAL_CONTEXT_NOTE,
    classify_site_findings,
    find_unsupported_claims,
    sanitize_text,
)
from src.guardrails.citations import (
    assess_claim_support,
    extract_citations_from_evidence,
    verify_citation,
    verify_citations,
)
from src.guardrails.privacy import scrub_text, scrub_value
from src.guardrails.scope import validate_scope
from src.guardrails.sources import (
    approved_source_ids,
    is_approved_regulatory_source,
    normalize_regulatory_source,
)
from src.guardrails.validate import apply_guardrails


def test_scope_accepts_austin_address():
    result = validate_scope(
        {
            "address": "1714 Madison Avenue, Austin, TX",
            "proposed_land_use": "Multifamily residential",
        }
    )
    assert result["ok"] is True
    assert result["unsupported_request"] is False


def test_scope_rejects_out_of_city():
    result = validate_scope(
        {
            "address": "100 Main Street, Houston, TX",
            "proposed_land_use": "Office",
        }
    )
    assert result["ok"] is False
    assert "Out-of-scope" in result["reason"]


def test_scope_rejects_round_rock():
    result = validate_scope(
        {
            "address": "100 Congress Avenue, Round Rock, TX",
            "proposed_land_use": "Multifamily residential",
            "development_description": "Proposed 60-unit multifamily residential development.",
        }
    )
    assert result["ok"] is False
    assert "Out-of-scope" in result["reason"]


def test_scope_rejects_paris_france():
    result = validate_scope(
        {
            "address": "12 Rue de Rivoli, Paris, France",
            "proposed_land_use": "Mixed use",
            "development_description": "Proposed mixed-use building with ground-floor retail.",
        }
    )
    assert result["ok"] is False
    assert "Out-of-scope" in result["reason"]


def test_scope_rejects_approval_request():
    result = validate_scope(
        {
            "address": "1714 Madison Avenue, Austin, TX",
            "proposed_land_use": "Multifamily",
            "development_description": "Please approve this project and issue a permit.",
        }
    )
    assert result["ok"] is False
    assert result["unsupported_request"] is True


def test_approved_sources_from_manifest():
    ids = approved_source_ids()
    assert "ldc_title_25" in ids
    assert "dcm" in ids
    assert "zoning_by_address" in ids
    assert is_approved_regulatory_source("LDC")
    assert is_approved_regulatory_source("Drainage Criteria Manual")
    assert normalize_regulatory_source("title 25") == "LDC"
    assert not is_approved_regulatory_source("Random Blog")


def test_citation_verification_found():
    evidence = [
        {
            "doc_id": "LDC",
            "source_name": "Austin Land Development Code (Title 25)",
            "source_url": "https://example.com",
            "chapter": "Chapter 25-1",
            "section_number": "25-1-1",
            "section_title": "IMPLEMENTATION OF COMPREHENSIVE PLAN",
            "text": (
                "This title implements the planning policies of the "
                "Comprehensive Plan and shall be construed to achieve its purposes."
            ),
            "chunk_id": "LDC:25-1-1:0",
        }
    ]
    citations = extract_citations_from_evidence(evidence)
    verified = verify_citations(citations)
    assert verified[0]["verification_status"] == "found"
    assert verified[0]["supports_claim"] is True


def test_citation_rejects_unrelated_claim():
    """Section existence alone is not enough — claim support is required."""

    result = verify_citation(
        {
            "source": "LDC",
            "section_number": "25-1-1",
            "section_title": "IMPLEMENTATION OF COMPREHENSIVE PLAN",
            "claim": (
                "Maximum impervious cover for SF-3 lots is forty-five percent "
                "and driveway spacing must be two hundred feet."
            ),
        },
        get_section=__import__(
            "src.guardrails.citations", fromlist=["lookup_section"]
        ).lookup_section,
    )
    assert result["supports_claim"] is False
    assert result["verification_status"] == "unsupported_claim"


def test_assess_claim_support_requires_overlap():
    support = assess_claim_support(
        "parking driveway access requirements",
        "This section establishes floodplain development criteria and watershed buffers.",
        section_title="FLOODPLAIN REGULATIONS",
    )
    assert support["supports_claim"] is False


def test_citation_rejects_unapproved_source():
    result = verify_citation(
        {
            "source": "Random Blog",
            "section_number": "1",
        },
        get_section=lambda s, n: {"status": "found", "matches": [{"text": "x" * 50}]},
    )
    assert result["verification_status"] == "unapproved_source"
    assert result["supports_claim"] is False


def test_unsupported_claims_are_sanitized():
    text = "This development will be approved and is fully compliant."
    hits = find_unsupported_claims(text)
    assert hits
    cleaned, cleaned_hits = sanitize_text(text)
    assert cleaned_hits
    assert "will be approved" not in cleaned.lower()
    assert "requires professional verification" in cleaned.lower()


def test_sanitize_preserves_negated_historical_caution():
    cleaned, hits = sanitize_text(HISTORICAL_CONTEXT_NOTE)
    assert hits == []
    assert "approval precedent" in cleaned
    assert "requires professional verification" not in cleaned


def test_privacy_scrub_removes_contact_info():
    text = "Contact jane@example.com or 512-555-0100. applicant: Jane Doe"
    cleaned = scrub_text(text)
    assert "jane@example.com" not in cleaned
    assert "512-555-0100" not in cleaned
    assert "[REDACTED]" in cleaned
    assert "[REDACTED]" in scrub_value({"note": "email me at a@b.com"})["note"]


def test_finding_labels_from_site_context():
    findings = classify_site_findings(
        {
            "zoning": {"status": "found", "zoning": "SF-3-NP"},
            "floodplain": {
                "status": "found",
                "intersects_floodplain": True,
            },
            "watershed": {"status": "found", "watershed": "Waller Creek"},
            "geocode": {"status": "found"},
        }
    )
    labels = {f["label"] for f in findings}
    assert "potential constraint" in labels
    assert labels.issubset(set(FINDING_LABELS))


def test_apply_guardrails_validates_report():
    state = {
        "input_valid": True,
        "proposal": {
            "address": "1714 Madison Avenue, Austin, TX",
            "proposed_land_use": "Multifamily residential",
        },
        "site_context": {
            "zoning": {"status": "found", "zoning": "SF-3-NP"},
            "floodplain": {
                "status": "found",
                "intersects_floodplain": False,
            },
            "watershed": {"status": "found", "watershed": "Waller Creek"},
            "geocode": {"status": "found"},
        },
        "evidence": [
            {
                "doc_id": "LDC",
                "source_name": "Austin Land Development Code (Title 25)",
                "source_url": "https://library.municode.com/tx/austin/codes/land_development_code",
                "chapter": "Chapter 25-1",
                "section_number": "25-1-1",
                "section_title": "IMPLEMENTATION OF COMPREHENSIVE PLAN",
                "text": (
                    "This title implements the planning policies of the "
                    "Comprehensive Plan and shall be construed to achieve its purposes."
                ),
                "chunk_id": "LDC:25-1-1:0",
                "query": "Austin development requirements comprehensive plan implementation",
            }
        ],
        "reviews": {
            "zoning_site_plan": {
                "query": "Austin development requirements comprehensive plan implementation",
                "retrieved_passages": [
                    {
                        "doc_id": "LDC",
                        "section_number": "25-1-1",
                        "section_title": "IMPLEMENTATION OF COMPREHENSIVE PLAN",
                        "chapter": "Chapter 25-1",
                    }
                ],
            }
        },
        "warnings": [],
        "missing_information": [],
        "execution_trace": ["synthesize_review: completed"],
        "final_report": {
            "project": {
                "address": "1714 Madison Avenue, Austin, TX",
                "proposed_land_use": "Multifamily residential",
            },
            "site_summary": {
                "reported_zoning": "SF-3-NP",
                "zoning_status": "found",
            },
            "review_sections": {
                "historical_context": {
                    "note": "stale note that should be replaced",
                    "summary": {"permit_count": 0},
                },
                "water_wastewater": {
                    "note": "Utility capacity is available for this site.",
                    "retrieved_passages": [],
                },
            },
            "llm_synthesis": "Nearby permits prove approval of similar projects.",
            "disclaimer": "Preliminary only.",
        },
    }

    result = apply_guardrails(state)
    assert result["guardrail_result"]["status"] == "validated"
    assert result["guardrail_result"]["citations_verified"] >= 1
    assert result["final_report"]["status"] == "validated"
    assert result["final_report"]["citations"]
    assert result["guardrail_result"]["unsupported_claim_count"] >= 1
    synth = result["final_report"]["llm_synthesis"].lower()
    assert "prove approval" not in synth
    hist_note = result["final_report"]["review_sections"]["historical_context"]["note"]
    assert "approval precedent" in hist_note
    assert "requires professional verification" not in hist_note


def test_apply_guardrails_omits_ambiguous_zoning_designation():
    state = {
        "input_valid": True,
        "proposal": {
            "address": "5508 Merrywing Circle, Austin, TX",
            "proposed_land_use": "Commercial retail",
        },
        "site_context": {
            "zoning": {
                "status": "multiple_records",
                "zoning": "SF-2",
                "zoning_designations": ["SF-2", "SF-3"],
            },
            "floodplain": {"status": "found", "intersects_floodplain": False},
            "watershed": {"status": "found", "watershed": "Onion Creek"},
            "geocode": {"status": "found"},
        },
        "evidence": [],
        "reviews": {},
        "warnings": [],
        "missing_information": [],
        "execution_trace": ["synthesize_review: completed"],
        "final_report": {
            "project": {"address": "5508 Merrywing Circle, Austin, TX"},
            "site_summary": {
                "reported_zoning": "SF-2",
                "zoning_status": "multiple_records",
            },
            "review_sections": {},
            "disclaimer": "Preliminary only.",
        },
    }
    result = apply_guardrails(state)
    assert result["final_report"]["site_summary"]["reported_zoning"] is None
    assert result["final_report"]["site_summary"]["zoning_status"] == "multiple_records"
