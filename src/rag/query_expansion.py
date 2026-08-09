"""Lay-language query expansion for regulatory retrieval.

Users describe projects conversationally ("can I take down this big old
tree?"), while the corpus speaks code vocabulary ("protected tree removal
permit"). The Task 7 held-out benchmark showed Hit@5 falling from 0.947 to
0.474 when questions were rephrased in lay language — almost entirely a
vocabulary mismatch.

This module maps common lay phrasings to the regulatory terms Austin's LDC,
DCM, and TCM actually use. The glossary is written as broad domain coverage
(zoning, site plan, environment, drainage, transportation, utilities), not as
answers to any benchmark's questions. Matching is regex on the lowercased
query; every matched entry contributes terms to an expanded query variant that
is retrieved alongside the original and rank-fused.
"""
from __future__ import annotations

import re

# (pattern, regulatory terms). Patterns fire on the lowercased query.
_G: list[tuple[str, str]] = [
    # --- zoning, lots, buildings -----------------------------------------
    (r"\b(granny flat|garage apartment|backyard (cottage|home|house)|in.?law (suite|unit|apartment)|casita)\b",
     "accessory dwelling unit secondary apartment"),
    (r"\b(split|divide|cut up)\b.{0,20}\b(lot|land|property|parcel)\b",
     "subdivision resubdivision minimum lot size"),
    (r"\b(smaller|shrink|reduce|undersized?)\b.{0,20}\blot\b|\blot\b.{0,20}\b(smaller|too small)\b",
     "minimum lot size reduction substandard lot exception"),
    (r"\bhow (tall|high)\b|\b(taller|height of (my|the) building)\b",
     "building height limit"),
    (r"\b(close|near|distance) to (the )?(property line|street|neighbou?r)|\bfrom the (property line|street edge)\b",
     "setback front yard side yard rear yard"),
    (r"\b(two|2) (units|homes|houses) on (one|a|the same) lot\b|\bduplex\b",
     "duplex use two-family residential"),
    (r"\bapartments?\b|\bcondo(minium)?s?\b|\b(housing|residential) complex\b|\bmulti.?unit\b",
     "multi-family residential"),
    (r"\b(concrete|paved?|pavement|hard surface|patio|hardscape)\b",
     "impervious cover"),
    (r"\bhow much of (my|the) (lot|land|yard) can (i|be) (cover|build)\b",
     "building coverage impervious cover"),
    # --- site plan and process --------------------------------------------
    (r"\b(go.?ahead|sign.?off|green.?light|approved plans?)\b",
     "site plan approval release"),
    (r"\b(valid|run out|expires?|how long do i have|more time|extension)\b",
     "expiration extension"),
    (r"\b(small|minor|tiny) (project|job|build|work)\b|\bexempt\b",
     "site plan exemption"),
    (r"\bpay (something|a fee|money) instead\b|\bfees? instead\b|\bin lieu\b",
     "fee in lieu"),
    (r"\b(give( up)?|donate|set aside|hand over)\b.{0,20}\b(land|strip|property|acreage)\b",
     "dedication easement"),
    (r"\bparks?\b|\bplayground\b|\bgreen space\b",
     "parkland dedication"),
    # --- trees and environment --------------------------------------------
    (r"\btrees?\b",
     "protected tree heritage tree removal permit"),
    (r"\b(boggy|marshy?|swampy?|bog|wet ground|soggy|standing water)\b",
     "wetland critical environmental feature"),
    (r"\b(creek|stream|waterway|river bank)\b",
     "waterway critical water quality zone buffer"),
    (r"\b(spring|cave|sinkhole|karst|bluff|canyon)\b",
     "critical environmental feature"),
    (r"\b(steep|slope|hillside|grade of the land)\b",
     "slope protection gradient"),
    (r"\b(dig( out)?|excavat\w*|build up the ground|fill dirt|regrade|earthwork|level (the|my) (lot|land|site))\b",
     "cut and fill grading depth"),
    (r"\b(erosion|wash(ing|ed)? away|soil loss)\b",
     "erosion hazard sedimentation control"),
    (r"\bflood(s|ing|ed)?\b|\bflood ?(zone|risk|area)\b",
     "floodplain"),
    (r"\b(rain|storm ?water|runoff|drainage)\b",
     "stormwater runoff drainage"),
    (r"\bponds?\b|\bhold (the )?(rain|water|runoff)\b",
     "detention pond stormwater management"),
    # --- transportation ----------------------------------------------------
    (r"\b(parking (spot|space|place)s?|car parking|park (my|their) cars?|how (many|much) parking)\b",
     "off-street parking requirement"),
    (r"\b(trucks?|deliver(y|ies)|unload(ing)?|loading (dock|area|zone))\b",
     "off-street loading facility"),
    (r"\b(entrance|entry|exit|access|way in|pull in|curb cut)s?\b.{0,25}\b(street|road|property|site|lot)\b",
     "driveway approach access street frontage"),
    (r"\bdriveways?\b",
     "driveway approach access"),
    (r"\btraffic (study|analysis|report)\b|\bhow much traffic\b",
     "traffic impact analysis"),
    (r"\b(cut(ting)? down|reduc\w+|fewer|less)\b.{0,20}\b(car|auto|vehicle|driving|trips?|commut\w+)\b|\bcarpool\b|\btransit incentive\b",
     "transportation demand management trip reduction"),
    (r"\bbike (rack|parking|storage)s?\b|\bbicycles?\b",
     "bicycle parking"),
    (r"\b(sidewalks?|foot ?paths?|walkways?)\b",
     "sidewalk installation"),
    # --- utilities ---------------------------------------------------------
    (r"\b(hook(ed)? ?up|connect\w*|tap(ping)? in(to)?)\b.{0,30}\b(water|sewer|utility|utilities|city service)\b"
     r"|\b(water|sewer) (line|main|service)\b",
     "water wastewater service extension utility connection"),
    (r"\b(sewage|sewer|septic|wastewater) (paperwork|report|documents?|forms?)\b",
     "wastewater report"),
    (r"\bseptic\b",
     "wastewater on-site sewage facility"),
]

_GLOSSARY = [(re.compile(p), terms) for p, terms in _G]


def expansion_terms(query: str) -> list[str]:
    """Regulatory terms matched by lay phrasings in the query, deduplicated."""
    q = query.lower()
    seen: dict[str, None] = {}
    for pattern, terms in _GLOSSARY:
        if pattern.search(q):
            for t in terms.split():
                seen.setdefault(t, None)
    return list(seen)


def expand_query(query: str) -> list[str]:
    """Query variants to retrieve and rank-fuse.

    Always returns the original first; adds one expanded variant when the
    glossary matched (original wording + regulatory vocabulary), so exact
    phrasings keep their rank signal and lay phrasings gain the corpus's own
    terms.
    """
    terms = expansion_terms(query)
    if not terms:
        return [query]
    return [query, f"{query} ({' '.join(terms)})"]
