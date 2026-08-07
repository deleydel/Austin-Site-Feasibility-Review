"""Task 3: address geocoding.

Order of precedence:
1. Manual coordinates (caller override) — always wins.
2. Local records: permit and site-plan rows at the same normalized address.
   Conflicting coordinates are surfaced as `ambiguous`, never averaged
   silently (disagreement threshold 200 ft, computed in EPSG:2277).
3. US Census Bureau geocoder (network; degrades gracefully offline).

Every result reports source, method, confidence, record count, and the
coordinate disagreement observed.
"""
from __future__ import annotations

import numpy as np
import requests

from src.tools import _data
from src.tools.address import normalize_address

DISAGREEMENT_THRESHOLD_FT = 200.0
CENSUS_URL = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"


def _local_candidates(normalized: str) -> list[dict]:
    rows = []
    p = _data.permits()
    hits = p[(p["address_normalized"] == normalized) & p["x_ft"].notna()]
    for r in hits.itertuples():
        rows.append({"dataset": "permits", "lat": r.latitude, "lon": r.longitude,
                     "x_ft": r.x_ft, "y_ft": r.y_ft})
    s = _data.site_plans()
    addr = s["address_normalized"] == normalized
    hits = s[addr & s["x_ft"].notna()]
    for r in hits.itertuples():
        rows.append({"dataset": "site_plans", "lat": r.latitude, "lon": r.longitude,
                     "x_ft": r.x_ft, "y_ft": r.y_ft})
    return rows


def geocode(address: str, manual_lat: float | None = None,
            manual_lon: float | None = None, allow_network: bool = True) -> dict:
    norm = normalize_address(address)
    out = {"query_address": address, "normalized_address": norm.normalized}

    if manual_lat is not None and manual_lon is not None:
        return {**out, "status": "found", "latitude": manual_lat,
                "longitude": manual_lon, "source": "manual",
                "method": "user_provided_coordinates", "confidence": "user_provided",
                "n_records": 0, "max_disagreement_ft": 0.0}

    if not norm.normalized:
        return {**out, "status": "not_found", "detail": "Address could not be parsed."}

    local = _local_candidates(norm.normalized)
    if local:
        xs = np.array([c["x_ft"] for c in local])
        ys = np.array([c["y_ft"] for c in local])
        # max pairwise spread in feet
        spread = float(np.hypot(xs[:, None] - xs[None, :],
                                ys[:, None] - ys[None, :]).max())
        if spread <= DISAGREEMENT_THRESHOLD_FT:
            lat = float(np.median([c["lat"] for c in local]))
            lon = float(np.median([c["lon"] for c in local]))
            return {**out, "status": "found", "latitude": lat, "longitude": lon,
                    "source": "local_records",
                    "method": "normalized_address_match_median",
                    "confidence": "high" if len(local) >= 2 else "medium",
                    "n_records": len(local),
                    "max_disagreement_ft": round(spread, 1)}
        return {**out, "status": "ambiguous", "source": "local_records",
                "method": "normalized_address_match",
                "n_records": len(local),
                "max_disagreement_ft": round(spread, 1),
                "candidates": [{"dataset": c["dataset"], "latitude": c["lat"],
                                "longitude": c["lon"]} for c in local],
                "detail": f"Matching records disagree by {spread:.0f} ft "
                          f"(> {DISAGREEMENT_THRESHOLD_FT:.0f} ft); coordinates "
                          "were not averaged. Provide manual coordinates or "
                          "confirm a candidate."}

    if allow_network:
        try:
            resp = requests.get(CENSUS_URL, params={
                "address": f"{address}, Austin, TX",
                "benchmark": "Public_AR_Current", "format": "json"}, timeout=10)
            matches = resp.json().get("result", {}).get("addressMatches", [])
            if matches:
                c = matches[0]["coordinates"]
                return {**out, "status": "found", "latitude": c["y"],
                        "longitude": c["x"], "source": "us_census_geocoder",
                        "method": "census_onelineaddress",
                        "confidence": "medium", "n_records": len(matches),
                        "max_disagreement_ft": None,
                        "matched_address": matches[0].get("matchedAddress")}
        except Exception as e:  # network failure is a normal condition here
            return {**out, "status": "not_found",
                    "detail": f"No local coordinate records; Census geocoder "
                              f"unavailable ({type(e).__name__}). Provide "
                              "manual coordinates."}
    return {**out, "status": "not_found",
            "detail": "No coordinate records found for this address. "
                      "Provide manual coordinates."}
