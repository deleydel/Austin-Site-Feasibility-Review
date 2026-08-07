"""Task 1: watershed and floodplain GeoJSON cleaning.

- Repairs invalid geometries with shapely make_valid.
- Stores geometry in EPSG:2277 (Texas Central State Plane, US survey feet),
  the CRS used for every distance/intersection computation in Task 3.
  Lat/lon inputs are converted at query time.
"""
from __future__ import annotations

import geopandas as gpd
from shapely.validation import make_valid

from src import config

WATERSHED_KEEP = [
    "watershed_id", "watershed_code", "watershed_full_name", "display_name",
    "receiving_basin", "receiving_waters", "shape_area", "geometry",
]
FLOODPLAIN_KEEP = [
    "objectid", "drainage_id", "flood_zone", "floodway", "source_citation",
    "shape_area", "geometry",
]


def _repair(gdf: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, int]:
    invalid = ~gdf.geometry.is_valid
    n = int(invalid.sum())
    if n:
        gdf.loc[invalid, "geometry"] = gdf.loc[invalid, "geometry"].map(make_valid)
    return gdf, n


def clean_watersheds() -> tuple[gpd.GeoDataFrame, dict]:
    gdf = gpd.read_file(config.WATERSHEDS_GEOJSON)
    stats = {"features_in": len(gdf)}
    gdf, stats["invalid_geometries_repaired"] = _repair(gdf)
    gdf = gdf[[c for c in WATERSHED_KEEP if c in gdf.columns]]
    gdf = gdf.set_crs(config.CRS_WGS84, allow_override=True).to_crs(config.CRS_TX_CENTRAL_FT)
    stats["features_out"] = len(gdf)
    stats["crs_out"] = config.CRS_TX_CENTRAL_FT
    return gdf, stats


def clean_floodplain() -> tuple[gpd.GeoDataFrame, dict]:
    gdf = gpd.read_file(config.FLOODPLAIN_GEOJSON)
    stats = {"features_in": len(gdf)}
    gdf, stats["invalid_geometries_repaired"] = _repair(gdf)
    gdf = gdf[[c for c in FLOODPLAIN_KEEP if c in gdf.columns]]
    stats["null_flood_zone"] = int(gdf["flood_zone"].isna().sum())
    stats["flood_zone_values"] = sorted(gdf["flood_zone"].dropna().unique().tolist())
    gdf = gdf.set_crs(config.CRS_WGS84, allow_override=True).to_crs(config.CRS_TX_CENTRAL_FT)
    stats["features_out"] = len(gdf)
    stats["crs_out"] = config.CRS_TX_CENTRAL_FT
    return gdf, stats
