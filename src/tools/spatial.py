"""Task 3: floodplain and watershed point checks.

All geometry math runs in EPSG:2277 (US survey feet); distances are feet.
Floodplain proximity is reported as informational context only — no
regulatory conclusion is attached to any distance threshold.
"""
from __future__ import annotations

from src.tools import _data

PROXIMITY_NOTE = "Informational proximity only; no regulatory conclusion."


def floodplain_check(lat: float, lon: float) -> dict:
    pt = _data.to_tx_ft(lat, lon)
    gdf = _data.floodplain()
    tree = _data.floodplain_tree()

    idx = tree.query(pt, predicate="intersects")
    if len(idx):
        zones = []
        for i in idx:
            row = gdf.iloc[i]
            zones.append({
                "flood_zone": row["flood_zone"],
                "floodway": row["floodway"],
                "drainage_id": row["drainage_id"],
                "source_citation": row["source_citation"],
            })
        return {
            "status": "found", "latitude": lat, "longitude": lon,
            "intersects_floodplain": True,
            "flood_zones": zones,
            "interpretation": "Point intersects mapped floodplain polygon(s) "
                              "in the City of Austin fully developed "
                              "floodplain dataset. Preliminary screening "
                              "only; an engineering flood study governs.",
        }

    nearest_i = tree.nearest(pt)
    nearest = gdf.iloc[nearest_i]
    dist_ft = float(pt.distance(nearest.geometry))
    return {
        "status": "found", "latitude": lat, "longitude": lon,
        "intersects_floodplain": False,
        "nearest_floodplain_distance_ft": round(dist_ft, 1),
        "nearest_flood_zone": nearest["flood_zone"],
        "interpretation": PROXIMITY_NOTE,
    }


def watershed_lookup(lat: float, lon: float) -> dict:
    pt = _data.to_tx_ft(lat, lon)
    gdf = _data.watersheds()
    tree = _data.watershed_tree()

    idx = tree.query(pt, predicate="intersects")
    matches = [{
        "watershed": gdf.iloc[i]["watershed_full_name"],
        "watershed_code": gdf.iloc[i]["watershed_code"],
        "receiving_basin": gdf.iloc[i]["receiving_basin"],
        "receiving_waters": gdf.iloc[i]["receiving_waters"],
    } for i in idx]

    if len(matches) == 1:
        return {"status": "found", "latitude": lat, "longitude": lon, **matches[0]}
    if len(matches) > 1:
        # Point sits on a shared boundary — report all, choose none.
        return {"status": "boundary", "latitude": lat, "longitude": lon,
                "matches": matches,
                "detail": "Point lies on a watershed boundary; multiple "
                          "watersheds intersect. Verification required."}

    nearest_i = tree.nearest(pt)
    nearest = gdf.iloc[nearest_i]
    dist_ft = float(pt.distance(nearest.geometry))
    return {"status": "not_found", "latitude": lat, "longitude": lon,
            "nearest_watershed": nearest["watershed_full_name"],
            "nearest_watershed_distance_ft": round(dist_ft, 1),
            "detail": "Point is outside all mapped Austin watershed "
                      "boundaries in this dataset."}
