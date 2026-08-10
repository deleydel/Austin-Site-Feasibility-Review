"""Tests for Task 4: agentic workflow and synthesis."""

from src.agents.graph import review_graph


def test_invalid_input_stops_workflow():
    """Missing required input should stop before site tools run."""

    result = review_graph.invoke(
        {
            "proposal": {
                "address": "",
                "proposed_land_use": "",
            }
        }
    )

    assert result["input_valid"] is False
    assert "address" in result["stop_reason"]
    assert "proposed_land_use" in result["stop_reason"]
    assert result["execution_trace"][0] == "validate_input: failed"
    # Invalid input still runs guardrail packaging + report build.
    assert result["execution_trace"][-1] == "build_report: completed"
    assert result["final_report"]["status"] == "blocked"
    assert "site_context" not in result


def test_complete_workflow():
    """A valid Austin site should complete every Task 4 review node."""

    result = review_graph.invoke(
        {
            "proposal": {
                "address": "1714 Madison Avenue",
                "proposed_land_use": "Multifamily residential",
                "development_description": (
                    "Proposed 40-unit multifamily residential development"
                ),
                "units": 40,
            }
        }
    )

    assert result["input_valid"] is True

    assert result["site_context"]["zoning"]["status"] == "found"
    assert result["site_context"]["zoning"]["zoning"] == "SF-3-NP"

    assert "zoning_site_plan" in result["reviews"]
    assert "drainage_environmental" in result["reviews"]
    assert "transportation_access" in result["reviews"]
    assert "water_wastewater" in result["reviews"]
    assert "historical_context" in result["reviews"]

    assert len(result["evidence"]) > 0

    assert "final_report" in result
    assert result["final_report"]["project"]["address"] == (
        "1714 Madison Avenue"
    )
    assert result["final_report"]["status"] == "validated"
    assert "report_document" in result
    assert result["report_document"]["schema_complete"] is True
    assert result["guardrail_result"]["status"] == "validated"

    assert result["execution_trace"][-1] == "build_report: completed"
    assert "apply_guardrails: completed" in result["execution_trace"]
    assert "synthesize_review: completed" in result["execution_trace"]


def test_sf3_multifamily_flags_potential_zoning_conflict():
    """SF-3 zoning plus multifamily proposal should require verification."""

    result = review_graph.invoke(
        {
            "proposal": {
                "address": "1714 Madison Avenue",
                "proposed_land_use": "Multifamily residential",
                "development_description": (
                    "Proposed 40-unit multifamily residential development"
                ),
                "units": 40,
            }
        }
    )

    zoning_review = result["reviews"]["zoning_site_plan"]

    assert zoning_review["potential_conflict"] is True
    assert "SF-3-NP" in zoning_review["conflict_detail"]
    assert "verification" in zoning_review["conflict_detail"].lower()

    # The conflict must reach the FINAL report as a potential constraint,
    # not stay buried in the review section — including without LLM synthesis.
    final = result["final_report"]
    constraints = final.get("potential_constraints") or []
    conflict_findings = [
        c for c in constraints
        if c.get("category") == "zoning" and "SF-3-NP" in (c.get("detail") or "")
    ]
    assert conflict_findings, (
        "zoning/use conflict missing from final potential_constraints"
    )

    from src.report.template import render_report_markdown

    markdown = render_report_markdown(result["report_document"])
    assert "SF-3-NP" in markdown
    assert "potential zoning/use conflict" in markdown.lower()