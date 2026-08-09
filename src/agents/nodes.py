"""Workflow nodes for the Task 4 LangGraph agent."""

from src.tools.nearby import (
    nearby_permits,
    nearby_plan_review_cases,
    nearby_site_plan_cases,
)
from src.agents.state import AgentState
from src.guardrails.scope import validate_scope
from src.tools.geocode import geocode
from src.tools.spatial import floodplain_check, watershed_lookup
from src.tools.zoning import zoning_lookup
from src.rag.retriever import get_retriever


def validate_input(state: AgentState) -> dict:
    """Validate required fields and Austin preliminary-review scope."""

    proposal = state.get("proposal", {})

    address = str(proposal.get("address", "")).strip()
    proposed_land_use = str(proposal.get("proposed_land_use", "")).strip()

    missing = []

    if not address:
        missing.append("address")

    if not proposed_land_use:
        missing.append("proposed_land_use")

    if missing:
        return {
            "input_valid": False,
            "stop_reason": "Missing required input: " + ", ".join(missing),
            "missing_information": missing,
            "execution_trace": ["validate_input: failed"],
        }

    scope = validate_scope(proposal)
    if not scope.get("ok"):
        return {
            "input_valid": False,
            "stop_reason": scope.get("reason")
            or "Request is outside supported preliminary-review scope.",
            "missing_information": [],
            "warnings": list(scope.get("warnings") or []),
            "execution_trace": ["validate_input: failed_scope"],
        }

    return {
        "input_valid": True,
        "stop_reason": None,
        "missing_information": [],
        "warnings": list(scope.get("warnings") or []),
        "reviews": {},
        "evidence": [],
        "citations": [],
        "execution_trace": ["validate_input: passed"],
    }


def collect_site_context(state: AgentState) -> dict:
    """Collect preliminary zoning, coordinates, floodplain, and watershed data."""

    proposal = state.get("proposal", {})

    address = proposal["address"]
    manual_lat = proposal.get("latitude")
    manual_lon = proposal.get("longitude")

    zoning_result = zoning_lookup(address)

    geocode_result = geocode(
        address,
        manual_lat=manual_lat,
        manual_lon=manual_lon,
    )

    site_context = {
        "zoning": zoning_result,
        "geocode": geocode_result,
    }

    if geocode_result.get("status") == "found":
        lat = geocode_result["latitude"]
        lon = geocode_result["longitude"]

        site_context["floodplain"] = floodplain_check(lat, lon)
        site_context["watershed"] = watershed_lookup(lat, lon)
        site_context["nearby_permits"] = nearby_permits(lat, lon)
        site_context["nearby_site_plans"] = nearby_site_plan_cases(lat, lon)
        site_context["nearby_plan_reviews"] = nearby_plan_review_cases(lat, lon)

    else:
        site_context["floodplain"] = {
            "status": "not_run",
            "detail": "Floodplain check requires confirmed coordinates.",
        }

        site_context["watershed"] = {
            "status": "not_run",
            "detail": "Watershed lookup requires confirmed coordinates.",
        }

    warnings = list(state.get("warnings", []))

    if zoning_result.get("status") != "found":
        warnings.append(
            "Zoning could not be confirmed exactly and requires verification."
        )

    if geocode_result.get("status") != "found":
        warnings.append(
            "Site coordinates could not be confirmed and require verification."
        )

    return {
        "site_context": site_context,
        "warnings": warnings,
        "execution_trace": list(state.get("execution_trace", []))
        + ["collect_site_context: completed"],
    }

def detect_zoning_use_conflict(
    reported_zoning: str,
    proposed_land_use: str,
    units: int | None = None,
) -> dict:
    """Flag obvious zoning/use combinations that require verification."""

    zoning_upper = str(reported_zoning or "").upper()
    use_lower = str(proposed_land_use or "").lower()

    if zoning_upper.startswith("SF-3") and "multifamily" in use_lower:
        unit_text = (
            f" for the proposed {units}-unit development"
            if units is not None
            else ""
        )

        return {
            "potential_conflict": True,
            "conflict_detail": (
                f"Reported zoning is {reported_zoning}, while the proposed "
                f"land use is multifamily residential{unit_text}. "
                "This combination presents a potential zoning/use conflict "
                "that requires verification against the applicable Austin "
                "Land Development Code requirements. No approval or "
                "prohibition determination is made here."
            ),
        }

    return {
        "potential_conflict": False,
        "conflict_detail": None,
    }

def zoning_review(state: AgentState) -> dict:
    """Retrieve zoning and site-plan regulations relevant to the proposal."""

    proposal = state.get("proposal", {})
    site_context = state.get("site_context", {})

    proposed_land_use = proposal.get("proposed_land_use", "")
    description = proposal.get("development_description", "")

    zoning = site_context.get("zoning", {})
    reported_zoning = zoning.get("zoning", "unknown zoning")
    units = proposal.get("units")

    conflict = detect_zoning_use_conflict(
        reported_zoning,
        proposed_land_use,
        units,
    )

    query = (
        f"Austin development requirements for {proposed_land_use}. "
        f"Reported zoning is {reported_zoning}. "
        f"Development description: {description}. "
        "Identify applicable zoning, land use, and site plan requirements."
    )

    retriever = get_retriever()

    results = retriever.retrieve(
        query=query,
        k=5,
        doc_ids=["LDC"],
        chapters=[
    "Chapter 25-1",
    "Chapter 25-2",
    "Chapter 25-5",
],
    )

    review = {
    "query": query,
    "reported_zoning": reported_zoning,
    "potential_conflict": conflict["potential_conflict"],
    "conflict_detail": conflict["conflict_detail"],
    "retrieved_passages": results,
    }

    reviews = dict(state.get("reviews", {}))
    reviews["zoning_site_plan"] = review

    evidence = list(state.get("evidence", []))
    evidence.extend(results)

    return {
        "reviews": reviews,
        "evidence": evidence,
        "execution_trace": list(state.get("execution_trace", []))
        + ["zoning_review: completed"],
    }


def drainage_review(state: AgentState) -> dict:
    """Retrieve drainage, floodplain, and environmental regulations."""

    proposal = state.get("proposal", {})
    site_context = state.get("site_context", {})

    proposed_land_use = proposal.get("proposed_land_use", "")
    description = proposal.get("development_description", "")

    floodplain = site_context.get("floodplain", {})
    watershed = site_context.get("watershed", {})

    floodplain_status = floodplain.get(
        "intersects_floodplain",
        "unknown",
    )

    watershed_name = watershed.get(
        "watershed",
        "unknown watershed",
    )

    query = (
        f"Austin drainage and environmental requirements for "
        f"{proposed_land_use}. "
        f"Development description: {description}. "
        f"Floodplain intersection: {floodplain_status}. "
        f"Watershed: {watershed_name}. "
        "Identify applicable drainage, floodplain, watershed, "
        "water quality, and environmental requirements."
    )

    retriever = get_retriever()

    results = retriever.retrieve(
        query=query,
        k=5,
        doc_ids=["LDC", "DCM"],
        chapters=[
            "Chapter 25-7",
            "Chapter 25-8",
            "Section 1",
            "Section 2",
            "Section 8",
            "Appendix E",
        ],
    )

    review = {
        "query": query,
        "floodplain": floodplain,
        "watershed": watershed,
        "retrieved_passages": results,
    }

    reviews = dict(state.get("reviews", {}))
    reviews["drainage_environmental"] = review

    evidence = list(state.get("evidence", []))
    evidence.extend(results)

    return {
        "reviews": reviews,
        "evidence": evidence,
        "execution_trace": list(state.get("execution_trace", []))
        + ["drainage_review: completed"],
    }


def transportation_review(state: AgentState) -> dict:
    """Retrieve transportation and site-access regulations."""

    proposal = state.get("proposal", {})

    proposed_land_use = proposal.get("proposed_land_use", "")
    description = proposal.get("development_description", "")
    units = proposal.get("units")

    query = (
        f"Austin transportation and site access requirements for "
        f"{proposed_land_use}. "
        f"Development description: {description}. "
        f"Approximate units: {units if units is not None else 'unknown'}. "
        "Identify applicable transportation, driveway, access, "
        "parking, circulation, and traffic requirements."
    )

    retriever = get_retriever()

    results = retriever.retrieve(
        query=query,
        k=5,
        doc_ids=["LDC", "TCM"],
        chapters=[
            "Chapter 25-6",
            "Section 1",
            "Section 7",
            "Section 9",
            "Section 10",
        ],
    )

    review = {
        "query": query,
        "retrieved_passages": results,
    }

    reviews = dict(state.get("reviews", {}))
    reviews["transportation_access"] = review

    evidence = list(state.get("evidence", []))
    evidence.extend(results)

    return {
        "reviews": reviews,
        "evidence": evidence,
        "execution_trace": list(state.get("execution_trace", []))
        + ["transportation_review: completed"],
    }

def water_wastewater_review(state: AgentState) -> dict:
    """Retrieve general Austin water and wastewater requirements."""

    proposal = state.get("proposal", {})

    proposed_land_use = proposal.get("proposed_land_use", "")
    description = proposal.get("development_description", "")
    units = proposal.get("units")

    query = (
        f"Austin water and wastewater requirements for "
        f"{proposed_land_use}. "
        f"Development description: {description}. "
        f"Approximate units: {units if units is not None else 'unknown'}. "
        "Identify applicable general water, wastewater, utility connection, "
        "and infrastructure requirements. Do not assume service availability "
        "or utility capacity."
    )

    retriever = get_retriever()

    results = retriever.retrieve(
        query=query,
        k=5,
        doc_ids=["LDC"],
        chapters=[
            "Chapter 25-9",
        ],
    )

    review = {
        "query": query,
        "retrieved_passages": results,
        "note": (
            "Regulatory requirements do not establish actual water or "
            "wastewater service availability or capacity. Verification "
            "with the appropriate utility authority is required."
        ),
    }

    reviews = dict(state.get("reviews", {}))
    reviews["water_wastewater"] = review

    evidence = list(state.get("evidence", []))
    evidence.extend(results)

    return {
        "reviews": reviews,
        "evidence": evidence,
        "execution_trace": list(state.get("execution_trace", []))
        + ["water_wastewater_review: completed"],
    }


def historical_context_review(state: AgentState) -> dict:
    """Summarize nearby permit and case records as historical context."""

    site_context = state.get("site_context", {})

    permits = site_context.get("nearby_permits", {})
    site_plans = site_context.get("nearby_site_plans", {})
    plan_reviews = site_context.get("nearby_plan_reviews", {})

    review = {
        "nearby_permits": permits,
        "nearby_site_plans": site_plans,
        "nearby_plan_reviews": plan_reviews,
        "summary": {
            "permit_count": permits.get("count_returned", 0),
            "site_plan_count": site_plans.get("count_returned", 0),
            "plan_review_count": plan_reviews.get("count_returned", 0),
        },
        "note": (
            "Nearby permits and cases are historical context only. "
            "They are not approval precedent and do not indicate future "
            "permitting outcomes for the proposed development."
        ),
    }

    reviews = dict(state.get("reviews", {}))
    reviews["historical_context"] = review

    return {
        "reviews": reviews,
        "execution_trace": list(state.get("execution_trace", []))
        + ["historical_context_review: completed"],
    }