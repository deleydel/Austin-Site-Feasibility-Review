"""Scope validation: Austin preliminary land-development review only."""

from __future__ import annotations

import re

# Out-of-scope location cues (non-Austin / non-Texas cities and states).
_OTHER_CITY_RE = re.compile(
    r"\b("
    r"houston|dallas|san\s*antonio|fort\s*worth|el\s*paso|seattle|portland|"
    r"denver|chicago|new\s*york|los\s*angeles|phoenix|miami|atlanta|"
    r"boston|philadelphia|san\s*francisco|san\s*diego|nashville"
    r")\b",
    re.I,
)
_OTHER_STATE_RE = re.compile(
    r"\b("
    r"california|florida|new\s*york|illinois|arizona|colorado|oregon|"
    r"washington|georgia|nevada|oklahoma|louisiana|new\s*mexico"
    r")\b",
    re.I,
)
_AUSTIN_RE = re.compile(r"\baustin\b", re.I)
_TEXAS_RE = re.compile(r"\b(tx|texas)\b", re.I)

# Requests that ask the system to act as an approval authority.
_UNSUPPORTED_REQUEST_RE = re.compile(
    r"\b("
    r"approve\s+(this|my|the)\s+(project|permit|site\s*plan|development)|"
    r"issue\s+(a\s+)?(permit|approval|variance)|"
    r"guarantee\s+(compliance|approval|feasibility)|"
    r"official\s+zoning\s+determination|"
    r"certify\s+compliance|"
    r"is\s+this\s+(fully\s+)?compliant\??"
    r")\b",
    re.I,
)


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

    other_city = _OTHER_CITY_RE.search(address) or _OTHER_CITY_RE.search(
        description
    )
    other_state = _OTHER_STATE_RE.search(address) or _OTHER_STATE_RE.search(
        description
    )
    mentions_austin = bool(_AUSTIN_RE.search(combined))
    mentions_texas = bool(_TEXAS_RE.search(combined))

    if other_city and not mentions_austin:
        return {
            "ok": False,
            "reason": (
                "Out-of-scope location: only City of Austin, Texas sites "
                "are supported for preliminary review."
            ),
            "warnings": warnings,
            "unsupported_request": False,
        }

    if other_state and not mentions_texas and not mentions_austin:
        return {
            "ok": False,
            "reason": (
                "Out-of-scope location: only Austin, Texas sites are supported."
            ),
            "warnings": warnings,
            "unsupported_request": False,
        }

    if not mentions_austin and not mentions_texas:
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
