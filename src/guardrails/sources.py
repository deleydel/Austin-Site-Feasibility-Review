"""Approved-source whitelist loaded from the Task 1 source manifest."""

from __future__ import annotations

import json
from functools import lru_cache

from src import config

# Regulatory doc_ids used by the retriever / citation checker.
APPROVED_REGULATORY_DOC_IDS = frozenset(config.SOURCE_DOCS.keys())

# Structured tool source ids from the preprocessing manifest.
APPROVED_STRUCTURED_SOURCE_IDS = frozenset(
    {
        "zoning_by_address",
        "issued_construction_permits",
        "site_plan_cases",
        "plan_review_cases",
        "watershed_boundaries",
        "fully_developed_floodplain",
    }
)


@lru_cache(maxsize=1)
def load_source_manifest() -> dict:
    """Load the committed approved-source list."""

    return json.loads(config.SOURCE_MANIFEST.read_text())


@lru_cache(maxsize=1)
def approved_source_ids() -> frozenset[str]:
    """Return all approved source ids from the manifest."""

    manifest = load_source_manifest()
    return frozenset(s["id"] for s in manifest.get("sources", []))


def is_approved_regulatory_source(source: str) -> bool:
    """True if source resolves to an approved regulatory document id."""

    return normalize_regulatory_source(source) is not None


def normalize_regulatory_source(source: str) -> str | None:
    """Map a free-text source name to LDC / DCM / TCM, or None if unapproved."""

    if not source:
        return None
    key = source.strip()
    upper = key.upper()
    if upper in APPROVED_REGULATORY_DOC_IDS:
        return upper
    lower = key.lower()
    aliases = {
        "ldc": "LDC",
        "land development code": "LDC",
        "title 25": "LDC",
        "austin land development code": "LDC",
        "austin land development code (title 25)": "LDC",
        "austin land development code, title 25": "LDC",
        "dcm": "DCM",
        "drainage criteria manual": "DCM",
        "austin drainage criteria manual": "DCM",
        "tcm": "TCM",
        "transportation criteria manual": "TCM",
        "austin transportation criteria manual": "TCM",
    }
    if lower in aliases:
        return aliases[lower]
    for doc_id, meta in config.SOURCE_DOCS.items():
        name = meta["name"].lower()
        if lower == name or lower in name or name in lower:
            return doc_id
    # Loose contains match for common short names.
    if "land development code" in lower or "title 25" in lower:
        return "LDC"
    if "drainage criteria" in lower:
        return "DCM"
    if "transportation criteria" in lower:
        return "TCM"
    return None


def sources_consulted_entries() -> list[dict]:
    """Return citation-ready source entries for the final report."""

    manifest = load_source_manifest()
    entries = []
    for src in manifest.get("sources", []):
        entries.append(
            {
                "id": src.get("id"),
                "name": src.get("name"),
                "url": src.get("url"),
                "type": src.get("type"),
                "limitations": src.get("limitations"),
                "coverage": src.get("coverage"),
            }
        )
    return entries
