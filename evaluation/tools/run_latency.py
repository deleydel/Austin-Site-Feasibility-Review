"""Task 3 performance evaluation: observed latency of every structured-data
tool on this machine (warm caches). Figures are measured observations, not
guarantees. Writes evaluation/results/tool_latency_ms.json.

Run:  python -m evaluation.tools.run_latency
"""
from __future__ import annotations

import json
import statistics
import time

from src import config
from src.tools.geocode import geocode
from src.tools.nearby import (nearby_permits, nearby_plan_review_cases,
                              nearby_site_plan_cases)
from src.tools.spatial import floodplain_check, watershed_lookup
from src.tools.zoning import zoning_lookup

ADDRESS = "1714 MADISON AVE"
LAT, LON = 30.34593535, -97.72842751
REPEATS = 5


def main() -> None:
    calls = {
        "zoning_lookup": lambda: zoning_lookup(ADDRESS),
        "geocode_local": lambda: geocode(ADDRESS, allow_network=False),
        "floodplain_check": lambda: floodplain_check(LAT, LON),
        "watershed_lookup": lambda: watershed_lookup(LAT, LON),
        "nearby_permits": lambda: nearby_permits(LAT, LON),
        "nearby_site_plans": lambda: nearby_site_plan_cases(LAT, LON),
        "nearby_plan_review": lambda: nearby_plan_review_cases(LAT, LON),
    }
    for fn in calls.values():   # warm data caches and spatial indexes
        fn()

    results = {}
    for name, fn in calls.items():
        samples = []
        for _ in range(REPEATS):
            t0 = time.perf_counter()
            fn()
            samples.append(1000 * (time.perf_counter() - t0))
        results[name] = {
            "median_ms": round(statistics.median(samples), 1),
            "max_ms": round(max(samples), 1),
            "repeats": REPEATS,
        }

    out = config.REPORTS_DIR / "tool_latency_ms.json"
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
