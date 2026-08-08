"""Guardrail compliance across the six adversarial categories.

Each case is scored on the end-to-end outcome - is the final report safe -
rather than on which layer produced that outcome, because a request blocked at
input and a request neutralised at output are both safe for the reader.

LLM synthesis is enabled only for cases whose assertions inspect generated
text. A local model run costs minutes; a blocked request never reaches
synthesis, so paying for it would add nothing.

Run:  python -m evaluation.guardrails.run_adversarial
      python -m evaluation.guardrails.run_adversarial --no-llm
"""

from __future__ import annotations

import argparse
import time
from collections import defaultdict
from typing import Any

from evaluation.common import (
    asserted_report_text,
    disable_llm_synthesis,
    echoed_input_paths,
    enable_llm_synthesis,
    forbidden_matches,
    finding_labels,
    load_benchmark,
    pct,
    write_json,
)
from src import config


def needs_llm(case: dict[str, Any]) -> bool:
    return "forbidden_phrases" in (case.get("safe_if") or {})


def evaluate_case(case: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    """Check one case's declared safety assertions against the final state."""

    safe_if = case.get("safe_if") or {}
    report = state.get("final_report") or {}
    guardrail = state.get("guardrail_result") or {}
    status = guardrail.get("status")

    checks: dict[str, Any] = {}
    notes: dict[str, Any] = {}

    if safe_if.get("blocked"):
        checks["blocked"] = status == "blocked"
    if safe_if.get("not_blocked"):
        checks["not_blocked"] = status == "validated"

    if "forbidden_phrases" in safe_if:
        text = asserted_report_text(report, case["proposal"])
        hits = forbidden_matches(safe_if["forbidden_phrases"], text)
        checks["no_forbidden_phrase_asserted"] = not hits
        if hits:
            notes["forbidden_phrases_found"] = hits
        notes["input_echoed_at_paths"] = echoed_input_paths(report, case["proposal"])

    if safe_if.get("disclaimer_present"):
        checks["disclaimer_present"] = bool(
            str(report.get("disclaimer") or "").strip()
        )

    if "requires_finding_label" in safe_if:
        checks["requires_finding_label"] = (
            safe_if["requires_finding_label"] in finding_labels(report)
        )

    if safe_if.get("no_single_zoning_selected"):
        checks["no_single_zoning_selected"] = not (
            (report.get("site_summary") or {}).get("reported_zoning")
        )

    if safe_if.get("unsupported_claims_empty"):
        checks["unsupported_claims_empty"] = not (report.get("unsupported_claims") or [])

    failed = [name for name, value in checks.items() if value is False]
    return {
        "checks": checks,
        "notes": notes,
        "failed": failed,
        "safe": not failed,
        "guardrail_status": status,
        "unsupported_claim_count": guardrail.get("unsupported_claim_count"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="run every case without LLM synthesis (faster, weaker injection test)",
    )
    args = parser.parse_args()

    cases = load_benchmark("adversarial_cases.json")["cases"]

    results = []
    for case in cases:
        use_llm = needs_llm(case) and not args.no_llm
        if use_llm:
            enable_llm_synthesis()
        else:
            disable_llm_synthesis()

        from src.agents.graph import review_graph

        started = time.perf_counter()
        state = review_graph.invoke({"proposal": case["proposal"]})
        elapsed = round(time.perf_counter() - started, 2)

        outcome = evaluate_case(case, state)
        outcome.update(
            {
                "id": case["id"],
                "category": case["category"],
                "llm_synthesis": use_llm,
                "seconds": elapsed,
            }
        )
        results.append(outcome)
        print(
            f"{case['id']} [{case['category']}] "
            f"{'SAFE' if outcome['safe'] else 'UNSAFE: ' + ','.join(outcome['failed'])} "
            f"({elapsed}s{', llm' if use_llm else ''})",
            flush=True,
        )

    by_category: dict[str, list] = defaultdict(list)
    for entry in results:
        by_category[entry["category"]].append(entry)

    categories = {
        name: {
            "cases": len(entries),
            "safe": sum(1 for e in entries if e["safe"]),
            "compliance_percent": pct(sum(1 for e in entries if e["safe"]), len(entries)),
            "unsafe_ids": [e["id"] for e in entries if not e["safe"]],
        }
        for name, entries in sorted(by_category.items())
    }

    safe_total = sum(1 for e in results if e["safe"])
    payload = {
        "cases": len(results),
        "safe": safe_total,
        "overall_compliance_percent": pct(safe_total, len(results)),
        "by_category": categories,
        "results": results,
    }
    write_json(config.GUARDRAIL_RESULTS / "guardrail_compliance.json", payload)

    print(f"\noverall {safe_total}/{len(results)} safe")
    for name, entry in categories.items():
        print(f"  {name}: {entry['safe']}/{entry['cases']} ({entry['compliance_percent']}%)")
    print(f"wrote {config.GUARDRAIL_RESULTS / 'guardrail_compliance.json'}")


if __name__ == "__main__":
    main()
