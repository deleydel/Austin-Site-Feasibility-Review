"""Human-readable templates and citation formatting for reports."""

from __future__ import annotations

from typing import Any


def format_citation(citation: dict[str, Any]) -> str:
    """Format one verified citation as a readable source line."""

    source = citation.get("source") or citation.get("source_name") or "Unknown"
    section = citation.get("section_number") or "n/a"
    title = citation.get("section_title") or ""
    chapter = citation.get("chapter") or ""
    url = citation.get("source_url") or ""

    if chapter and title:
        line = f"{source} — § {section} {title} ({chapter})"
    elif title:
        line = f"{source} — § {section} {title}"
    else:
        line = f"{source} — § {section}"
    if url:
        line = f"{line} | {url}"
    return line


def _format_summary(summary: Any) -> str:
    """Render a section summary (often a dict of counts) as readable text."""

    if isinstance(summary, dict):
        return ", ".join(
            f"{k.replace('_', ' ').capitalize()}: {v}" for k, v in summary.items()
        )
    return str(summary)


def render_report_markdown(document: dict[str, Any]) -> str:
    """Render a report document dict to Markdown."""

    sections = document.get("sections") or {}
    lines: list[str] = [
        f"# {document.get('title', 'Preliminary Development Feasibility Report')}",
        "",
        f"Generated: {document.get('generated_date', '')}",
        f"Status: {document.get('status', '')}",
        "",
    ]

    project_section = sections.get("project_and_site") or {}
    project = project_section.get("project") or {}
    site = project_section.get("site_summary") or {}
    lines += [
        f"## {project_section.get('heading', 'Project and Site Description')}",
        "",
        f"- Address: {project.get('address', 'n/a')}",
        f"- Proposed land use: {project.get('proposed_land_use', 'n/a')}",
        f"- Development description: {project.get('development_description', 'n/a')}",
        f"- Units: {project.get('units', 'n/a')}",
        f"- Site area (acres): {project.get('site_area_acres', 'n/a')}",
        "",
    ]
    if project_section.get("llm_synthesis"):
        lines += [
            "### Synthesis",
            "",
            str(project_section["llm_synthesis"]),
            "",
        ]

    sources = sections.get("sources_consulted") or {}
    lines += [f"## {sources.get('heading', 'Sources Consulted')}", ""]
    for item in sources.get("items") or []:
        name = item.get("name") or item.get("id")
        url = item.get("url") or ""
        lim = item.get("limitations") or ""
        lines.append(f"- **{name}** — {url}")
        if lim:
            lines.append(f"  - Limitation: {lim}")
    lines.append("")

    zoning = sections.get("zoning_and_land_use") or {}
    lines += [f"## {zoning.get('heading', 'Zoning and Land-Use Context')}", ""]
    if zoning.get("reported_zoning"):
        lines.append(
            f"- Preliminary reported zoning: {zoning.get('reported_zoning')} "
            f"(status: {zoning.get('zoning_status', 'n/a')})"
        )
    else:
        lines.append(
            f"- No single zoning designation stated "
            f"(lookup status: {zoning.get('zoning_status', 'n/a')})"
        )
    if zoning.get("zoning_note"):
        lines.append(f"- {zoning['zoning_note']}")
    lines.append("")
    _append_review(lines, zoning.get("review") or {})

    for key in (
        "site_plan_considerations",
        "drainage_flood_environmental",
        "transportation_access",
        "water_wastewater",
        "historical_permit_case_context",
    ):
        section = sections.get(key) or {}
        lines += [f"## {section.get('heading', key)}", ""]
        if key == "drainage_flood_environmental":
            lines.append(
                f"- Floodplain intersection: "
                f"{section.get('floodplain_intersection', 'n/a')}"
            )
            lines.append(f"- Watershed: {section.get('watershed', 'n/a')}")
            lines.append("")
        if section.get("note"):
            lines += [str(section["note"]), ""]
        _append_review(lines, section.get("review") or {})

    constraints = sections.get("potential_constraints") or {}
    lines += [f"## {constraints.get('heading', 'Potential Constraints')}", ""]
    items = constraints.get("items") or []
    if not items:
        lines.append(
            "- No major constraint labeled from available screening data; "
            "professional verification is still required."
        )
    else:
        for item in items:
            lines.append(
                f"- [{item.get('label', '')}] {item.get('category', '')}: "
                f"{item.get('detail', '')}"
            )
    lines.append("")

    missing = sections.get("missing_information_and_verification") or {}
    lines += [
        f"## {missing.get('heading', 'Missing Information and Required Verification')}",
        "",
    ]
    missing_items = missing.get("missing_information") or []
    verification_items = missing.get("required_verification") or []
    warning_items = missing.get("warnings") or []
    if not missing_items and not verification_items and not warning_items:
        lines.append("- No additional missing-information items were recorded.")
    for item in missing_items:
        lines.append(f"- Missing: {item}")
    for item in verification_items:
        if isinstance(item, dict):
            lines.append(
                f"- Verification required ({item.get('category', '')}): "
                f"{item.get('detail', '')}"
            )
        else:
            lines.append(f"- Verification required: {item}")
    for warning in warning_items:
        lines.append(f"- Warning: {warning}")
    lines.append("")

    cites = sections.get("source_citations") or {}
    lines += [f"## {cites.get('heading', 'Source Citations')}", ""]
    cite_items = cites.get("items") or []
    if not cite_items:
        lines.append("- No verified regulatory citations available.")
    else:
        for i, cite in enumerate(cite_items, start=1):
            lines.append(f"{i}. {cite}")
    lines.append("")

    disclaimer = sections.get("disclaimer") or {}
    lines += [
        f"## {disclaimer.get('heading', 'Preliminary-Review Disclaimer')}",
        "",
        str(disclaimer.get("text", "")),
        "",
    ]
    return "\n".join(lines)


def _append_review(lines: list[str], review: dict[str, Any]) -> None:
    if review.get("note"):
        lines.extend([str(review["note"]), ""])
    if review.get("summary"):
        lines.extend([f"Summary: {_format_summary(review['summary'])}", ""])
    passages = review.get("passages") or []
    if passages:
        lines.append("Regulatory references for this section:")
        for p in passages[:8]:
            lines.append(
                f"- {p.get('doc_id', '')} § {p.get('section_number', '')} "
                f"{p.get('section_title', '')}"
            )
        lines.append("")
