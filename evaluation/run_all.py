"""Run the Task 7 evaluation suite and assemble the scorecard.

Stages run in dependency order. A stage that fails is recorded and the run
continues, so one broken measurement never costs the rest of a suite that
takes hours of local model time.

Reads whatever results already exist when ``--collect-only`` is given, which
is how the scorecard is rebuilt after scoring the manual sheet.

Run:  python -m evaluation.run_all
      python -m evaluation.run_all --collect-only
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from typing import Any

from evaluation.common import read_json, write_json
from src import config

STAGES = [
    ("scenarios", ["evaluation.scenarios.run_scenarios"]),
    ("retrieval", ["evaluation.retrieval.run_task7_retrieval"]),
    ("tool_accuracy", ["evaluation.tools.run_accuracy"]),
    # evaluation.tools.run_latency is deliberately not a stage here: it is the
    # tools workstream's own benchmark and its committed results are their
    # evidence. Running it from this suite would overwrite their measurements
    # with numbers taken while the machine is loaded by the local judge.
    ("grounding", ["evaluation.grounding.run_grounding"]),
    ("guardrails", ["evaluation.guardrails.run_adversarial"]),
    ("report_checks", ["evaluation.report.run_report_checks"]),
    ("manual_sheet", ["evaluation.manual.build_sheet"]),
]


def run_stage(module_args: list[str]) -> dict[str, Any]:
    started = time.perf_counter()
    completed = subprocess.run(
        [sys.executable, "-m", *module_args],
        cwd=config.PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    return {
        "command": " ".join(["python", "-m", *module_args]),
        "returncode": completed.returncode,
        "ok": completed.returncode == 0,
        "seconds": round(time.perf_counter() - started, 1),
        "stderr_tail": completed.stderr.strip().splitlines()[-8:],
    }


def _load(path) -> Any:
    try:
        return read_json(path)
    except Exception:
        return None


def collect() -> dict[str, Any]:
    """Gather every metric family from the per-area result files."""

    retrieval = _load(config.RETRIEVAL_RESULTS / "retrieval_task7.json")
    accuracy = _load(config.TOOLS_RESULTS / "tool_accuracy.json")
    latency = _load(config.TOOLS_RESULTS / "tool_latency_ms.json")
    scenarios = _load(config.SCENARIO_RESULTS / "scenario_results.json")
    grounding = _load(config.GROUNDING_RESULTS / "grounding.json")
    guardrails = _load(config.GUARDRAIL_RESULTS / "guardrail_compliance.json")
    reports = _load(config.REPORT_CHECK_RESULTS / "report_checks.json")
    agreement = _load(config.MANUAL_REVIEW_DIR / "manual_agreement.json")

    metrics: dict[str, Any] = {}

    if retrieval:
        ranking = retrieval["ranking"]
        metrics["retrieval_hit_at_5"] = {
            "value": ranking["hit_at_5"],
            "n": retrieval["n_questions"],
            "detail": (
                f"Hit@1 {ranking['hit_at_1']}, Recall@5 {ranking['recall_at_5']}, "
                f"MRR {ranking['mrr']}"
            ),
        }
        sensitivity = retrieval.get("phrasing_sensitivity")
        if sensitivity:
            metrics["retrieval_hit_at_5_lay_phrasing"] = {
                "value": sensitivity["lay_worded"]["hit_at_5"],
                "n": sensitivity["n_questions"],
                "detail": (
                    "same questions asked in plain language; code-worded "
                    f"Hit@5 was {sensitivity['code_worded']['hit_at_5']}"
                ),
            }
        relevance = retrieval.get("relevance")
        if relevance:
            metrics["retrieval_relevance_precision_at_5"] = {
                "value": relevance["precision_at_5_percent"],
                "n": relevance["passages_judged"],
                "unit": "%",
                "detail": f"{relevance['judge_failures']} judge failures, counted not relevant",
            }

    if accuracy:
        overall = accuracy["overall"]
        metrics["structured_data_accuracy"] = {
            "value": overall["correct_percent"],
            "n": overall["answerable_n"],
            "unit": "%",
            "detail": "correct answers on cases that have a right answer",
        }
        metrics["structured_data_safe_failure"] = {
            "value": overall["safe_failure_percent"],
            "n": overall["unanswerable_n"],
            "unit": "%",
            "detail": "unanswerable cases declined instead of answered wrongly",
        }

    if scenarios:
        completion = scenarios["task_completion"]
        metrics["agent_task_completion"] = {
            "value": completion["scenarios_passed"],
            "n": completion["scenarios_run"],
            "detail": "scenario runs meeting every declared expectation",
        }
        timing = scenarios.get("timing") or {}
        for mode, entry in timing.items():
            metrics[f"end_to_end_seconds_{mode}"] = {
                "value": entry["median_seconds"],
                "n": entry["n"],
                "unit": "s (median)",
                "detail": f"min {entry['min_seconds']}s, max {entry['max_seconds']}s",
            }

    if grounding:
        overall = grounding["overall"]
        metrics["groundedness"] = {
            "value": overall["groundedness_percent"],
            "n": overall["claims"],
            "unit": "%",
            "detail": "claims supported by evidence the agent retrieved",
        }
        metrics["unsupported_claim_rate"] = {
            "value": overall["unsupported_claim_rate_percent"],
            "n": overall["claims"],
            "unit": "%",
        }
        metrics["citation_correctness"] = {
            "value": overall["citation_correctness_percent"],
            "n": overall["claims_with_citation"],
            "unit": "%",
            "detail": (
                f"{overall['claims_uncited']} further claims had no topically "
                "related citation and are excluded"
            ),
        }

    if guardrails:
        metrics["guardrail_compliance"] = {
            "value": guardrails["overall_compliance_percent"],
            "n": guardrails["cases"],
            "unit": "%",
            "detail": ", ".join(
                f"{name} {entry['safe']}/{entry['cases']}"
                for name, entry in guardrails["by_category"].items()
            ),
        }

    if reports:
        overall = reports["overall"]
        metrics["report_completeness"] = {
            "value": overall["completeness_percent"],
            "n": reports["scenarios"],
            "unit": "%",
        }
        metrics["report_consistency"] = {
            "value": overall["consistency_percent"],
            "n": reports["scenarios"],
            "unit": "%",
            "detail": "no rule-based cross-section conflict",
        }

    if latency:
        slowest = max(latency.items(), key=lambda kv: kv[1]["median_ms"])
        metrics["tool_latency_ms"] = {
            "value": slowest[1]["median_ms"],
            "n": len(latency),
            "unit": "ms (slowest tool median)",
            "detail": f"slowest is {slowest[0]}",
        }

    if agreement:
        metrics["judge_human_agreement"] = {
            "value": agreement["agreement_percent"],
            "n": agreement["items_scored"],
            "unit": "%",
            "detail": "hand-scored sample checking the local judge",
        }

    return {"metrics": metrics, "sources_present": {
        "retrieval": bool(retrieval),
        "tool_accuracy": bool(accuracy),
        "tool_latency": bool(latency),
        "scenarios": bool(scenarios),
        "grounding": bool(grounding),
        "guardrails": bool(guardrails),
        "report_checks": bool(reports),
        "manual_agreement": bool(agreement),
    }}


def render_scorecard(payload: dict[str, Any]) -> str:
    metrics = payload["metrics"]
    lines = [
        "# Task 7 Evaluation Scorecard",
        "",
        "Every figure below was produced by the scripts in `evaluation/`; "
        "nothing here is estimated. Sample sizes are small and stated, and the "
        "judge behind the text metrics is a local llama3.2, so read the "
        "caveats before quoting a number.",
        "",
        "| metric | value | n | notes |",
        "| --- | --- | ---: | --- |",
    ]
    for name, entry in metrics.items():
        value = entry.get("value")
        unit = entry.get("unit", "")
        shown = "not measured" if value is None else f"{value}{(' ' + unit) if unit else ''}"
        lines.append(
            f"| {name.replace('_', ' ')} | {shown} | {entry.get('n', '')} | "
            f"{entry.get('detail', '')} |"
        )

    missing = [k for k, v in payload["sources_present"].items() if not v]
    lines += [
        "",
        "## How to read this",
        "",
        "- **Retrieval** is scored on a held-out question set whose gold "
        "sections are disjoint from the set the retrieval workstream tuned "
        "against. The lay-phrasing row is the same questions in plain "
        "language and is the more realistic figure.",
        "- **Safe failure** matters as much as accuracy here: the system is "
        "required never to answer when it does not know.",
        "- **Groundedness and citation correctness** come from an LLM judge "
        "whose support verdicts are re-checked in code - a verdict is "
        "rejected unless the evidence really contains the claim's numbers and "
        "named identifiers. Every failure path resolves to unsupported.",
        "- **Guardrail compliance** scores the end-to-end outcome, so a "
        "request blocked at input and one neutralised at output both count "
        "as safe.",
    ]
    if missing:
        lines += [
            "",
            f"Not present in this run: {', '.join(missing)}.",
        ]
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--collect-only",
        action="store_true",
        help="rebuild the scorecard from existing results without re-running",
    )
    args = parser.parse_args()

    stage_results = {}
    if not args.collect_only:
        for name, module_args in STAGES:
            print(f"--- {name}", flush=True)
            outcome = run_stage(module_args)
            stage_results[name] = outcome
            status = "ok" if outcome["ok"] else f"FAILED ({outcome['returncode']})"
            print(f"    {status} in {outcome['seconds']}s", flush=True)
            if not outcome["ok"]:
                for line in outcome["stderr_tail"]:
                    print(f"    | {line}", flush=True)

    payload = collect()
    payload["stages"] = stage_results
    write_json(config.SUMMARY_RESULTS / "evaluation_results.json", payload)
    scorecard = config.SUMMARY_RESULTS / "EVALUATION.md"
    scorecard.parent.mkdir(parents=True, exist_ok=True)
    scorecard.write_text(render_scorecard(payload), encoding="utf-8")

    print(f"\nwrote {scorecard}")
    print(f"wrote {config.SUMMARY_RESULTS / 'evaluation_results.json'}")


if __name__ == "__main__":
    main()
