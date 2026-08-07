"""Task 3: nearby historical-record search (permits, site-plan cases,
plan-review cases).

- Radius search in EPSG:2277 feet over precomputed x_ft/y_ft columns.
- Output fields are allow-listed per dataset: no applicant, owner, or
  contact information is ever returned.
- Records flagged exclude_from_search (VOID/test) never appear.
- Results are historical context only, never approval precedent.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.tools import _data

HISTORY_NOTE = ("Nearby records are historical context only; they are not "
                "evidence that any future application will be approved.")

PERMIT_FIELDS = [
    "permit_number", "permit_class_mapped", "permit_class", "work_class",
    "permit_location", "description", "status_current", "applieddate",
    "issue_date", "completed_date", "housing_units", "number_of_floors",
    "total_job_valuation", "link",
]
SITE_PLAN_FIELDS = [
    "PERMIT_NUMBER", "CASE_TYPE", "CASE_NAME", "SUB_TYPE", "STATUS",
    "STATUS_DATE", "APPLICATION_START_DATE", "APPROVAL_DATE",
    "DESCRIPTION_OF_WORK", "PROPOSED_LAND_USE", "EXISTING_ZONING",
    "PROPOSED_NO_OF_UNITS", "GROSS_SITE_AREA_ACRES", "WATERSHED", "LINK",
]
PLAN_REVIEW_FIELDS = [
    "Permit_Number", "Case_Type", "Sub_Type", "Work_Class", "Project_Name",
    "Folder_Description", "Status_Current", "Status_Date", "Applied_Date",
    "Issued_Date", "Number_Of_Units", "Total_Job_Valuation", "Web_Link",
]


def _radius_search(df: pd.DataFrame, lat: float, lon: float, radius_ft: float,
                   date_col: str | None, years: float | None,
                   fields: list[str], limit: int) -> dict:
    pt = _data.to_tx_ft(lat, lon)
    d = df[df["x_ft"].notna()]
    excluded_no_geometry = len(df) - len(d)

    if years and date_col:
        cutoff = pd.Timestamp.now() - pd.DateOffset(years=years)
        d = d[d[date_col].notna() & (d[date_col] >= cutoff)]

    dist = np.hypot(d["x_ft"].to_numpy() - pt.x, d["y_ft"].to_numpy() - pt.y)
    mask = dist <= radius_ft
    hits = d[mask].copy()
    hits["distance_ft"] = np.round(dist[mask], 1)
    hits = hits.sort_values("distance_ft").head(limit)

    records = []
    for _, row in hits.iterrows():
        rec = {"distance_ft": float(row["distance_ft"])}
        for f in fields:
            v = row.get(f)
            if pd.isna(v):
                continue
            rec[f.lower()] = v.isoformat() if isinstance(v, pd.Timestamp) else v
        records.append(rec)

    return {
        "status": "found" if records else "no_records_in_radius",
        "latitude": lat, "longitude": lon,
        "radius_ft": radius_ft,
        "years_lookback": years,
        "count_in_radius": int(mask.sum()),
        "count_returned": len(records),
        "rows_without_coordinates_not_searchable": excluded_no_geometry,
        "records": records,
        "note": HISTORY_NOTE,
    }


def nearby_permits(lat: float, lon: float, radius_ft: float = 800,
                   years: float | None = 5, limit: int = 20) -> dict:
    return _radius_search(_data.permits(), lat, lon, radius_ft,
                          "issue_date", years, PERMIT_FIELDS, limit)


def nearby_site_plan_cases(lat: float, lon: float, radius_ft: float = 800,
                           years: float | None = None, limit: int = 20) -> dict:
    return _radius_search(_data.site_plans(), lat, lon, radius_ft,
                          "APPLICATION_START_DATE", years, SITE_PLAN_FIELDS, limit)


def nearby_plan_review_cases(lat: float, lon: float, radius_ft: float = 800,
                             years: float | None = 5, limit: int = 20) -> dict:
    df = _data.plan_review()
    df = df[~df["exclude_from_search"]]
    return _radius_search(df, lat, lon, radius_ft,
                          "Applied_Date", years, PLAN_REVIEW_FIELDS, limit)
