"""Task 1: source manifest — one entry per dataset with provenance and limits.

This file is also the seed for the guardrail team's approved-source list.
"""
from __future__ import annotations

import json
from datetime import date

from src import config

SNAPSHOT_DATE = "2026-08-07"  # from the Open Data export filenames

MANIFEST = [
    {
        "id": "ldc_title_25",
        "name": "Austin Land Development Code, Title 25",
        "publisher": "City of Austin / Municode",
        "url": config.SOURCE_DOCS["LDC"]["url"],
        "file": config.LDC_DOCX.name,
        "type": "regulatory_docx",
        "coverage": "Chapters 25-1, 25-2, 25-5, 25-6, 25-7, 25-8, 25-9",
        "limitations": "Snapshot export; ordinances adopted after the export date are not reflected.",
    },
    {
        "id": "dcm",
        "name": "Austin Drainage Criteria Manual",
        "publisher": "City of Austin / Municode",
        "url": config.SOURCE_DOCS["DCM"]["url"],
        "file": config.DCM_DOCX.name,
        "type": "regulatory_docx",
        "coverage": "Sections 1, 2, 8 and Appendix E",
        "limitations": "Partial manual; other DCM sections are out of scope for this system.",
    },
    {
        "id": "tcm",
        "name": "Austin Transportation Criteria Manual",
        "publisher": "City of Austin / Municode",
        "url": config.SOURCE_DOCS["TCM"]["url"],
        "file": config.TCM_DOCX.name,
        "type": "regulatory_docx",
        "coverage": "Sections 1, 7, 9, 10",
        "limitations": "Partial manual; other TCM sections are out of scope for this system.",
    },
    {
        "id": "zoning_by_address",
        "name": "Zoning by Address",
        "publisher": "City of Austin Open Data Portal (data.austintexas.gov)",
        "url": "https://data.austintexas.gov/ (search: Zoning by Address)",
        "file": config.ZONING_CSV.name,
        "type": "structured_csv",
        "snapshot_date": SNAPSHOT_DATE,
        "limitations": "Preliminary reported zoning only; not an official zoning "
                       "determination. No coordinates; matching is by address string.",
    },
    {
        "id": "issued_construction_permits",
        "name": "Issued Construction Permits",
        "publisher": "City of Austin Open Data Portal",
        "url": "https://data.austintexas.gov/Building-and-Development/Issued-Construction-Permits/3syk-w9eu",
        "file": config.PERMITS_CSV.name,
        "type": "structured_csv",
        "snapshot_date": SNAPSHOT_DATE,
        "limitations": "Issued permits 2021+ only. Historical proximity context; "
                       "not approval precedent.",
    },
    {
        "id": "site_plan_cases",
        "name": "Site Plan Cases",
        "publisher": "City of Austin Open Data Portal",
        "url": "https://data.austintexas.gov/ (search: Site Plan Cases)",
        "file": config.SITE_PLANS_CSV.name,
        "type": "structured_csv",
        "snapshot_date": SNAPSHOT_DATE,
        "limitations": "Some records lack coordinates. Applicant/owner contact "
                       "fields removed during preprocessing (privacy).",
    },
    {
        "id": "plan_review_cases",
        "name": "Plan Review Cases",
        "publisher": "City of Austin Open Data Portal",
        "url": "https://data.austintexas.gov/ (search: Plan Review Cases)",
        "file": config.PLAN_REVIEW_CSV.name,
        "type": "structured_csv",
        "snapshot_date": SNAPSHOT_DATE,
        "limitations": "Contains VOID/test records (retained but flagged "
                       "exclude_from_search). Contact fields removed (privacy).",
    },
    {
        "id": "watershed_boundaries",
        "name": "Watershed Boundaries",
        "publisher": "City of Austin Open Data Portal",
        "url": "https://data.austintexas.gov/ (search: Watershed Boundaries)",
        "file": config.WATERSHEDS_GEOJSON.name,
        "type": "geojson",
        "snapshot_date": SNAPSHOT_DATE,
        "limitations": "76 named watersheds within the Austin planning area.",
    },
    {
        "id": "fully_developed_floodplain",
        "name": "Greater Austin Fully Developed Floodplain",
        "publisher": "City of Austin Open Data Portal",
        "url": "https://data.austintexas.gov/ (search: Greater Austin Fully Developed Floodplain)",
        "file": config.FLOODPLAIN_GEOJSON.name,
        "type": "geojson",
        "snapshot_date": SNAPSHOT_DATE,
        "limitations": "City of Austin fully developed floodplain model (Atlas 14); "
                       "not the FEMA effective floodplain. Preliminary screening only.",
    },
]


def write_manifest() -> dict:
    out = {
        "generated": date.today().isoformat(),
        "snapshot_date": SNAPSHOT_DATE,
        "sources": MANIFEST,
    }
    config.SOURCE_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    config.SOURCE_MANIFEST.write_text(json.dumps(out, indent=2))
    return out
