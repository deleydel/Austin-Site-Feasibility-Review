"""Address normalization shared by preprocessing (Task 1) and lookup tools (Task 3).

Canonical form matches the Zoning_By_Address FULL_STREET_NAME convention:
uppercase, single spaces, USPS-style abbreviated suffix (ST, AVE, DR, ...),
directionals as N/S/E/W, fractional numbers kept ("6008 1/2 CERVINUS RUN").
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict

import usaddress

# USPS street-suffix canonicalization (common Austin variants).
SUFFIX_MAP = {
    "STREET": "ST", "STR": "ST", "ST": "ST",
    "AVENUE": "AVE", "AV": "AVE", "AVE": "AVE",
    "BOULEVARD": "BLVD", "BLVD": "BLVD", "BOUL": "BLVD",
    "DRIVE": "DR", "DR": "DR", "DRV": "DR",
    "LANE": "LN", "LN": "LN",
    "ROAD": "RD", "RD": "RD",
    "COURT": "CT", "CT": "CT",
    "CIRCLE": "CIR", "CIR": "CIR", "CRCLE": "CIR",
    "COVE": "CV", "CV": "CV",
    "PLACE": "PL", "PL": "PL",
    "TRAIL": "TRL", "TRL": "TRL", "TR": "TRL",
    "PARKWAY": "PKWY", "PKWY": "PKWY", "PKY": "PKWY",
    "HIGHWAY": "HWY", "HWY": "HWY",
    "EXPRESSWAY": "EXPY", "EXPY": "EXPY", "EXPWY": "EXPY",
    "TERRACE": "TER", "TER": "TER",
    "PATH": "PATH", "PASS": "PASS", "RUN": "RUN", "ROW": "ROW",
    "WAY": "WAY", "WALK": "WALK", "BEND": "BND", "BND": "BND",
    "LOOP": "LOOP", "PLAZA": "PLZ", "PLZ": "PLZ",
    "SQUARE": "SQ", "SQ": "SQ", "POINT": "PT", "PT": "PT",
    "RIDGE": "RDG", "RDG": "RDG", "CROSSING": "XING", "XING": "XING",
    "HOLLOW": "HOLW", "HOLW": "HOLW", "VIEW": "VW", "VW": "VW",
    "TRACE": "TRCE", "TRCE": "TRCE",
}

DIRECTIONAL_MAP = {
    "NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W",
    "N": "N", "S": "S", "E": "E", "W": "W",
    "NORTHEAST": "NE", "NORTHWEST": "NW", "SOUTHEAST": "SE", "SOUTHWEST": "SW",
    "NE": "NE", "NW": "NW", "SE": "SE", "SW": "SW",
}


@dataclass
class NormalizedAddress:
    raw: str
    normalized: str            # canonical full string used for matching
    street_number: str | None  # "6008" or "6008 1/2"
    predirectional: str | None
    street_name: str | None
    suffix: str | None
    postdirectional: str | None
    unit: str | None
    parse_method: str          # "usaddress" | "regex_fallback"

    def to_dict(self) -> dict:
        return asdict(self)


def _clean_token(tok: str) -> str:
    return re.sub(r"[^\w/]", "", tok).upper()


def _basic_clean(raw: str) -> str:
    s = raw.upper().strip()
    s = re.sub(r"[.,#]", " ", s)
    s = re.sub(r"\s+", " ", s)
    # "6008 1/2" and "60081/2" both -> "6008 1/2"
    s = re.sub(r"(\d)\s*1/2", r"\1 1/2", s)
    return s.strip()


def normalize_address(raw: str) -> NormalizedAddress:
    """Parse and canonicalize a raw address string.

    Never raises on messy input: falls back to a regex split when usaddress
    cannot tag the string.
    """
    cleaned = _basic_clean(raw or "")
    number = predir = name = suffix = postdir = unit = None
    method = "usaddress"

    try:
        tagged, _ = usaddress.tag(cleaned)
    except usaddress.RepeatedLabelError:
        tagged = None

    if tagged:
        number = tagged.get("AddressNumber")
        if tagged.get("AddressNumberSuffix"):
            number = f"{number} {_clean_token(tagged['AddressNumberSuffix'])}".strip()
        predir = tagged.get("StreetNamePreDirectional")
        name = tagged.get("StreetName")
        suffix = tagged.get("StreetNamePostType")
        postdir = tagged.get("StreetNamePostDirectional")
        unit = tagged.get("OccupancyIdentifier")
        # usaddress sometimes folds pre-type into the name (e.g. "RANCH ROAD 620")
        if tagged.get("StreetNamePreType"):
            name = f"{tagged['StreetNamePreType']} {name or ''}".strip()
    else:
        method = "regex_fallback"
        m = re.match(r"^(\d+(?:\s1/2)?)\s+(.*)$", cleaned)
        if m:
            number, rest = m.group(1), m.group(2)
        else:
            rest = cleaned
        tokens = rest.split()
        if tokens and tokens[0] in DIRECTIONAL_MAP and len(tokens) > 1:
            predir, tokens = DIRECTIONAL_MAP[tokens[0]], tokens[1:]
        if tokens and _clean_token(tokens[-1]) in SUFFIX_MAP and len(tokens) > 1:
            suffix, tokens = tokens[-1], tokens[:-1]
        name = " ".join(tokens) if tokens else None

    predir = DIRECTIONAL_MAP.get(_clean_token(predir)) if predir else None
    postdir = DIRECTIONAL_MAP.get(_clean_token(postdir)) if postdir else None
    if suffix:
        suffix = SUFFIX_MAP.get(_clean_token(suffix), _clean_token(suffix))
    if name:
        name = re.sub(r"\s+", " ", name.upper()).strip()
    if number:
        number = number.upper().strip()

    parts = [p for p in (number, predir, name, suffix, postdir) if p]
    normalized = " ".join(parts)
    return NormalizedAddress(
        raw=raw, normalized=normalized, street_number=number, predirectional=predir,
        street_name=name, suffix=suffix, postdirectional=postdir, unit=unit,
        parse_method=method,
    )
