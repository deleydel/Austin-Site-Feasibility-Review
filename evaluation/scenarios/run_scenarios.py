"""Run the benchmark site scenarios through the full review graph.

Produces the shared inputs the rest of the Task 7 suite reads:

* a cached final state per scenario per mode, so no other metric has to re-run
  the graph (a run with local LLM synthesis takes minutes);
* end-to-end response time with a per-node breakdown;
* agent task completion against each scenario's declared expectations.

Run:  python -m evaluation.scenarios.run_scenarios
      python -m evaluation.scenarios.run_scenarios --mode without_llm
"""

from __future__ import annotations

import argparse
import time
from typing import Any

from evaluation.common import (
    asserted_report_text,
    disable_llm_synthesis,
    echoed_input_paths,
    enable_llm_synthesis,
    finding_labels,
    forbidden_matches,
    jsonable,
    load_benchmark,
    read_json,
    write_json,
)
from src import config

MODES = ("with_llm", "without_llm")

REVIEW_KEYS = (
    "zoning_site_plan",
    "drainage_environmental",
    "transportation_access",
    "water_wastewater",
    "historical_context",
)


def run_graph(proposal: dict[str, Any]) -> tuple[dict[str, Any], list[dict], float]:
    """Invoke the graph, returning (final_state, node_timings, total_seconds).

    Streamed as updates so each node can be timed. AgentState declares no
    reducers, so merging the updates in order reproduces the final state.
    """

    from src.agents.graph import review_graph

    state: dict[str, Any] = {"proposal": proposal}
    timings: list[dict] = []
    started = time.perf_counter()
    last = started
    for chunk in review_graph.stream({"proposal": proposal}, stream_mode="updates"):
        now = time.perf_counter()
        for node, update in chunk.items():
            if isinstance(update, dict):
                state.update(update)
            timings.append({"node": node, "seconds": round(now - last, 3)})
        last = now
    return state, timings, round(time.perf_counter() - started, 3)


def check_completion(state: dict[str, Any], expect: dict[str, Any]) -> dict[str, Any]:
    """Score one scenario against its declared expectations."""

    checks: dict[str, Any] = {}
    report = state.get("final_report") or {}
    site = state.get("site_context") or {}
    guardrail = state.get("guardrail_result") or {}

    if "input_valid" in expect:
        checks["input_valid"] = state.get("input_valid") is expect["input_valid"]

    if "guardrail_status" in expect:
        checks["guardrail_status"] = (
            guardrail.get("status") == expect["guardrail_status"]
        )

    if "zoning_status" in expect:
        checks["zoning_status"] = (
            (site.get("zoning") or {}).get("status") == expect["zoning_status"]
        )

    if "geocode_status" in expect:
        checks["geocode_status"] = (
            (site.get("geocode") or {}).get("status") == expect["geocode_status"]
        )

    if "floodplain_intersects" in expect:
        checks["floodplain_intersects"] = (
            (site.get("floodplain") or {}).get("intersects_floodplain")
            is expect["floodplain_intersects"]
        )

    if "reviews_present" in expect:
        present = set((state.get("reviews") or {}).keys())
        checks["reviews_present"] = set(expect["reviews_present"]).issubset(present)

    if "finding_labels_allowed" in expect:
        allowed = set(expect["finding_labels_allowed"])
        labels = finding_labels(report)
        checks["finding_labels_allowed"] = bool(labels) and all(
            label in allowed for label in labels
        )

    if "requires_finding_label" in expect:
        checks["requires_finding_label"] = (
            expect["requires_finding_label"] in finding_labels(report)
        )

    if expect.get("no_single_zoning_selected"):
        checks["no_single_zoning_selected"] = not (
            (report.get("site_summary") or {}).get("reported_zoning")
        )

    if expect.get("disclaimer_present"):
        checks["disclaimer_present"] = bool(str(report.get("disclaimer") or "").strip())

    if "forbidden_phrases" in expect:
        text = asserted_report_text(report, state.get("proposal") or {})
        hits = forbidden_matches(expect["forbidden_phrases"], text)
        checks["forbidden_phrases_absent"] = not hits
        if hits:
            checks["forbidden_phrases_found"] = hits
        # Recorded, not scored: quoting the applicant's own words back is not
        # the system asserting them, but injected instruction text still
        # reaches the exported document.
        checks["input_echoed_at_paths"] = echoed_input_paths(
            report, state.get("proposal") or {}
        )

    # Task completion is independent of the per-scenario expectations: every
    # applicable review category ran and the workflow reached report building.
    trace = state.get("execution_trace") or []
    if state.get("input_valid"):
        checks["all_review_nodes_completed"] = set(REVIEW_KEYS).issubset(
            set((state.get("reviews") or {}).keys())
        )
    checks["reached_report_build"] = "build_report: completed" in trace

    return checks


def rescore_mode(mode: str, scenarios: list[dict]) -> dict[str, Any]:
    """Re-apply the expectations to already-cached states.

    Scoring rules change more often than the runs do, and a with_llm run costs
    most of an hour, so a scoring fix must not require re-invoking the graph.
    """

    previous = {}
    existing = config.SCENARIO_RESULTS / "scenario_results.json"
    if existing.exists():
        for entry in (read_json(existing).get("modes") or {}).get(mode, {}).get(
            "scenarios", []
        ):
            previous[entry["id"]] = entry

    results = []
    for scenario in scenarios:
        path = config.SCENARIO_STATES / mode / f"{scenario['id']}.json"
        if not path.exists():
            continue
        state = read_json(path)
        checks = check_completion(state, scenario.get("expect", {}))
        failed = [k for k, v in checks.items() if v is False]
        prior = previous.get(scenario["id"], {})
        results.append(
            {
                "id": scenario["id"],
                "label": scenario["label"],
                "total_seconds": prior.get("total_seconds", 0.0),
                "node_seconds": prior.get("node_seconds", []),
                "checks": checks,
                "failed_checks": failed,
                "passed": not failed,
            }
        )
        print(
            f"[{mode}] {scenario['id']}: rescored "
            f"{'PASS' if not failed else 'FAIL ' + ','.join(failed)}",
            flush=True,
        )
    return {"mode": mode, "scenarios": results}


def run_mode(mode: str, scenarios: list[dict]) -> dict[str, Any]:
    if mode == "with_llm":
        enable_llm_synthesis()
    else:
        disable_llm_synthesis()

    results = []
    for scenario in scenarios:
        print(f"[{mode}] {scenario['id']} ...", flush=True)
        state, timings, total = run_graph(scenario["proposal"])
        checks = check_completion(state, scenario.get("expect", {}))
        failed = [k for k, v in checks.items() if v is False]

        write_json(config.SCENARIO_STATES / mode / f"{scenario['id']}.json", state)

        results.append(
            {
                "id": scenario["id"],
                "label": scenario["label"],
                "total_seconds": total,
                "node_seconds": timings,
                "checks": checks,
                "failed_checks": failed,
                "passed": not failed,
            }
        )
        print(
            f"[{mode}] {scenario['id']}: {total}s, "
            f"{'PASS' if not failed else 'FAIL ' + ','.join(failed)}",
            flush=True,
        )
    return {"mode": mode, "scenarios": results}


def summarize_timing(by_mode: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for mode, payload in by_mode.items():
        totals = sorted(s["total_seconds"] for s in payload["scenarios"])
        if not totals:
            continue
        node_totals: dict[str, float] = {}
        for scenario in payload["scenarios"]:
            for entry in scenario["node_seconds"]:
                node_totals[entry["node"]] = (
                    node_totals.get(entry["node"], 0.0) + entry["seconds"]
                )
        n = len(totals)
        summary[mode] = {
            "n": n,
            "median_seconds": totals[n // 2],
            "min_seconds": totals[0],
            "max_seconds": totals[-1],
            "mean_seconds_per_node": {
                node: round(total / n, 3)
                for node, total in sorted(
                    node_totals.items(), key=lambda kv: -kv[1]
                )
            },
        }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=(*MODES, "both"), default="both")
    parser.add_argument(
        "--rescore",
        action="store_true",
        help="re-apply expectations to cached states without re-running the graph",
    )
    args = parser.parse_args()

    scenarios = load_benchmark("site_scenarios.json")["scenarios"]
    modes = MODES if args.mode == "both" else (args.mode,)

    # Merge with any previous run so the two modes can be measured separately;
    # the with_llm mode costs most of an hour and must not be lost by a later
    # without_llm run.
    by_mode: dict[str, Any] = {}
    existing = config.SCENARIO_RESULTS / "scenario_results.json"
    if existing.exists():
        by_mode.update(read_json(existing).get("modes") or {})

    for mode in modes:
        by_mode[mode] = (
            rescore_mode(mode, scenarios)
            if args.rescore
            else run_mode(mode, scenarios)
        )

    passed = sum(
        1 for m in by_mode.values() for s in m["scenarios"] if s["passed"]
    )
    total = sum(len(m["scenarios"]) for m in by_mode.values())

    payload = {
        "modes": jsonable(by_mode),
        "task_completion": {
            "scenarios_passed": passed,
            "scenarios_run": total,
        },
        "timing": summarize_timing(by_mode),
    }
    write_json(config.SCENARIO_RESULTS / "scenario_results.json", payload)
    write_json(
        config.SCENARIO_RESULTS / "end_to_end_timing.json", payload["timing"]
    )
    print(f"\n{passed}/{total} scenario runs passed all checks")
    print(f"wrote {config.SCENARIO_RESULTS / 'scenario_results.json'}")


if __name__ == "__main__":
    main()
