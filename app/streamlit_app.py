"""Task 8: Streamlit frontend for Austin SiteFeasibility AI.

Collects a site/proposal from the user, runs the Task 4-6 review graph
(site-context tools -> agentic review -> guardrails -> report build), and
displays the guarded findings, citations, and a downloadable report.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from src.agents.graph import review_graph
from src.report.export import export_report, render_report_html
from src.report.template import format_citation, render_report_markdown

WORKFLOW_STEPS = [
    ("validate_input", "Validating input and scope"),
    ("collect_site_context", "Looking up zoning, floodplain, watershed, and nearby cases"),
    ("zoning_review", "Reviewing zoning and site-plan requirements"),
    ("drainage_review", "Reviewing drainage and environmental requirements"),
    ("transportation_review", "Reviewing transportation and access requirements"),
    ("water_wastewater_review", "Reviewing water and wastewater requirements"),
    ("historical_context_review", "Interpreting nearby permit and case history"),
    ("synthesize_review", "Synthesizing findings"),
    ("apply_guardrails", "Applying guardrails and citation checks"),
    ("build_report", "Building the report"),
]

FINDING_COLOR = {
    "potential constraint": "orange",
    "verification required": "blue",
    "insufficient information": "gray",
    "no major issue identified from available data": "green",
}


def run_review(proposal: dict[str, Any]) -> dict[str, Any]:
    """Run the compiled review graph and return the final state."""

    return review_graph.invoke({"proposal": proposal})


LAND_USE_OPTIONS = [
    "Multifamily residential",
    "Single-family residential",
    "Commercial office",
    "Retail",
    "Mixed-use",
    "Industrial",
    "Other",
]


def render_input_form() -> dict[str, Any] | None:
    st.subheader("Site and Proposal Information")

    land_use_choice = st.selectbox(
        "Proposed land use",
        LAND_USE_OPTIONS,
        key="land_use_choice",
    )
    proposed_land_use_other = ""
    if land_use_choice == "Other":
        proposed_land_use_other = st.text_input(
            "Specify proposed land use",
            placeholder="e.g. hospitality / hotel",
            key="land_use_other",
        )

    with st.form("proposal_form"):
        address = st.text_input(
            "Austin street address",
            placeholder="e.g. 301 W 2nd St, Austin, TX 78701",
        )
        development_description = st.text_area(
            "Development description",
            placeholder="Briefly describe the proposed project.",
        )

        col1, col2 = st.columns(2)
        with col1:
            units = st.number_input(
                "Approximate number of units",
                min_value=0,
                value=0,
                step=1,
            )
        with col2:
            site_area_acres = st.number_input(
                "Approximate site area (acres)",
                min_value=0.0,
                value=0.0,
                step=0.1,
                format="%.2f",
            )

        with st.expander("Optional: manual coordinates (fallback if geocoding fails)"):
            col3, col4 = st.columns(2)
            with col3:
                latitude = st.number_input(
                    "Latitude", value=0.0, format="%.6f", step=0.000001
                )
            with col4:
                longitude = st.number_input(
                    "Longitude", value=0.0, format="%.6f", step=0.000001
                )

        submitted = st.form_submit_button("Run Preliminary Feasibility Review")

    if not submitted:
        return None

    resolved_land_use = (
        proposed_land_use_other.strip()
        if land_use_choice == "Other"
        else land_use_choice
    )

    return {
        "address": address.strip(),
        "proposed_land_use": resolved_land_use,
        "development_description": development_description.strip(),
        "units": int(units) or None,
        "site_area_acres": float(site_area_acres) or None,
        "latitude": latitude or None,
        "longitude": longitude or None,
    }


def render_progress_and_run(proposal: dict[str, Any]) -> dict[str, Any]:
    progress = st.progress(0.0, text="Starting review...")
    total = len(WORKFLOW_STEPS)

    # The compiled graph runs end-to-end; the step list communicates the
    # stages to the user while the (short) run completes in the background.
    for i, (_, label) in enumerate(WORKFLOW_STEPS[:-1]):
        progress.progress((i + 1) / total, text=label)

    with st.spinner("Running agentic review workflow..."):
        result = run_review(proposal)

    progress.progress(1.0, text="Done")
    return result


def render_blocked(result: dict[str, Any]) -> None:
    st.error(
        result.get("stop_reason")
        or "This request could not be processed within the supported scope."
    )
    missing = result.get("missing_information") or []
    if missing:
        st.write("Missing required information:")
        st.write(", ".join(missing))
    for warning in result.get("warnings") or []:
        st.warning(warning)


def render_findings(document: dict[str, Any]) -> None:
    sections = document.get("sections", {})

    st.subheader("Preliminary Feasibility Findings")

    metrics = document.get("metrics", {})
    m1, m2, m3 = st.columns(3)
    m1.metric("Verified citations", metrics.get("verified_citation_count", 0))
    m2.metric("Regulatory evidence items", metrics.get("regulatory_evidence_count", 0))
    m3.metric("Unsupported claims removed", metrics.get("unsupported_claim_count", 0))

    project_site = sections.get("project_and_site", {})
    if project_site.get("llm_synthesis"):
        st.markdown("**Summary**")
        st.write(project_site["llm_synthesis"])

    constraints = sections.get("potential_constraints", {}).get("items") or []
    if constraints:
        st.markdown("### Potential Constraints")
        for item in constraints:
            st.markdown(f"- :orange[**Potential constraint**] {_finding_text(item)}")

    missing_section = sections.get("missing_information_and_verification", {})
    verification_items = missing_section.get("required_verification") or []
    if verification_items:
        st.markdown("### Verification Required")
        for item in verification_items:
            st.markdown(f"- :blue[**Verification required**] {_finding_text(item)}")

    missing_info = missing_section.get("missing_information") or []
    if missing_info:
        st.markdown("### Missing Information")
        for item in missing_info:
            st.markdown(f"- {item}")

    review_labels = [
        ("zoning_and_land_use", "Zoning and Land Use"),
        ("site_plan_considerations", "Site-Plan Considerations"),
        ("drainage_flood_environmental", "Drainage, Flood, and Environmental"),
        ("transportation_access", "Transportation and Access"),
        ("water_wastewater", "Water and Wastewater"),
        ("historical_permit_case_context", "Historical Permit and Case Context"),
    ]
    st.markdown("### Review Sections")
    for key, label in review_labels:
        section = sections.get(key, {})
        with st.expander(label):
            review = section.get("review", {})
            note = section.get("note") or review.get("note")
            if note:
                st.caption(note)
            passages = review.get("passages") or []
            if not passages:
                st.write("No retrieved passages for this section.")
            for passage in passages:
                st.markdown(f"- {_passage_text(passage)}")

    citations = sections.get("source_citations", {}).get("items") or []
    if citations:
        st.markdown("### Source Citations")
        for citation in citations:
            st.markdown(f"- {_citation_text(citation)}")

    warnings = missing_section.get("warnings") or []
    for warning in warnings:
        st.warning(warning)

    disclaimer = sections.get("disclaimer", {}).get("text")
    if disclaimer:
        st.info(disclaimer)


def _finding_text(item: Any) -> str:
    if isinstance(item, dict):
        return (
            item.get("text")
            or item.get("description")
            or item.get("detail")
            or str(item)
        )
    return str(item)


def _citation_text(citation: Any) -> str:
    if not isinstance(citation, dict):
        return str(citation)
    line = format_citation(citation)
    url = citation.get("source_url")
    if url:
        return line.replace(f"| {url}", f"| [{url}]({url})")
    return line


def _passage_text(passage: Any) -> str:
    if not isinstance(passage, dict):
        return str(passage)
    if "text" in passage:
        return str(passage["text"])

    doc_id = passage.get("doc_id", "")
    section = passage.get("section_number", "")
    title = passage.get("section_title", "")
    chapter = passage.get("chapter", "")
    url = passage.get("source_url", "")

    line = f"{doc_id} § {section} {title}".strip()
    if chapter:
        line = f"{line} ({chapter})"
    if url:
        line = f"{line} | [{url}]({url})"
    return line


def render_downloads(document: dict[str, Any]) -> None:
    st.subheader("Download Report")

    markdown_text = render_report_markdown(document)
    html_text = render_report_html(document)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.download_button(
            "Download as Markdown",
            data=markdown_text.encode("utf-8"),
            file_name="preliminary_feasibility_report.md",
            mime="text/markdown",
        )
    with col2:
        st.download_button(
            "Download as HTML",
            data=html_text.encode("utf-8"),
            file_name="preliminary_feasibility_report.html",
            mime="text/html",
        )
    with col3:
        st.download_button(
            "Download as DOCX",
            data=_export_bytes(document, "docx"),
            file_name="preliminary_feasibility_report.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    with col4:
        st.download_button(
            "Download as PDF",
            data=_export_bytes(document, "pdf"),
            file_name="preliminary_feasibility_report.pdf",
            mime="application/pdf",
        )


def _export_bytes(document: dict[str, Any], fmt: str) -> bytes:
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / f"report.{fmt}"
        export_report(document, path, fmt=fmt)
        return path.read_bytes()


def main() -> None:
    st.set_page_config(page_title="Austin SiteFeasibility AI", layout="wide")
    st.title("Austin SiteFeasibility AI")
    st.caption(
        "Preliminary land-development screening for Austin, Texas. "
        "This tool supports early screening only and does not issue an "
        "official zoning determination, establish code compliance, "
        "guarantee utility service, or replace review by qualified "
        "engineers and City of Austin authorities."
    )

    proposal = render_input_form()
    if proposal is None:
        return

    result = render_progress_and_run(proposal)

    if not result.get("input_valid", True):
        render_blocked(result)
        return

    document = result.get("report_document") or {}
    if not document:
        st.error("The review workflow did not produce a report. Please try again.")
        return

    render_findings(document)
    render_downloads(document)


if __name__ == "__main__":
    main()
