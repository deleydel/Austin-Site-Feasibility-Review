"""Scope validation: Austin preliminary land-development review only."""

from __future__ import annotations

import re

_AUSTIN_RE = re.compile(r"\baustin\b", re.I)
_TEXAS_RE = re.compile(r"\b(tx|texas)\b", re.I)

# Non-US / non-Texas location cues.
_FOREIGN_COUNTRY_RE = re.compile(
    r"\b("
    r"france|canada|mexico|uk|united\s*kingdom|england|scotland|ireland|"
    r"germany|spain|italy|japan|china|india|australia|brazil|argentina|"
    r"colombia|chile|peru|portugal|netherlands|belgium|sweden|norway|"
    r"denmark|finland|switzerland|austria|poland|greece|turkey|egypt|"
    r"south\s*africa|new\s*zealand|singapore|korea|philippines|thailand|"
    r"indonesia|malaysia|vietnam|israel|uae|saudi\s*arabia|russia|ukraine"
    r")\b",
    re.I,
)

_US_STATE_NAMES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
    "maine", "maryland", "massachusetts", "michigan", "minnesota",
    "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new hampshire", "new jersey", "new mexico", "new york",
    "north carolina", "north dakota", "ohio", "oklahoma", "oregon",
    "pennsylvania", "rhode island", "south carolina", "south dakota",
    "tennessee", "utah", "vermont", "virginia", "washington",
    "west virginia", "wisconsin", "wyoming", "district of columbia",
}

_US_STATE_ABBREV = {
    "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga", "hi", "id",
    "il", "in", "ia", "ks", "ky", "la", "me", "md", "ma", "mi", "mn", "ms",
    "mo", "mt", "ne", "nv", "nh", "nj", "nm", "ny", "nc", "nd", "oh", "ok",
    "or", "pa", "ri", "sc", "sd", "tn", "ut", "vt", "va", "wa", "wv", "wi",
    "wy", "dc",
}

# Requests that ask the system to act as an approval authority.
_UNSUPPORTED_REQUEST_RE = re.compile(
    r"\b("
    r"approve\s+(this|my|the)\s+(project|permit|site\s*plan|development)|"
    r"issue\s+(a\s+)?(permit|approval|variance)|"
    r"guarantee\s+(compliance|approval|feasibility)|"
    r"official\s+zoning\s+determination|"
    r"certify\s+compliance|"
    r"is\s+this\s+(fully\s+)?compliant\??|"
    r"tell\s+me\s+definitively\s+whether\s+this\s+complies|"
    r"yes\s+or\s+no\s+answer\s+only"
    r")\b",
    re.I,
)


def _parse_address_location(address: str) -> dict[str, str | None]:
    """Best-effort city / state / country parse from a comma-separated address."""

    parts = [p.strip() for p in str(address or "").split(",") if p.strip()]
    city = None
    state = None
    country = None

    if not parts:
        return {"city": None, "state": None, "country": None}

    last = parts[-1]
    last_lower = last.lower()

    if _FOREIGN_COUNTRY_RE.search(last):
        country = last
        if len(parts) >= 2:
            city = parts[-2]
        return {"city": city, "state": None, "country": country}

    # "City, TX" or "City, Texas"
    if re.fullmatch(r"(tx|texas)", last_lower):
        state = "TX"
        if len(parts) >= 2:
            city = parts[-2]
        return {"city": city, "state": state, "country": "USA"}

    # "City, CO" / "City, Colorado"
    if last_lower in _US_STATE_ABBREV and last_lower != "tx":
        state = last.upper()
        if len(parts) >= 2:
            city = parts[-2]
        return {"city": city, "state": state, "country": "USA"}

    if last_lower in _US_STATE_NAMES and last_lower != "texas":
        state = last
        if len(parts) >= 2:
            city = parts[-2]
        return {"city": city, "state": state, "country": "USA"}

    # "Paris, France" already handled; also "France" alone as last token with city.
    if len(parts) >= 2 and _FOREIGN_COUNTRY_RE.search(parts[-1]):
        return {
            "city": parts[-2],
            "state": None,
            "country": parts[-1],
        }

    # Fallback: second-to-last token often is the city when present.
    if len(parts) >= 2:
        maybe_city = parts[-2]
        maybe_state = parts[-1]
        if re.fullmatch(r"[A-Za-z .'-]+", maybe_city):
            city = maybe_city
        if _TEXAS_RE.search(maybe_state):
            state = "TX"
        elif maybe_state.lower() in _US_STATE_ABBREV | _US_STATE_NAMES:
            state = maybe_state

    return {"city": city, "state": state, "country": country}


def validate_scope(proposal: dict) -> dict:
    """Validate that the request is an in-scope Austin preliminary review.

    Returns:
        {
          "ok": bool,
          "reason": str | None,
          "warnings": list[str],
          "unsupported_request": bool,
        }
    """

    address = str(proposal.get("address", "")).strip()
    land_use = str(proposal.get("proposed_land_use", "")).strip()
    description = str(proposal.get("development_description", "")).strip()
    combined = " ".join([address, land_use, description])

    warnings: list[str] = []

    if not address or not land_use:
        return {
            "ok": False,
            "reason": "Missing required input for preliminary review scope.",
            "warnings": warnings,
            "unsupported_request": False,
        }

    if _UNSUPPORTED_REQUEST_RE.search(combined):
        return {
            "ok": False,
            "reason": (
                "Unsupported request: this system provides preliminary "
                "feasibility screening only and cannot issue approvals, "
                "permits, variances, or official compliance determinations."
            ),
            "warnings": warnings,
            "unsupported_request": True,
        }

    # Foreign countries are always out of scope.
    if _FOREIGN_COUNTRY_RE.search(combined):
        return {
            "ok": False,
            "reason": (
                "Out-of-scope location: only City of Austin, Texas sites "
                "are supported for preliminary review."
            ),
            "warnings": warnings,
            "unsupported_request": False,
        }

    location = _parse_address_location(address)
    city = (location.get("city") or "").strip()
    state = (location.get("state") or "").strip()
    mentions_austin = bool(_AUSTIN_RE.search(combined))
    city_is_austin = bool(city and _AUSTIN_RE.search(city))

    # Explicit non-Austin city in the address (e.g. Round Rock, Houston, Paris).
    if city and not city_is_austin:
        return {
            "ok": False,
            "reason": (
                "Out-of-scope location: only City of Austin, Texas sites "
                "are supported for preliminary review."
            ),
            "warnings": warnings,
            "unsupported_request": False,
        }

    # Non-Texas US state with no Austin mention.
    if state and state.upper() != "TX" and state.lower() != "texas":
        if not mentions_austin:
            return {
                "ok": False,
                "reason": (
                    "Out-of-scope location: only Austin, Texas sites are supported."
                ),
                "warnings": warnings,
                "unsupported_request": False,
            }

    # Description names another city even if address does not.
    desc_location = _parse_address_location(description)
    desc_city = (desc_location.get("city") or "").strip()
    if desc_city and not _AUSTIN_RE.search(desc_city) and not mentions_austin:
        # Only treat as city when description looks like a location phrase.
        if re.search(
            rf"\b(in|at|near|located\s+in)\s+{re.escape(desc_city)}\b",
            description,
            re.I,
        ):
            return {
                "ok": False,
                "reason": (
                    "Out-of-scope location: only City of Austin, Texas sites "
                    "are supported for preliminary review."
                ),
                "warnings": warnings,
                "unsupported_request": False,
            }

    if not mentions_austin and not _TEXAS_RE.search(combined):
        warnings.append(
            "Address does not explicitly mention Austin or Texas; "
            "proceeding as a preliminary Austin screening subject to "
            "geocode and zoning verification."
        )

    return {
        "ok": True,
        "reason": None,
        "warnings": warnings,
        "unsupported_request": False,
    }
