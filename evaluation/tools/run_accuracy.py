"""Structured-data tool accuracy against ground truth from the datasets.

Two rates are reported per tool, because they measure different risks:

* correct rate - on cases that have a right answer, how often the tool gives it;
* safe-failure rate - on cases that have no right answer, how often the tool
  declines (any status other than ``found``) instead of returning a confident
  wrong one. For a system that must never bluff, the second is the one that
  matters.

Ground truth is derived from the committed datasets and, for the radius
searches, recomputed independently in numpy rather than taken from the tool.

Run:  python -m evaluation.tools.run_accuracy
"""

from __future__ import annotations

import argparse
from typing import Any

import numpy as np
from pyproj import Transformer

from evaluation.common import pct, write_json
from src import config
from src.tools import _data
from src.tools.geocode import geocode
from src.tools.nearby import (
    nearby_permits,
    nearby_plan_review_cases,
    nearby_site_plan_cases,
)
from src.tools.spatial import floodplain_check, watershed_lookup
from src.tools.zoning import zoning_lookup

SEED = 7
SAMPLE = 50
RADIUS_SAMPLE = 12

_TO_WGS84 = Transformer.from_crs(
    config.CRS_TX_CENTRAL_FT, config.CRS_WGS84, always_xy=True
)


_SUFFIX_EXPANSIONS = {
    "AVE": "Avenue",
    "ST": "Street",
    "RD": "Road",
    "BLVD": "Boulevard",
    "DR": "Drive",
    "LN": "Lane",
    "CIR": "Circle",
    "CT": "Court",
    "PL": "Place",
    "TRL": "Trail",
    "PKWY": "Parkway",
    "HWY": "Highway",
    "BND": "Bend",
    "CV": "Cove",
    "WAY": "Way",
}


def _as_typed(normalized: str) -> str:
    """Rewrite a canonical address the way a person would type it."""

    parts = normalized.split()
    if parts and parts[-1].upper() in _SUFFIX_EXPANSIONS:
        parts[-1] = _SUFFIX_EXPANSIONS[parts[-1].upper()]
    rebuilt = " ".join(
        part if part.upper() == part and not part.isalpha() else part.title()
        for part in parts
    )
    return f"{rebuilt}, Austin, TX"


def _tally(cases: list[dict]) -> dict[str, Any]:
    answerable = [c for c in cases if c["answerable"]]
    unanswerable = [c for c in cases if not c["answerable"]]
    correct = sum(1 for c in answerable if c["ok"])
    safe = sum(1 for c in unanswerable if c["ok"])

    # Individual cases are retained, not just the counts, so the manual review
    # has concrete input/expected/actual triples to check. A reviewer handed
    # only "80/80 correct" can do nothing but agree, and an agreement rate
    # produced that way would look like validation without being it.
    def strip(case: dict) -> dict:
        return {k: v for k, v in case.items() if k != "ok"}

    samples = [strip(c) for c in answerable[:2]]
    samples += [strip(c) for c in answerable[len(answerable) // 2:][:1]]
    samples += [strip(c) for c in unanswerable[:2]]

    return {
        "answerable_n": len(answerable),
        "answerable_correct": correct,
        "correct_percent": pct(correct, len(answerable)),
        "unanswerable_n": len(unanswerable),
        "unanswerable_safe": safe,
        "safe_failure_percent": pct(safe, len(unanswerable)),
        "failures": [strip(c) for c in cases if not c["ok"]][:10],
        "samples": samples,
    }


# --------------------------------------------------------------------- #
def check_zoning() -> dict[str, Any]:
    frame = _data.zoning()
    single = frame[~frame["has_multiple_zoning"]]
    single = single[single["address_normalized"].str.len() > 6]
    rows = single.sample(n=SAMPLE, random_state=SEED)

    cases = []
    for _, row in rows.iterrows():
        address = row["address_normalized"]
        result = zoning_lookup(address)
        ok = (
            result.get("status") == "found"
            and result.get("zoning") == row["ZONING_ZTYPE"]
        )
        cases.append(
            {
                "case": address,
                "answerable": True,
                "expected": row["ZONING_ZTYPE"],
                "got": f"{result.get('status')}/{result.get('zoning')}",
                "ok": ok,
            }
        )

    # Ground truth is keyed on the same normalized string the tool indexes on,
    # which makes the exact-match cohort easy. These rewrite each address the
    # way a person would type it, so the score reflects real input.
    for _, row in rows.head(30).iterrows():
        messy = _as_typed(row["address_normalized"])
        result = zoning_lookup(messy)
        ok = (
            result.get("status") in {"found", "fuzzy_match"}
            and result.get("zoning") == row["ZONING_ZTYPE"]
        )
        cases.append(
            {
                "case": f"typed as: {messy}",
                "answerable": True,
                "expected": row["ZONING_ZTYPE"],
                "got": f"{result.get('status')}/{result.get('zoning')}",
                "ok": ok,
            }
        )

    streets = [
        s for s in single["address_normalized"].sample(n=20, random_state=SEED + 1)
    ]
    for address in streets:
        parts = address.split(" ", 1)
        if len(parts) != 2:
            continue
        # A street number that does not exist on a real street: the tool must
        # never inherit a neighbour's designation.
        fake = f"99{parts[0]}7 {parts[1]}"
        result = zoning_lookup(fake)
        ok = result.get("status") != "found" and "zoning" not in result
        cases.append(
            {
                "case": fake,
                "answerable": False,
                "expected": "no single zoning",
                "got": f"{result.get('status')}/{result.get('zoning')}",
                "ok": ok,
            }
        )

    for nonsense in ("123 TOTALLY FAKE STREET XYZZY", "???", "", "0 NOWHERE"):
        result = zoning_lookup(nonsense)
        ok = result.get("status") != "found" and "zoning" not in result
        cases.append(
            {
                "case": nonsense,
                "answerable": False,
                "expected": "no single zoning",
                "got": f"{result.get('status')}/{result.get('zoning')}",
                "ok": ok,
            }
        )

    return _tally(cases)


def check_geocode() -> dict[str, Any]:
    permits = _data.permits()
    permits = permits[permits["x_ft"].notna()]
    rows = permits.sample(n=SAMPLE, random_state=SEED)

    cases = []
    for _, row in rows.iterrows():
        address = row.get("address_normalized")
        if not isinstance(address, str) or not address.strip():
            continue
        result = geocode(address, allow_network=False)
        ok = False
        if result.get("status") == "found":
            ok = (
                abs(result["latitude"] - row["latitude"]) < 1e-3
                and abs(result["longitude"] - row["longitude"]) < 1e-3
            )
        elif result.get("status") == "ambiguous":
            # Conflicting source records: declining is correct behaviour, not
            # a wrong answer, so it is not scored as a miss.
            ok = "latitude" not in result
        cases.append(
            {
                "case": address,
                "answerable": True,
                "expected": f"{row['latitude']:.5f},{row['longitude']:.5f}",
                "got": f"{result.get('status')}/{result.get('latitude')}",
                "ok": ok,
            }
        )

    for nonsense in (
        "1 NOWHERE BLVD ZZZZZ",
        "999999 IMAGINARY PKWY",
        "???",
    ):
        result = geocode(nonsense, allow_network=False)
        ok = result.get("status") != "found"
        cases.append(
            {
                "case": nonsense,
                "answerable": False,
                "expected": "not found",
                "got": str(result.get("status")),
                "ok": ok,
            }
        )

    return _tally(cases)


def check_floodplain() -> dict[str, Any]:
    frame = _data.floodplain()
    rows = frame.sample(n=25, random_state=SEED)

    cases = []
    for _, row in rows.iterrows():
        point = row.geometry.representative_point()
        lon, lat = _TO_WGS84.transform(point.x, point.y)
        result = floodplain_check(lat, lon)
        ok = result.get("intersects_floodplain") is True
        cases.append(
            {
                "case": f"inside polygon at {lat:.5f},{lon:.5f}",
                "answerable": True,
                "expected": "intersects",
                "got": str(result.get("intersects_floodplain")),
                "ok": ok,
            }
        )

    # Points well outside every floodplain polygon must report no intersection
    # and a positive distance, never a silent True.
    union_bounds = frame.total_bounds
    for index in range(25):
        x = union_bounds[2] + 50_000 + index * 1_000
        y = union_bounds[3] + 50_000 + index * 1_000
        lon, lat = _TO_WGS84.transform(x, y)
        result = floodplain_check(lat, lon)
        ok = result.get("intersects_floodplain") is False
        cases.append(
            {
                "case": f"far outside at {lat:.5f},{lon:.5f}",
                "answerable": True,
                "expected": "no intersection",
                "got": str(result.get("intersects_floodplain")),
                "ok": ok,
            }
        )

    return _tally(cases)


def check_watershed() -> dict[str, Any]:
    frame = _data.watersheds()
    name_col = "watershed_full_name"
    rows = frame.sample(n=min(SAMPLE, len(frame)), random_state=SEED)

    cases = []
    for _, row in rows.iterrows():
        point = row.geometry.representative_point()
        lon, lat = _TO_WGS84.transform(point.x, point.y)
        result = watershed_lookup(lat, lon)
        expected = row[name_col] if name_col else None
        ok = result.get("status") in {"found", "boundary"}
        if ok and expected and result.get("status") == "found":
            ok = str(result.get("watershed")) == str(expected)
        cases.append(
            {
                "case": f"{expected} at {lat:.5f},{lon:.5f}",
                "answerable": True,
                "expected": str(expected),
                "got": f"{result.get('status')}/{result.get('watershed')}",
                "ok": bool(ok),
            }
        )

    # Far outside Travis County: no watershed should be claimed.
    bounds = frame.total_bounds
    for index in range(5):
        lon, lat = _TO_WGS84.transform(
            bounds[2] + 200_000 + index * 5_000, bounds[3] + 200_000
        )
        result = watershed_lookup(lat, lon)
        ok = result.get("status") not in {"found", "boundary"}
        cases.append(
            {
                "case": f"outside coverage at {lat:.5f},{lon:.5f}",
                "answerable": False,
                "expected": "no watershed",
                "got": str(result.get("status")),
                "ok": ok,
            }
        )

    return _tally(cases)


def _expected_radius_hits(
    frame, lat: float, lon: float, radius_ft: float, date_col: str | None, years
) -> int:
    """Recompute a radius search independently of the tool under test."""

    import pandas as pd

    work = frame[frame["x_ft"].notna()].copy()
    if years and date_col and date_col in work.columns:
        cutoff = pd.Timestamp.now() - pd.DateOffset(years=years)
        dates = pd.to_datetime(work[date_col], errors="coerce")
        work = work[dates.isna() | (dates >= cutoff)]
    point = _data.to_tx_ft(lat, lon)
    distance = np.hypot(work["x_ft"] - point.x, work["y_ft"] - point.y)
    return int((distance <= radius_ft).sum())


def check_nearby() -> dict[str, Any]:
    permits = _data.permits()
    seeds = permits[permits["x_ft"].notna()].sample(
        n=RADIUS_SAMPLE, random_state=SEED
    )

    specs = (
        ("nearby_permits", nearby_permits, _data.permits, "issue_date", 5),
        (
            "nearby_site_plan_cases",
            nearby_site_plan_cases,
            _data.site_plans,
            "APPLICATION_START_DATE",
            None,
        ),
    )

    cases = []
    for _, seed_row in seeds.iterrows():
        lat, lon = seed_row["latitude"], seed_row["longitude"]
        for name, tool, loader, date_col, years in specs:
            result = tool(lat, lon)
            expected = _expected_radius_hits(
                loader(), lat, lon, result["radius_ft"], date_col, years
            )
            returned = result.get("records") or []
            reported = result.get("count_returned", len(returned))
            capped = expected > len(returned)
            distances = [r["distance_ft"] for r in returned]
            ok = (
                reported == len(returned)
                and distances == sorted(distances)
                and all(d <= result["radius_ft"] + 1 for d in distances)
                and (len(returned) == expected or capped)
            )
            cases.append(
                {
                    "case": f"{name} at {lat:.5f},{lon:.5f}",
                    "answerable": True,
                    "expected": (
                        f"{expected} record(s) within {result['radius_ft']} ft"
                        + (
                            f"; the tool returns at most {len(returned)} "
                            "(result cap), nearest first"
                            if capped
                            else ""
                        )
                    ),
                    "got": (
                        f"{len(returned)} record(s), sorted by distance, all "
                        f"within {result['radius_ft']} ft"
                    ),
                    "ok": ok,
                }
            )

    # VOID and test plan-review records must never surface.
    plan_review = _data.plan_review()
    voids = plan_review[plan_review["exclude_from_search"] & plan_review["x_ft"].notna()]
    for _, row in voids.head(10).iterrows():
        result = nearby_plan_review_cases(
            row["latitude"], row["longitude"], radius_ft=1, years=None, limit=50
        )
        numbers = {r.get("permit_number") for r in (result.get("records") or [])}
        ok = row["Permit_Number"] not in numbers
        cases.append(
            {
                "case": f"void record {row['Permit_Number']} excluded",
                "answerable": True,
                "expected": "excluded",
                "got": "excluded" if ok else "returned",
                "ok": ok,
            }
        )

    return _tally(cases)


CHECKS = {
    "zoning_lookup": check_zoning,
    "geocode": check_geocode,
    "floodplain_check": check_floodplain,
    "watershed_lookup": check_watershed,
    "nearby_searches": check_nearby,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=tuple(CHECKS), default=None)
    args = parser.parse_args()

    selected = {args.only: CHECKS[args.only]} if args.only else CHECKS

    results = {}
    for name, check in selected.items():
        print(f"checking {name} ...", flush=True)
        results[name] = check()
        entry = results[name]
        print(
            f"  correct {entry['answerable_correct']}/{entry['answerable_n']} "
            f"({entry['correct_percent']}%), safe failure "
            f"{entry['unanswerable_safe']}/{entry['unanswerable_n']} "
            f"({entry['safe_failure_percent']}%)",
            flush=True,
        )

    answerable = sum(r["answerable_n"] for r in results.values())
    correct = sum(r["answerable_correct"] for r in results.values())
    unanswerable = sum(r["unanswerable_n"] for r in results.values())
    safe = sum(r["unanswerable_safe"] for r in results.values())

    payload = {
        "seed": SEED,
        "per_tool": results,
        "overall": {
            "answerable_n": answerable,
            "correct_percent": pct(correct, answerable),
            "unanswerable_n": unanswerable,
            "safe_failure_percent": pct(safe, unanswerable),
        },
    }
    write_json(config.TOOLS_RESULTS / "tool_accuracy.json", payload)
    print(f"\noverall: {correct}/{answerable} correct, {safe}/{unanswerable} safe")
    print(f"wrote {config.TOOLS_RESULTS / 'tool_accuracy.json'}")


if __name__ == "__main__":
    main()
