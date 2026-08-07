"""Task 1: cleaning of the four structured CSV datasets.

Rules implemented (per review):
- Zoning duplicates are preserved: an address with multiple distinct zoning
  designations is flagged, never collapsed to one row.
- Permits: exact duplicate rows removed; duplicate permit_numbers audited and
  retained when meaningful fields differ.
- Site-plan / plan-review outputs keep ONLY allow-listed fields (no applicant,
  owner, or contact information).
- VOID/test plan-review records are retained with exclude_from_search=True,
  never deleted.
Every function returns (DataFrame, stats_dict); stats feed the quality report.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd
from pyproj import Transformer

from src import config
from src.tools.address import normalize_address

_TO_TX_FT = Transformer.from_crs(config.CRS_WGS84, config.CRS_TX_CENTRAL_FT, always_xy=True)


def _project_xy(df: pd.DataFrame, lon_col: str, lat_col: str) -> pd.DataFrame:
    """Add EPSG:2277 x_ft / y_ft columns (NaN where coordinates are missing)."""
    lon = pd.to_numeric(df[lon_col], errors="coerce")
    lat = pd.to_numeric(df[lat_col], errors="coerce")
    x = np.full(len(df), np.nan)
    y = np.full(len(df), np.nan)
    mask = lon.notna() & lat.notna()
    if mask.any():
        xs, ys = _TO_TX_FT.transform(lon[mask].to_numpy(), lat[mask].to_numpy())
        x[mask.to_numpy()] = xs
        y[mask.to_numpy()] = ys
    df["longitude"] = lon
    df["latitude"] = lat
    df["x_ft"] = x
    df["y_ft"] = y
    return df


def _parse_wkt_point(series: pd.Series) -> tuple[pd.Series, pd.Series]:
    """'POINT (-97.74 30.26)' -> (lon, lat); NaN when absent/malformed."""
    pat = series.str.extract(r"POINT \(([-\d.]+) ([-\d.]+)\)")
    return pd.to_numeric(pat[0], errors="coerce"), pd.to_numeric(pat[1], errors="coerce")


# --------------------------------------------------------------------------- #
# Zoning
# --------------------------------------------------------------------------- #
def clean_zoning() -> tuple[pd.DataFrame, dict]:
    df = pd.read_csv(config.ZONING_CSV, dtype=str)
    stats = {"rows_in": len(df)}

    norm = df["FULL_STREET_NAME"].map(lambda s: normalize_address(s))
    df["address_normalized"] = [n.normalized for n in norm]
    df["street_number"] = [n.street_number for n in norm]
    df["street_name"] = [n.street_name for n in norm]
    df["street_suffix"] = [n.suffix for n in norm]
    df["parse_method"] = [n.parse_method for n in norm]
    stats["regex_fallback_parses"] = int((df["parse_method"] == "regex_fallback").sum())
    stats["normalized_empty"] = int((df["address_normalized"] == "").sum())

    # Exact duplicate rows (same address, same zoning) add nothing.
    before = len(df)
    df = df.drop_duplicates(subset=["address_normalized", "ZONING_ZTYPE"]).copy()
    stats["exact_dup_address_zoning_removed"] = before - len(df)

    # Addresses with >1 distinct designation are legitimate multi-zoning
    # records: keep every row, flag the address.
    multi = df.groupby("address_normalized")["ZONING_ZTYPE"].transform("nunique") > 1
    df["has_multiple_zoning"] = multi
    stats["addresses_with_multiple_zoning"] = int(
        df.loc[multi, "address_normalized"].nunique()
    )
    stats["null_zoning"] = int(df["ZONING_ZTYPE"].isna().sum())
    stats["rows_out"] = len(df)
    return df, stats


# --------------------------------------------------------------------------- #
# Permits
# --------------------------------------------------------------------------- #
_PERMIT_AUDIT_FIELDS = [
    "status_current", "issue_date", "completed_date", "description",
    "total_job_valuation", "latitude", "longitude", "work_class",
]


def clean_permits() -> tuple[pd.DataFrame, dict]:
    df = pd.read_csv(config.PERMITS_CSV, dtype=str)
    stats = {"rows_in": len(df)}

    before = len(df)
    df = df.drop_duplicates().copy()
    stats["exact_duplicate_rows_removed"] = before - len(df)

    # Audit duplicate permit numbers instead of blind dedup: collapse only
    # rows identical across meaningful fields; keep genuine variants.
    dup_mask = df.duplicated(subset=["permit_number"], keep=False)
    stats["duplicate_permit_numbers_before_audit"] = int(
        df.loc[dup_mask, "permit_number"].nunique()
    )
    before = len(df)
    df = df.drop_duplicates(subset=["permit_number"] + _PERMIT_AUDIT_FIELDS).copy()
    stats["dup_permit_rows_identical_on_audit_fields_removed"] = before - len(df)
    still_dup = df.duplicated(subset=["permit_number"], keep=False)
    df["duplicate_permit_number"] = still_dup
    stats["permit_numbers_retained_with_variants"] = int(
        df.loc[still_dup, "permit_number"].nunique()
    )

    for col in ("applieddate", "issue_date", "completed_date"):
        df[col] = pd.to_datetime(df[col], errors="coerce")
    for col in ("total_existing_bldg_sqft", "remodel_repair_sqft", "total_new_add_sqft",
                "total_job_valuation", "number_of_floors", "housing_units",
                "total_lot_sq_ft"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = _project_xy(df, "longitude", "latitude")
    stats["rows_missing_coordinates"] = int(df["x_ft"].isna().sum())

    norm = df["permit_location"].fillna("").map(lambda s: normalize_address(s))
    df["address_normalized"] = [n.normalized for n in norm]
    stats["rows_out"] = len(df)
    return df, stats


# --------------------------------------------------------------------------- #
# Site-plan cases (allow-listed output)
# --------------------------------------------------------------------------- #
SITE_PLAN_ALLOWED = [
    "FOLDERRSN", "CASE_TYPE", "CASE_NAME", "PERMIT_NUMBER", "SUB_TYPE", "WORK",
    "STATUS", "DESCRIPTION_OF_WORK", "PROPOSED_LAND_USE", "LINK", "STATUS_DATE",
    "APPROVAL_DATE", "FINAL_DATE", "APPLICATION_START_DATE",
    "CALENDAR_YEAR_FOLDER_CREATED", "STREET_NUMBER", "STREET_PREFIX",
    "STREET_DIRECTION", "STREET_NAME", "STREET_TYPE", "LATITUDE", "LONGITUDE",
    "CITY", "ZIP_CODE", "NEIGHBORHOOD_PLAN_NAME", "COUNCIL_DISTRICT",
    "WATERSHED_CLASS", "WATERSHED", "LEGAL_DESCRIPTION", "EXISTING_ZONING",
    "EXISTING_LAND_USE", "EXISTING_NO_OF_UNITS", "PROPOSED_NO_OF_UNITS",
    "RELATED_CASES", "SMART_HOUSING", "GROSS_SITE_AREA_ACRES",
    "PROPOSED_BLDG_SQ_FOOTAGE", "TIA_REQUIRED", "TIA_SUBMITTED",
    "PROP_IMPERVIOUS_COVER_PERCENT", "Jurisdiction",
]


def clean_site_plans() -> tuple[pd.DataFrame, dict]:
    raw = pd.read_csv(config.SITE_PLANS_CSV, dtype=str, low_memory=False)
    stats = {"rows_in": len(raw), "columns_in": len(raw.columns)}

    df = raw[[c for c in SITE_PLAN_ALLOWED if c in raw.columns]].copy()
    stats["columns_dropped_by_allowlist"] = len(raw.columns) - len(df.columns)

    before = len(df)
    df = df.drop_duplicates().copy()
    stats["exact_duplicate_rows_removed"] = before - len(df)

    for col in ("APPROVAL_DATE", "FINAL_DATE", "APPLICATION_START_DATE"):
        df[col] = pd.to_datetime(df[col], errors="coerce", format="mixed")
    df["STATUS_DATE"] = pd.to_datetime(
        df["STATUS_DATE"], errors="coerce", format="%Y %b %d %I:%M:%S %p"
    )
    for col in ("GROSS_SITE_AREA_ACRES", "PROPOSED_BLDG_SQ_FOOTAGE",
                "PROP_IMPERVIOUS_COVER_PERCENT", "EXISTING_NO_OF_UNITS",
                "PROPOSED_NO_OF_UNITS"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = _project_xy(df, "LONGITUDE", "LATITUDE")
    df["no_geometry"] = df["x_ft"].isna()
    stats["rows_missing_coordinates"] = int(df["no_geometry"].sum())

    addr = (
        df["STREET_NUMBER"].fillna("") + " "
        + df["STREET_DIRECTION"].fillna("") + " "
        + df["STREET_NAME"].fillna("") + " "
        + df["STREET_TYPE"].fillna("")
    ).str.strip()
    df["address_normalized"] = addr.map(lambda s: normalize_address(s).normalized if s else "")
    stats["rows_out"] = len(df)
    return df, stats


# --------------------------------------------------------------------------- #
# Plan-review cases (allow-listed output; VOID kept but flagged)
# --------------------------------------------------------------------------- #
PLAN_REVIEW_ALLOWED = [
    "Case_Type", "Folder_Type", "Sub_Type", "Work_Class", "Permit_Number",
    "Referencefile", "Project_Name", "Folder_Description", "Express_Permit",
    "Folderrsn", "Web_Link", "Status_Current", "Status_Date", "Condominium",
    "Issued_Date", "Applied_Date", "Expires_Date", "Final_Date",
    "Number_Of_Floors", "Number_Of_Units", "Remodel_Repair_Footage",
    "Total_Existing_Bldg_Footage", "Total_Job_Valuation",
    "Total_New_Add_Footage", "Council_District", "Legal_Description",
    "Location", "Update_Date",
]


def clean_plan_review() -> tuple[pd.DataFrame, dict]:
    raw = pd.read_csv(config.PLAN_REVIEW_CSV, dtype=str, low_memory=False)
    stats = {"rows_in": len(raw), "columns_in": len(raw.columns)}

    df = raw[[c for c in PLAN_REVIEW_ALLOWED if c in raw.columns]].copy()
    stats["columns_dropped_by_allowlist"] = len(raw.columns) - len(df.columns)

    before = len(df)
    df = df.drop_duplicates().copy()
    stats["exact_duplicate_rows_removed"] = before - len(df)

    for col in ("Status_Date", "Applied_Date", "Issued_Date", "Expires_Date",
                "Final_Date"):
        df[col] = pd.to_datetime(df[col], errors="coerce",
                                 format="%Y %b %d %I:%M:%S %p")
    for col in ("Number_Of_Floors", "Number_Of_Units", "Total_Job_Valuation",
                "Remodel_Repair_Footage", "Total_Existing_Bldg_Footage",
                "Total_New_Add_Footage"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    lon, lat = _parse_wkt_point(df["Location"].fillna(""))
    df["longitude"], df["latitude"] = lon, lat
    df = _project_xy(df, "longitude", "latitude")
    stats["rows_missing_coordinates"] = int(df["x_ft"].isna().sum())

    # Retained-but-excluded records (auditability): VOID status or test rows.
    desc = df["Folder_Description"].fillna("").str.upper()
    void = df["Status_Current"].fillna("").str.upper().eq("VOID")
    test = desc.str.contains(r"\bTEST\b", regex=True)
    df["exclude_from_search"] = void | test
    df["exclusion_reason"] = np.select(
        [void & test, void, test],
        ["VOID record; test record", "VOID record", "test record"],
        default="",
    )
    stats["rows_flagged_excluded"] = int(df["exclude_from_search"].sum())
    stats["rows_out"] = len(df)
    return df, stats
