"""Groundedness, unsupported-claim rate and citation correctness.

Reads the cached scenario states produced by
``evaluation.scenarios.run_scenarios`` (with_llm mode), so the graph is not
re-run per metric.

Definitions used, stated because they are choices:

* Groundedness - share of extracted claims supported by the evidence the
  agent actually retrieved (``state['evidence']``).
* Unsupported-claim rate - share of claims no retrieved evidence supports.
* Citation correctness - share of claims whose closest cited section, resolved
  from the section index and read in full, supports them. Claims with no
  topically related citation are reported as uncited rather than counted wrong.

Run:  python -m evaluation.grounding.run_grounding
"""

from __future__ import annotations

import argparse
import re
from typing import Any

from evaluation.common import pct, read_json, write_json
from evaluation.grounding.citation_support import (
    best_citation_for,
    verify_claim_support,
)
from evaluation.judge import get_judge, prompts
from evaluation.judge.enforce import enforce_support_verdict, term_overlap
from src import config

# Judge at most this many evidence passages per claim, chosen by content-term
# overlap. A local model costs seconds per call, so spending them on the
# passages that could plausibly support the claim is the difference between a
# suite that runs and one that does not.
EVIDENCE_CANDIDATES = 2
SUPPORTED = {"supported", "partially_supported"}


# Imperative openers that mark an action item rather than an assertion about
# the site or the code. The extraction rubric already asks the model to leave
# recommendations out; it does not reliably comply, and counting "Obtain the
# necessary permits" as an ungrounded claim would understate groundedness by
# filling the denominator with sentences no evidence could ever support.
_RECOMMENDATION_OPENERS = {
    "apply", "assess", "check", "complete", "conduct", "confirm", "consider",
    "consult", "contact", "coordinate", "determine", "develop", "engage",
    "ensure", "evaluate", "hire", "monitor", "obtain", "perform", "prepare",
    "provide", "retain", "review", "seek", "submit", "verify",
}


# Statements that assert nothing checkable: the report saying it does not know
# something. No evidence can support or refute "the traffic impact is unknown",
# so scoring them produces noise in both directions - in a first run one such
# sentence was called supported and another unsupported.
_UNCERTAINTY_RE = re.compile(
    r"\b(is|are|was|were|remains?) (currently )?"
    r"(unknown|unclear|undetermined|not known|not available|not specified|"
    r"not confirmed|to be determined)\b"
    r"|\bno information (is )?available\b"
    r"|\b(cannot|could not) be (determined|confirmed|established)\b",
    re.I,
)


def looks_like_recommendation(claim: str) -> bool:
    """True when a claim is really a next step for the applicant."""

    words = re.sub(r"^[\s*#\-\d.)]+", "", claim).split()
    return bool(words) and words[0].strip(":,").lower() in _RECOMMENDATION_OPENERS


def states_uncertainty(claim: str) -> bool:
    """True when a claim only reports that something is not known."""

    return bool(_UNCERTAINTY_RE.search(claim))


def site_evidence(state: dict[str, Any]) -> list[dict[str, Any]]:
    """The structured tool output, as a passage claims can be checked against.

    Site facts - zoning, floodplain, watershed, nearby records - come from the
    deterministic tools, not from the regulatory corpus. Judging "the site is
    zoned SF-3-NP" against Land Development Code passages guarantees a false
    unsupported verdict, so the tool output belongs in the evidence pool.
    """

    context = state.get("site_context") or {}
    if not context:
        return []

    parts: list[str] = []
    zoning = context.get("zoning") or {}
    if zoning.get("zoning"):
        parts.append(f"Reported zoning is {zoning['zoning']}.")
    for designation in zoning.get("zoning_designations") or []:
        parts.append(f"Reported zoning designation {designation}.")
    if zoning.get("base_zone"):
        parts.append(f"Base zone is {zoning['base_zone']}.")
    parts.append(f"Zoning lookup status is {zoning.get('status')}.")

    floodplain = context.get("floodplain") or {}
    if "intersects_floodplain" in floodplain:
        verb = "intersects" if floodplain["intersects_floodplain"] else "does not intersect"
        parts.append(f"The site {verb} the floodplain.")
    for zone in floodplain.get("flood_zones") or []:
        if isinstance(zone, dict) and zone.get("flood_zone"):
            parts.append(f"Flood zone: {zone['flood_zone']}.")
    if floodplain.get("nearest_floodplain_distance_ft") is not None:
        parts.append(
            "Distance to the nearest floodplain is "
            f"{floodplain['nearest_floodplain_distance_ft']} feet."
        )

    watershed = context.get("watershed") or {}
    if watershed.get("watershed"):
        parts.append(f"The site is in the {watershed['watershed']} watershed.")

    geocode = context.get("geocode") or {}
    parts.append(f"Geocode status is {geocode.get('status')}.")

    for key, label in (
        ("nearby_permits", "nearby issued permits"),
        ("nearby_site_plans", "nearby site plan cases"),
        ("nearby_plan_reviews", "nearby plan review cases"),
    ):
        entry = context.get(key) or {}
        if entry.get("count_returned") is not None:
            parts.append(f"There are {entry['count_returned']} {label}.")

    return [
        {
            "doc_id": "SITE",
            "section_number": "structured tool output",
            "text": " ".join(parts),
        }
    ]


def extract_claims(text: str, judge) -> tuple[list[str], dict[str, list[str]], bool]:
    """Return (checkable claims, excluded claims by reason, judge_failed)."""

    call = prompts.claim_extraction(text)
    verdict = judge.ask_or_default(
        call.system, call.user, call.default, call.required_keys, call.task
    )
    extracted = [
        " ".join(str(c).split())
        for c in (verdict.get("claims") or [])
        if str(c).strip()
    ]

    claims: list[str] = []
    excluded: dict[str, list[str]] = {"recommendation": [], "uncertainty": []}
    for claim in extracted:
        if looks_like_recommendation(claim):
            excluded["recommendation"].append(claim)
        elif states_uncertainty(claim):
            excluded["uncertainty"].append(claim)
        else:
            claims.append(claim)
    return claims, excluded, bool(verdict.get("judge_failed"))


def ground_claim(claim: str, evidence: list[dict], judge) -> dict[str, Any]:
    """Best support verdict for a claim across the available evidence.

    The site-data passage is always a candidate rather than competing for a
    slot on term overlap. It is two sentences long while regulatory passages
    run to thousands of characters, so a long passage sharing generic words
    ("watershed", "drainage", "requirements") outranks the short passage that
    actually names Shoal Creek, and the site fact is never checked against the
    tool output that produced it.
    """

    site = [p for p in evidence if p.get("doc_id") == "SITE"]
    regulatory = [p for p in evidence if p.get("doc_id") != "SITE"]
    ranked = site + sorted(
        regulatory,
        key=lambda p: term_overlap(claim, str(p.get("text") or "")),
        reverse=True,
    )[:EVIDENCE_CANDIDATES]

    best = {
        "verdict": "unsupported",
        "reason": "no retrieved evidence was topically related to the claim",
        "enforced": True,
    }
    for passage in ranked:
        body = str(passage.get("text") or "")
        if not body.strip():
            continue
        label = f"{passage.get('doc_id')} {passage.get('section_number')}"
        call = prompts.claim_support(claim, body, label)
        raw = judge.ask_or_default(
            call.system, call.user, call.default, call.required_keys, call.task
        )
        verdict = enforce_support_verdict(raw, claim, body)
        verdict["evidence"] = label
        if verdict["verdict"] == "supported":
            return verdict
        if verdict["verdict"] == "partially_supported":
            best = verdict
        elif best.get("verdict") == "unsupported":
            best = verdict
    return best


def score_scenario(state: dict[str, Any], judge, retriever) -> dict[str, Any]:
    report = state.get("final_report") or {}
    synthesis = str(report.get("llm_synthesis") or "").strip()
    if not synthesis:
        return {"measurable": False, "reason": "no LLM synthesis in this state"}

    claims, excluded, extraction_failed = extract_claims(synthesis, judge)
    if not claims:
        return {
            "measurable": False,
            "reason": (
                "claim extraction produced no checkable claims"
                + (" (judge failure)" if extraction_failed else "")
            ),
            "excluded": {k: len(v) for k, v in excluded.items()},
        }

    # Regulatory passages plus the structured tool output: a site fact is
    # grounded in the tools, a regulatory statement in the corpus.
    evidence = list(state.get("evidence") or []) + site_evidence(state)
    citations = report.get("citations") or []

    rows = []
    for claim in claims:
        grounding = ground_claim(claim, evidence, judge)
        citation = best_citation_for(claim, citations)
        if citation is None:
            citation_result = {
                "verdict": "uncited",
                "reason": "no cited section was topically related to the claim",
            }
        else:
            citation_result = verify_claim_support(claim, citation, judge, retriever)
        rows.append(
            {
                "claim": claim,
                "grounding_verdict": grounding["verdict"],
                "grounding_evidence": grounding.get("evidence"),
                "grounding_reason": grounding.get("reason"),
                "grounding_enforced": bool(grounding.get("enforced")),
                "citation": citation_result.get("citation"),
                "citation_verdict": citation_result["verdict"],
                "citation_reason": citation_result.get("reason"),
            }
        )
        print(
            f"    claim: {grounding['verdict']:>20s} | "
            f"citation: {citation_result['verdict']:>20s} | {claim[:60]}",
            flush=True,
        )

    total = len(rows)
    grounded = sum(1 for r in rows if r["grounding_verdict"] in SUPPORTED)
    unsupported = sum(1 for r in rows if r["grounding_verdict"] == "unsupported")
    cited = [r for r in rows if r["citation_verdict"] != "uncited"]
    citation_ok = sum(1 for r in cited if r["citation_verdict"] in SUPPORTED)

    return {
        "measurable": True,
        "claims": total,
        "excluded": {k: len(v) for k, v in excluded.items()},
        "grounded_in_site_data": sum(
            1 for r in rows if r.get("grounding_evidence", "").startswith("SITE")
        ),
        "grounded": grounded,
        "groundedness_percent": pct(grounded, total),
        "unsupported": unsupported,
        "unsupported_claim_rate_percent": pct(unsupported, total),
        "claims_with_citation": len(cited),
        "claims_uncited": total - len(cited),
        "citations_supporting": citation_ok,
        "citation_correctness_percent": pct(citation_ok, len(cited)),
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="with_llm")
    args = parser.parse_args()

    state_dir = config.SCENARIO_STATES / args.mode
    files = sorted(state_dir.glob("*.json"))
    if not files:
        raise SystemExit(
            f"no cached states in {state_dir}. Run "
            "'python -m evaluation.scenarios.run_scenarios --mode with_llm' first."
        )

    judge = get_judge()
    judge.require()
    from src.rag.retriever import get_retriever

    retriever = get_retriever()

    per_scenario = {}
    for path in files:
        print(f"scoring {path.stem} ...", flush=True)
        per_scenario[path.stem] = score_scenario(read_json(path), judge, retriever)

    measured = [s for s in per_scenario.values() if s.get("measurable")]
    claims = sum(s["claims"] for s in measured)
    grounded = sum(s["grounded"] for s in measured)
    unsupported = sum(s["unsupported"] for s in measured)
    cited = sum(s["claims_with_citation"] for s in measured)
    citation_ok = sum(s["citations_supporting"] for s in measured)

    payload = {
        "mode": args.mode,
        "scenarios_scored": len(measured),
        "scenarios_skipped": len(per_scenario) - len(measured),
        "overall": {
            "claims": claims,
            "excluded_recommendations": sum(
                (s.get("excluded") or {}).get("recommendation", 0)
                for s in per_scenario.values()
            ),
            "excluded_uncertainty_statements": sum(
                (s.get("excluded") or {}).get("uncertainty", 0)
                for s in per_scenario.values()
            ),
            "grounded_in_site_data": sum(
                s.get("grounded_in_site_data", 0) for s in measured
            ),
            "groundedness_percent": pct(grounded, claims),
            "unsupported_claim_rate_percent": pct(unsupported, claims),
            "claims_with_citation": cited,
            "claims_uncited": claims - cited,
            "citation_correctness_percent": pct(citation_ok, cited),
        },
        "per_scenario": per_scenario,
        "judge_calls": getattr(judge, "calls", None),
        "judge_failures": getattr(judge, "failures", None),
    }
    write_json(config.GROUNDING_RESULTS / "grounding.json", payload)
    print("\n" + str(payload["overall"]))
    print(f"wrote {config.GROUNDING_RESULTS / 'grounding.json'}")


if __name__ == "__main__":
    main()
