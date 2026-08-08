"""Unsupported-claim controls for generated feasibility text."""

from __future__ import annotations

import re
from typing import Any

FINDING_LABELS = (
    "potential constraint",
    "verification required",
    "insufficient information",
    "no major issue identified from available data",
)

# Phrases that assert definitive outcomes the system must not claim.
_BANNED_CLAIM_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "definitive_approval",
        re.compile(
            r"\b("
            r"will\s+be\s+approved|is\s+approved|approved\s+for\s+construction|"
            r"guarantee[sd]?\s+approval|automatically\s+approved|"
            r"entitled\s+to\s+approval"
            r")\b",
            re.I,
        ),
    ),
    (
        "definitive_compliance",
        re.compile(
            r"\b("
            r"is\s+(fully\s+)?compliant|fully\s+complies|"
            r"meets\s+all\s+(code|regulatory)\s+requirements|"
            r"guarantees?\s+compliance|code\s+compliant"
            r")\b",
            re.I,
        ),
    ),
    (
        "definitive_feasibility",
        re.compile(
            r"\b("
            r"is\s+(definitely|clearly|fully)\s+feasible|"
            r"definitely\s+feasible|not\s+feasible\s+under\s+any\s+circumstances|"
            r"guarantees?\s+feasibility"
            r")\b",
            re.I,
        ),
    ),
    (
        "utility_capacity",
        re.compile(
            r"\b("
            r"utility\s+(service|capacity)\s+is\s+available|"
            r"has\s+(adequate|sufficient)\s+(water|wastewater|utility)\s+capacity|"
            r"water\s+(and\s+wastewater\s+)?service\s+is\s+(confirmed|guaranteed|available)"
            r")\b",
            re.I,
        ),
    ),
    (
        "historical_precedent",
        re.compile(
            r"\b("
            r"nearby\s+(permits?|cases?)\s+(prove|guarantee|ensure|establish)\s+"
            r"(approval|compliance|feasibility)|"
            r"historical\s+(permits?|cases?)\s+as\s+(proof|precedent)\s+of\s+approval|"
            r"because\s+nearby\s+(projects?|permits?)\s+were\s+approved"
            r")\b",
            re.I,
        ),
    ),
]

_REVISION_SUFFIX = (
    " [Claim removed or revised: unsupported definitive statement; "
    "professional verification required.]"
)


def find_unsupported_claims(text: str) -> list[dict[str, str]]:
    """Return banned-claim matches found in text."""

    if not text:
        return []
    hits = []
    for claim_type, pattern in _BANNED_CLAIM_PATTERNS:
        for match in pattern.finditer(text):
            hits.append(
                {
                    "claim_type": claim_type,
                    "match": match.group(0),
                    "span": f"{match.start()}:{match.end()}",
                }
            )
    return hits


def sanitize_text(text: str) -> tuple[str, list[dict[str, str]]]:
    """Neutralize banned claims in text; return (cleaned, hits)."""

    if not text:
        return text, []

    hits = find_unsupported_claims(text)
    cleaned = text
    for claim_type, pattern in _BANNED_CLAIM_PATTERNS:
        cleaned = pattern.sub(
            "requires professional verification",
            cleaned,
        )

    if hits and _REVISION_SUFFIX not in cleaned:
        cleaned = cleaned.rstrip() + _REVISION_SUFFIX
    return cleaned, hits


def classify_site_findings(site_context: dict[str, Any]) -> list[dict[str, str]]:
    """Derive cautious finding labels from structured tool statuses."""

    findings: list[dict[str, str]] = []

    zoning = site_context.get("zoning", {}) or {}
    z_status = zoning.get("status")
    if z_status == "found":
        findings.append(
            {
                "category": "zoning",
                "label": "verification required",
                "detail": (
                    "Preliminary reported zoning was retrieved from Open Data "
                    "and requires official verification."
                ),
            }
        )
    elif z_status in {"multiple_records", "ambiguous", "fuzzy_match"}:
        findings.append(
            {
                "category": "zoning",
                "label": "verification required",
                "detail": (
                    f"Zoning lookup status is '{z_status}'; official "
                    "verification is required before design decisions."
                ),
            }
        )
    else:
        findings.append(
            {
                "category": "zoning",
                "label": "insufficient information",
                "detail": "Zoning could not be confirmed from available data.",
            }
        )

    floodplain = site_context.get("floodplain", {}) or {}
    fp_status = floodplain.get("status")
    if fp_status == "found" and floodplain.get("intersects_floodplain") is True:
        findings.append(
            {
                "category": "drainage_flood",
                "label": "potential constraint",
                "detail": (
                    "Site intersects the fully developed floodplain model "
                    "used for preliminary screening."
                ),
            }
        )
    elif fp_status == "found":
        findings.append(
            {
                "category": "drainage_flood",
                "label": "no major issue identified from available data",
                "detail": (
                    "No floodplain intersection identified in available "
                    "screening data; proximity notes are informational only."
                ),
            }
        )
    elif fp_status in {"boundary", "not_run", None}:
        findings.append(
            {
                "category": "drainage_flood",
                "label": "verification required",
                "detail": (
                    "Floodplain status is incomplete or ambiguous and "
                    "requires verification."
                ),
            }
        )
    else:
        findings.append(
            {
                "category": "drainage_flood",
                "label": "insufficient information",
                "detail": "Floodplain check was not available for this site.",
            }
        )

    watershed = site_context.get("watershed", {}) or {}
    ws_status = watershed.get("status")
    if ws_status == "found":
        findings.append(
            {
                "category": "watershed",
                "label": "no major issue identified from available data",
                "detail": (
                    f"Watershed identified as "
                    f"{watershed.get('watershed', 'unknown')} from available data."
                ),
            }
        )
    elif ws_status == "boundary":
        findings.append(
            {
                "category": "watershed",
                "label": "verification required",
                "detail": "Site appears near a watershed boundary.",
            }
        )
    else:
        findings.append(
            {
                "category": "watershed",
                "label": "insufficient information",
                "detail": "Watershed could not be confirmed from available data.",
            }
        )

    geocode = site_context.get("geocode", {}) or {}
    if geocode.get("status") != "found":
        findings.append(
            {
                "category": "location",
                "label": "verification required",
                "detail": (
                    "Site coordinates were not uniquely confirmed; spatial "
                    "checks may be incomplete."
                ),
            }
        )

    # Historical nearby records are context only.
    findings.append(
        {
            "category": "historical_context",
            "label": "verification required",
            "detail": (
                "Nearby permits and cases are historical context only and "
                "must not be treated as approval precedent."
            ),
        }
    )

    return findings
