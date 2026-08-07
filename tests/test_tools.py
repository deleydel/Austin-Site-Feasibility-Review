"""Task 3 correctness tests: ground-truth checks, false-positive checks,
boundary coordinates, conflicting records, and the PII allow-list.

Run:  python -m pytest tests/test_tools.py -v
"""
from __future__ import annotations

import numpy as np

from src.tools import _data
from src.tools.address import normalize_address
from src.tools.geocode import geocode
from src.tools.nearby import (nearby_permits, nearby_plan_review_cases,
                              nearby_site_plan_cases)
from src.tools.spatial import floodplain_check, watershed_lookup
from src.tools.zoning import zoning_lookup

# Ground truth taken from the datasets themselves (verified rows).
KNOWN_ADDRESS = "1714 MADISON AVE"          # permit row with coordinates
KNOWN_LAT, KNOWN_LON = 30.34593535, -97.72842751


# --------------------------------------------------------------------- #
# Address normalization
# --------------------------------------------------------------------- #
def test_normalize_suffix_and_case():
    n = normalize_address("1714 Madison Avenue")
    assert n.normalized == "1714 MADISON AVE"


def test_normalize_fractional():
    n = normalize_address("6008 1/2 Cervinus Run")
    assert n.street_number == "6008 1/2"
    assert n.normalized == "6008 1/2 CERVINUS RUN"


def test_normalize_garbage_does_not_crash():
    n = normalize_address("???")
    assert n.normalized == "" or isinstance(n.normalized, str)


# --------------------------------------------------------------------- #
# Zoning lookup
# --------------------------------------------------------------------- #
def test_zoning_exact_match():
    r = zoning_lookup("1714 Madison Avenue")
    assert r["status"] == "found" and r["match_type"] == "exact"
    assert r["zoning"] == "SF-3-NP"
    assert r["verification_required"] is True


def test_zoning_multiple_records_not_collapsed():
    z = _data.zoning()
    addr = z[z["has_multiple_zoning"]]["address_normalized"].iloc[0]
    r = zoning_lookup(addr)
    assert r["status"] == "multiple_records"
    assert len(r["zoning_designations"]) > 1
    assert "zoning" not in r          # no single answer auto-selected


def test_zoning_never_returns_neighbor_number():
    """False-positive check: unknown street number on a real street must NOT
    inherit a neighbor's zoning."""
    r = zoning_lookup("99999 MADISON AVE")
    assert r["status"] in ("ambiguous", "not_found")
    assert "zoning" not in r


def test_zoning_nonsense_not_found_or_ambiguous():
    r = zoning_lookup("123 TOTALLY FAKE STREET XYZZY")
    assert r["status"] in ("not_found", "ambiguous")
    assert "zoning" not in r


def test_zoning_fuzzy_same_number_only():
    """A small typo with the same street number may fuzzy-match, but the
    result must be labeled and carry a warning."""
    r = zoning_lookup("1714 MADISONN AVE")
    if r["status"] == "fuzzy_match":
        assert r["match_type"] == "same_street_number_textual"
        assert "warning" in r
    else:
        assert r["status"] in ("ambiguous", "not_found")


# --------------------------------------------------------------------- #
# Geocoding
# --------------------------------------------------------------------- #
def test_geocode_local_records():
    g = geocode(KNOWN_ADDRESS, allow_network=False)
    assert g["status"] == "found" and g["source"] == "local_records"
    assert abs(g["latitude"] - KNOWN_LAT) < 1e-4
    assert g["n_records"] >= 1
    assert g["max_disagreement_ft"] <= 200


def test_geocode_manual_override_wins():
    g = geocode(KNOWN_ADDRESS, manual_lat=30.0, manual_lon=-97.7)
    assert g["source"] == "manual" and g["latitude"] == 30.0


def test_geocode_conflicting_records_ambiguous(monkeypatch):
    """Synthetic conflict: two records >200 ft apart must yield ambiguous,
    not a silent average."""
    from src.tools import geocode as gc
    fake = [
        {"dataset": "permits", "lat": 30.30, "lon": -97.70, "x_ft": 0.0, "y_ft": 0.0},
        {"dataset": "site_plans", "lat": 30.31, "lon": -97.71, "x_ft": 5000.0, "y_ft": 0.0},
    ]
    monkeypatch.setattr(gc, "_local_candidates", lambda _: fake)
    g = gc.geocode("1 CONFLICT ST", allow_network=False)
    assert g["status"] == "ambiguous"
    assert g["max_disagreement_ft"] == 5000.0
    assert "latitude" not in g        # nothing averaged


def test_geocode_unknown_address_not_found():
    g = geocode("1 NOWHERE BLVD ZZZZZ", allow_network=False)
    assert g["status"] == "not_found"


# --------------------------------------------------------------------- #
# Floodplain / watershed
# --------------------------------------------------------------------- #
def test_watershed_known_point():
    w = watershed_lookup(KNOWN_LAT, KNOWN_LON)
    assert w["status"] == "found"
    assert w["watershed"] == "Shoal Creek"


def test_floodplain_point_inside_polygon():
    """Use a floodplain polygon's own representative point as ground truth."""
    gdf = _data.floodplain()
    rep = gdf.geometry.iloc[0].representative_point()
    lon, lat = (
        __import__("pyproj").Transformer
        .from_crs("EPSG:2277", "EPSG:4326", always_xy=True)
        .transform(rep.x, rep.y)
    )
    f = floodplain_check(lat, lon)
    assert f["intersects_floodplain"] is True
    assert f["flood_zones"]


def test_floodplain_point_outside_reports_distance_only():
    f = floodplain_check(KNOWN_LAT, KNOWN_LON)
    assert f["intersects_floodplain"] is False
    assert f["nearest_floodplain_distance_ft"] > 0
    assert "no regulatory conclusion" in f["interpretation"].lower()


def test_floodplain_boundary_point():
    """A point ON a polygon boundary must intersect (closed-set semantics),
    not fall through the cracks."""
    gdf = _data.floodplain()
    poly = gdf.geometry.iloc[0]
    boundary_pt = poly.exterior.interpolate(0.5, normalized=True) \
        if poly.geom_type == "Polygon" else \
        poly.geoms[0].exterior.interpolate(0.5, normalized=True)
    from pyproj import Transformer
    lon, lat = Transformer.from_crs("EPSG:2277", "EPSG:4326", always_xy=True) \
        .transform(boundary_pt.x, boundary_pt.y)
    f = floodplain_check(lat, lon)
    # Reprojection wobble can land the point a hair outside; either it
    # intersects or it is within a few feet — never a silent large miss.
    assert f["intersects_floodplain"] or f["nearest_floodplain_distance_ft"] < 5


def test_watershed_boundary_point_reports_all_or_one():
    gdf = _data.watersheds()
    poly = gdf.geometry.iloc[0]
    g = poly.geoms[0] if poly.geom_type == "MultiPolygon" else poly
    bpt = g.exterior.interpolate(0.25, normalized=True)
    from pyproj import Transformer
    lon, lat = Transformer.from_crs("EPSG:2277", "EPSG:4326", always_xy=True) \
        .transform(bpt.x, bpt.y)
    w = watershed_lookup(lat, lon)
    assert w["status"] in ("found", "boundary", "not_found")
    if w["status"] == "boundary":
        assert len(w["matches"]) > 1


# --------------------------------------------------------------------- #
# Nearby records
# --------------------------------------------------------------------- #
def test_nearby_permits_distances_match_manual_math():
    p = nearby_permits(KNOWN_LAT, KNOWN_LON, radius_ft=800)
    assert p["status"] == "found"
    assert p["records"][0]["distance_ft"] < 50   # the permit at this address
    # independent verification of the reported distance
    df = _data.permits()
    pt = _data.to_tx_ft(KNOWN_LAT, KNOWN_LON)
    row = df[df["permit_number"] == p["records"][0]["permit_number"]].iloc[0]
    manual = float(np.hypot(row["x_ft"] - pt.x, row["y_ft"] - pt.y))
    assert abs(manual - p["records"][0]["distance_ft"]) < 1.0
    # radius respected
    assert all(r["distance_ft"] <= 800 for r in p["records"])


def test_nearby_results_sorted_and_limited():
    p = nearby_permits(KNOWN_LAT, KNOWN_LON, radius_ft=2000, limit=10)
    d = [r["distance_ft"] for r in p["records"]]
    assert d == sorted(d) and len(d) <= 10


def test_nearby_no_pii_fields():
    recs = (nearby_permits(KNOWN_LAT, KNOWN_LON)["records"]
            + nearby_site_plan_cases(KNOWN_LAT, KNOWN_LON, radius_ft=5000)["records"]
            + nearby_plan_review_cases(KNOWN_LAT, KNOWN_LON)["records"])
    banned = ("applicant", "owner", "phone", "email", "contact")
    for rec in recs:
        for key in rec:
            assert not any(b in key.lower() for b in banned), key


def test_nearby_plan_review_excludes_void():
    df = _data.plan_review()
    void = df[df["exclude_from_search"] & df["x_ft"].notna()]
    assert len(void) > 0
    row = void.iloc[0]
    res = nearby_plan_review_cases(row["latitude"], row["longitude"],
                                   radius_ft=1, years=None, limit=50)
    nums = {r.get("permit_number") for r in res["records"]}
    assert row["Permit_Number"] not in nums


def test_nearby_history_disclaimer_present():
    p = nearby_permits(KNOWN_LAT, KNOWN_LON)
    assert "not" in p["note"] and "approv" in p["note"]


# Latency measurement lives in evaluation/tools/run_latency.py.
