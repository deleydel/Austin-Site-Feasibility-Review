"""Report completeness, export integrity and cross-section consistency.

Completeness and export run against every cached scenario state. Consistency
is checked deterministically first - facts that must agree between sections
are compared directly - and only then handed to the judge for conflicts that
cannot be expressed as a rule.

Run:  python -m evaluation.report.run_report_checks
      python -m evaluation.report.run_report_checks --no-judge
"""

from __future__ import annotations

import argparse
from typing import Any

from evaluation.common import pct, read_json, write_json
from evaluation.judge import get_judge, prompts
from src import config
from src.guardrails.claims import FINDING_LABELS
from src.report.export import export_report
from src.report.schema import REQUIRED_SECTIONS, build_report_document

EXPORT_FORMATS = ("md", "html", "docx", "pdf")

_HEADING_ONLY = {"heading"}

# Sections whose emptiness is a correct answer, not an incomplete report: a
# site with no constraints should carry an empty constraints list, and a fully
# resolved site has nothing outstanding to verify. These must be present and
# are reported when empty, but emptiness is not scored as a defect.
MAY_BE_EMPTY = {
    "potential_constraints",
    "missing_information_and_verification",
}


def check_completeness(document: dict[str, Any]) -> dict[str, Any]:
    sections = document.get("sections") or {}
    missing = [name for name in REQUIRED_SECTIONS if name not in sections]
    empty = []
    for name in REQUIRED_SECTIONS:
        body = sections.get(name)
        if not isinstance(body, dict):
            continue
        payload = {k: v for k, v in body.items() if k not in _HEADING_ONLY}
        if not any(v not in (None, "", [], {}) for v in payload.values()):
            empty.append(name)

    unexpectedly_empty = [name for name in empty if name not in MAY_BE_EMPTY]
    return {
        "required": len(REQUIRED_SECTIONS),
        "present": len(REQUIRED_SECTIONS) - len(missing),
        "missing": missing,
        "empty": empty,
        "unexpectedly_empty": unexpectedly_empty,
        "complete": not missing and not unexpectedly_empty,
    }


def check_exports(final_report: dict[str, Any], scenario_id: str) -> dict[str, Any]:
    """Every advertised format must produce a non-trivial file."""

    outcomes = {}
    out_dir = config.REPORT_CHECK_RESULTS / "exports"
    for fmt in EXPORT_FORMATS:
        path = out_dir / f"{scenario_id}.{fmt}"
        try:
            written = export_report(final_report, path)
            size = written.stat().st_size
            outcomes[fmt] = {"ok": size > 500, "bytes": size}
        except Exception as exc:  # noqa: BLE001 - the failure is the result
            outcomes[fmt] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return outcomes


def check_label_vocabulary(final_report: dict[str, Any]) -> dict[str, Any]:
    labels = [
        str(f.get("label"))
        for f in (final_report.get("findings") or [])
        if isinstance(f, dict)
    ]
    invalid = sorted({label for label in labels if label not in FINDING_LABELS})
    return {"labels_used": sorted(set(labels)), "invalid": invalid, "ok": not invalid}


def check_deterministic_consistency(
    state: dict[str, Any], final_report: dict[str, Any]
) -> list[dict[str, str]]:
    """Facts that must agree across the report, compared directly."""

    conflicts: list[dict[str, str]] = []
    site_context = state.get("site_context") or {}
    summary = final_report.get("site_summary") or {}
    findings = final_report.get("findings") or []
    labels = {
        f.get("category"): f.get("label") for f in findings if isinstance(f, dict)
    }

    tool_flood = (site_context.get("floodplain") or {}).get("intersects_floodplain")
    if summary.get("floodplain_intersection") != tool_flood:
        conflicts.append(
            {
                "sections": "site_summary vs floodplain tool result",
                "detail": (
                    f"summary reports {summary.get('floodplain_intersection')!r} "
                    f"but the tool returned {tool_flood!r}"
                ),
            }
        )

    if tool_flood is True and labels.get("drainage_flood") != "potential constraint":
        conflicts.append(
            {
                "sections": "floodplain tool result vs findings",
                "detail": (
                    "site intersects the floodplain but the drainage finding is "
                    f"labelled {labels.get('drainage_flood')!r}"
                ),
            }
        )

    constraints = final_report.get("potential_constraints") or []
    declared = [
        f for f in findings
        if isinstance(f, dict) and f.get("label") == "potential constraint"
    ]
    if len(declared) != len(constraints):
        conflicts.append(
            {
                "sections": "findings vs potential_constraints",
                "detail": (
                    f"{len(declared)} finding(s) labelled a potential constraint "
                    f"but the constraints list holds {len(constraints)}"
                ),
            }
        )

    zoning_status = (site_context.get("zoning") or {}).get("status")
    if zoning_status != "found" and summary.get("reported_zoning"):
        conflicts.append(
            {
                "sections": "zoning tool result vs site_summary",
                "detail": (
                    f"zoning lookup status is {zoning_status!r} yet the summary "
                    f"states zoning {summary.get('reported_zoning')!r}"
                ),
            }
        )

    return conflicts


def _section_text(document: dict[str, Any]) -> dict[str, str]:
    import json

    sections = document.get("sections") or {}
    return {
        name: json.dumps(sections.get(name, {}), default=str)[:2000]
        for name in (
            "project_and_site",
            "zoning_and_land_use",
            "drainage_flood_environmental",
            "potential_constraints",
            "missing_information_and_verification",
        )
        if name in sections
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="with_llm")
    parser.add_argument("--no-judge", action="store_true")
    args = parser.parse_args()

    state_dir = config.SCENARIO_STATES / args.mode
    files = sorted(state_dir.glob("*.json"))
    if not files:
        raise SystemExit(f"no cached states in {state_dir}; run the scenarios first")

    judge = None
    if not args.no_judge:
        judge = get_judge()
        judge.require()

    per_scenario = {}
    for path in files:
        state = read_json(path)
        final_report = state.get("final_report") or {}
        document = state.get("report_document") or build_report_document(final_report)

        completeness = check_completeness(document)
        exports = check_exports(final_report, path.stem)
        labels = check_label_vocabulary(final_report)
        rule_conflicts = check_deterministic_consistency(state, final_report)

        judged_conflicts: list[dict] = []
        judge_assessed = False
        if judge is not None:
            call = prompts.report_consistency(_section_text(document))
            verdict = judge.ask_or_default(
                call.system, call.user, call.default, call.required_keys, call.task
            )
            judge_assessed = not verdict.get("judge_failed")
            # A conflict with no stated detail is not a finding, it is noise.
            judged_conflicts = [
                c
                for c in (verdict.get("contradictions") or [])
                if isinstance(c, dict) and str(c.get("detail") or "").strip()
            ]

        per_scenario[path.stem] = {
            "completeness": completeness,
            "exports": exports,
            "finding_labels": labels,
            "rule_based_conflicts": rule_conflicts,
            "judged_conflicts": judged_conflicts,
            "judge_assessed": judge_assessed,
            "consistent": not rule_conflicts,
        }
        print(
            f"{path.stem}: sections {completeness['present']}/{completeness['required']}"
            f", exports {sum(1 for e in exports.values() if e['ok'])}/{len(exports)}"
            f", rule conflicts {len(rule_conflicts)}"
            f", judged conflicts {len(judged_conflicts)}",
            flush=True,
        )

    n = len(per_scenario)
    complete = sum(1 for s in per_scenario.values() if s["completeness"]["complete"])
    consistent = sum(1 for s in per_scenario.values() if s["consistent"])
    export_ok = sum(
        1
        for s in per_scenario.values()
        if all(e["ok"] for e in s["exports"].values())
    )

    payload = {
        "mode": args.mode,
        "scenarios": n,
        "overall": {
            "complete_reports": complete,
            "completeness_percent": pct(complete, n),
            "consistent_reports": consistent,
            "consistency_percent": pct(consistent, n),
            "all_formats_exported": export_ok,
            "export_percent": pct(export_ok, n),
        },
        "per_scenario": per_scenario,
    }
    write_json(config.REPORT_CHECK_RESULTS / "report_checks.json", payload)
    print(f"\n{payload['overall']}")
    print(f"wrote {config.REPORT_CHECK_RESULTS / 'report_checks.json'}")


if __name__ == "__main__":
    main()
