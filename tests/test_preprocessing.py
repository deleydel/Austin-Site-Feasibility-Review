"""Task 1 correctness tests: cleaning rules, parsing, geometry validity,
PII removal, and data-quality invariants, checked against the processed
outputs in data/processed/.

Run:  python -m pytest tests/test_preprocessing.py -v
"""
from __future__ import annotations

import json

import geopandas as gpd
import pandas as pd
import pytest

from src import config
from src.preprocessing.structured import PLAN_REVIEW_ALLOWED, SITE_PLAN_ALLOWED

PII_TOKENS = ("applicant", "owner", "phone", "email", "contact", "manager")


@pytest.fixture(scope="module")
def zoning():
    return pd.read_parquet(config.ZONING_PARQUET)


@pytest.fixture(scope="module")
def permits():
    return pd.read_parquet(config.PERMITS_PARQUET)


@pytest.fixture(scope="module")
def site_plans():
    return pd.read_parquet(config.SITE_PLANS_PARQUET)


@pytest.fixture(scope="module")
def plan_review():
    return pd.read_parquet(config.PLAN_REVIEW_PARQUET)


# --------------------------------------------------------------------- #
# Zoning
# --------------------------------------------------------------------- #
def test_zoning_no_null_designations(zoning):
    assert zoning["ZONING_ZTYPE"].notna().all()


def test_zoning_multi_designation_addresses_preserved(zoning):
    """Addresses with several distinct zoning designations must keep every
    row (never collapsed to one)."""
    multi = zoning[zoning["has_multiple_zoning"]]
    assert len(multi) > 0
    per_addr = multi.groupby("address_normalized")["ZONING_ZTYPE"].nunique()
    assert (per_addr > 1).all()


def test_zoning_no_exact_address_zoning_duplicates(zoning):
    assert not zoning.duplicated(["address_normalized", "ZONING_ZTYPE"]).any()


def test_zoning_addresses_normalized(zoning):
    sample = zoning["address_normalized"].dropna().head(1000)
    assert (sample == sample.str.upper()).all()
    assert not sample.str.contains(r"\s{2,}").any()


# --------------------------------------------------------------------- #
# Permits
# --------------------------------------------------------------------- #
def test_permits_dates_parsed(permits):
    assert pd.api.types.is_datetime64_any_dtype(permits["issue_date"])
    assert permits["issue_date"].notna().mean() > 0.9


def test_permits_duplicate_numbers_audited_not_blindly_dropped(permits):
    """Rows sharing a permit_number may exist only if flagged as variants."""
    dup = permits[permits.duplicated("permit_number", keep=False)]
    assert dup["duplicate_permit_number"].all() if len(dup) else True


def test_permits_projected_coordinates_present(permits):
    has = permits["x_ft"].notna()
    assert has.mean() > 0.99
    # EPSG:2277 easting/northing for Austin sits in a known range (survey ft)
    assert permits.loc[has, "x_ft"].between(2_900_000, 3_300_000).all()
    assert permits.loc[has, "y_ft"].between(9_900_000, 10_400_000).all()


# --------------------------------------------------------------------- #
# PII allow-lists
# --------------------------------------------------------------------- #
def test_site_plans_only_allowlisted_plus_derived(site_plans):
    derived = {"longitude", "latitude", "x_ft", "y_ft", "no_geometry",
               "address_normalized"}
    extra = set(site_plans.columns) - set(SITE_PLAN_ALLOWED) - derived
    assert extra == set()


def test_no_pii_columns_in_outputs(site_plans, plan_review):
    for df in (site_plans, plan_review):
        for col in df.columns:
            assert not any(t in col.lower() for t in PII_TOKENS), col


def test_plan_review_only_allowlisted_plus_derived(plan_review):
    derived = {"longitude", "latitude", "x_ft", "y_ft",
               "exclude_from_search", "exclusion_reason"}
    extra = set(plan_review.columns) - set(PLAN_REVIEW_ALLOWED) - derived
    assert extra == set()


# --------------------------------------------------------------------- #
# VOID/test retention
# --------------------------------------------------------------------- #
def test_void_records_retained_and_flagged(plan_review):
    flagged = plan_review[plan_review["exclude_from_search"]]
    assert len(flagged) > 0                       # retained, not deleted
    assert (flagged["exclusion_reason"] != "").all()
    void = plan_review["Status_Current"].fillna("").str.upper() == "VOID"
    assert plan_review.loc[void, "exclude_from_search"].all()


# --------------------------------------------------------------------- #
# Geodata
# --------------------------------------------------------------------- #
def test_geodata_valid_and_in_feet_crs():
    for path in (config.WATERSHEDS_PARQUET, config.FLOODPLAIN_PARQUET):
        gdf = gpd.read_parquet(path)
        assert gdf.crs.to_epsg() == int(config.CRS_TX_CENTRAL_FT.split(":")[1])
        assert gdf.geometry.is_valid.all()


def test_watersheds_complete():
    gdf = gpd.read_parquet(config.WATERSHEDS_PARQUET)
    assert len(gdf) == 76
    assert gdf["watershed_full_name"].notna().all()


# --------------------------------------------------------------------- #
# Manifest / quality artifacts
# --------------------------------------------------------------------- #
def test_source_manifest_covers_every_dataset():
    manifest = json.loads(config.SOURCE_MANIFEST.read_text())
    ids = {s["id"] for s in manifest["sources"]}
    assert len(ids) == 9        # 3 regulatory docs + 6 structured datasets
    assert all(s.get("url") and s.get("limitations") for s in manifest["sources"])


def test_quality_stats_written():
    stats = json.loads((config.DATA_PROCESSED / "quality_stats.json").read_text())
    assert {"Zoning by Address", "Issued Construction Permits",
            "Site Plan Cases", "Plan Review Cases"} <= set(stats)
