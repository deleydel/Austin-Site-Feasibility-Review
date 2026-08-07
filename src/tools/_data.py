"""Lazy, cached access to processed datasets and spatial indexes (Task 3)."""
from __future__ import annotations

from functools import lru_cache

import geopandas as gpd
import pandas as pd
from pyproj import Transformer
from shapely.geometry import Point
from shapely.strtree import STRtree

from src import config

_TO_TX_FT = Transformer.from_crs(config.CRS_WGS84, config.CRS_TX_CENTRAL_FT, always_xy=True)


def to_tx_ft(lat: float, lon: float) -> Point:
    """WGS84 lat/lon -> EPSG:2277 point (US survey feet)."""
    x, y = _TO_TX_FT.transform(lon, lat)
    return Point(x, y)


@lru_cache(maxsize=1)
def zoning() -> pd.DataFrame:
    return pd.read_parquet(config.ZONING_PARQUET)


@lru_cache(maxsize=1)
def permits() -> pd.DataFrame:
    return pd.read_parquet(config.PERMITS_PARQUET)


@lru_cache(maxsize=1)
def site_plans() -> pd.DataFrame:
    return pd.read_parquet(config.SITE_PLANS_PARQUET)


@lru_cache(maxsize=1)
def plan_review() -> pd.DataFrame:
    return pd.read_parquet(config.PLAN_REVIEW_PARQUET)


@lru_cache(maxsize=1)
def watersheds() -> gpd.GeoDataFrame:
    return gpd.read_parquet(config.WATERSHEDS_PARQUET)


@lru_cache(maxsize=1)
def floodplain() -> gpd.GeoDataFrame:
    return gpd.read_parquet(config.FLOODPLAIN_PARQUET)


@lru_cache(maxsize=1)
def watershed_tree() -> STRtree:
    return STRtree(watersheds().geometry.values)


@lru_cache(maxsize=1)
def floodplain_tree() -> STRtree:
    return STRtree(floodplain().geometry.values)
