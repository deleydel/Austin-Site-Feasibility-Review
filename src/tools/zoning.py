"""Task 3: zoning lookup by address.

Match policy (per review):
- Exact normalized match -> found (or multiple_records when the address has
  more than one distinct zoning designation — all are returned, none chosen).
- High-confidence textual match with the SAME street number -> fuzzy_match
  with an explicit warning.
- Different street number is NEVER returned as the subject property's zoning:
  those become ambiguous candidates for user confirmation.
- Zoning is always preliminary Open Data; official verification is required.
"""
from __future__ import annotations

from rapidfuzz import fuzz

from src.tools import _data
from src.tools.address import normalize_address

FUZZY_MIN_SCORE = 92.0
CANDIDATE_MIN_SCORE = 80.0
DISCLAIMER = ("Preliminary reported zoning from Austin Open Data; not an "
              "official zoning determination. Official verification required.")


def _records(rows) -> list[dict]:
    return [
        {
            "address": r.FULL_STREET_NAME,
            "zoning": r.ZONING_ZTYPE,
            "base_zone": r.BASE_ZONE,
            "base_zone_category": r.BASE_ZONE_CATEGORY,
        }
        for r in rows.itertuples()
    ]


def zoning_lookup(address: str) -> dict:
    df = _data.zoning()
    norm = normalize_address(address)
    out = {
        "query_address": address,
        "normalized_address": norm.normalized,
        "verification_required": True,
        "disclaimer": DISCLAIMER,
    }
    if not norm.normalized:
        return {**out, "status": "not_found",
                "detail": "Address could not be parsed."}

    exact = df[df["address_normalized"] == norm.normalized]
    if len(exact):
        designations = sorted(exact["ZONING_ZTYPE"].dropna().unique())
        if len(designations) > 1:
            return {**out, "status": "multiple_records",
                    "zoning_designations": designations,
                    "records": _records(exact),
                    "detail": "Address has multiple distinct zoning "
                              "designations; none was auto-selected."}
        return {**out, "status": "found", "match_type": "exact",
                "zoning": designations[0],
                "base_zone": exact.iloc[0]["BASE_ZONE"],
                "base_zone_category": exact.iloc[0]["BASE_ZONE_CATEGORY"],
                "records": _records(exact)}

    # Same street number required for any fuzzy result.
    if norm.street_number:
        same_no = df[df["street_number"] == norm.street_number]
        if len(same_no):
            scores = same_no["address_normalized"].map(
                lambda a: fuzz.ratio(a, norm.normalized))
            best = scores.max()
            hits = same_no[scores >= FUZZY_MIN_SCORE]
            designations = sorted(hits["ZONING_ZTYPE"].dropna().unique())
            if len(hits) and len(designations) == 1:
                top = hits.loc[scores[hits.index].idxmax()]
                return {**out, "status": "fuzzy_match",
                        "match_type": "same_street_number_textual",
                        "match_score": float(scores[hits.index].max()),
                        "matched_address": top["FULL_STREET_NAME"],
                        "zoning": top["ZONING_ZTYPE"],
                        "base_zone": top["BASE_ZONE"],
                        "base_zone_category": top["BASE_ZONE_CATEGORY"],
                        "warning": "Matched by textual similarity "
                                   f"({scores[hits.index].max():.0f}/100) to a record with the "
                                   "same street number, not an exact address "
                                   "match. Confirm the address."}
            if len(hits) and len(designations) > 1:
                return {**out, "status": "multiple_records",
                        "zoning_designations": designations,
                        "records": _records(hits),
                        "detail": "Multiple similar records with the same "
                                  "street number disagree on zoning."}

    # Candidates only — a neighbor's zoning is never returned as the answer.
    street_only = " ".join(p for p in (norm.predirectional, norm.street_name,
                                       norm.suffix) if p)
    cand = df
    if street_only:
        scores = df["address_normalized"].map(
            lambda a: fuzz.partial_ratio(street_only, a))
        cand = df[scores >= CANDIDATE_MIN_SCORE]
    if len(cand) == 0:
        return {**out, "status": "not_found",
                "detail": "No matching or similar address in the zoning dataset."}
    cand = cand.head(1000)
    sim = cand["address_normalized"].map(lambda a: fuzz.ratio(a, norm.normalized))
    top = cand.assign(_s=sim).sort_values("_s", ascending=False).head(5)
    return {**out, "status": "ambiguous",
            "candidates": _records(top),
            "detail": "No exact or same-street-number match. Candidate "
                      "addresses returned for user confirmation; their zoning "
                      "was NOT assigned to the subject property."}
