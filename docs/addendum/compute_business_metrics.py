#!/usr/bin/env python3
"""Compute Part-2 business metrics once manual timing / survey scores are known.

Examples:
  python docs/addendum/compute_business_metrics.py --manual-seconds 1200
  python docs/addendum/compute_business_metrics.py --manual-seconds 900 \\
      --trust 4.25 --usefulness 4.0
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

SYSTEM_MEDIAN_NO_LLM_S = 0.305
SYSTEM_MEDIAN_WITH_LLM_S = 2.738

# Completeness from fixed Madison checklist (see BUSINESS_EVALUATION.md)
COMPLETENESS = {
    "scenario": "1714 Madison Avenue — 40-unit multifamily",
    "items_total": 9,
    "identified": 7,
    "partial": 2,
    "missing": 0,
    "weighted_pct": round(100.0 * (7 + 0.5 * 2) / 9, 1),
    "strict_pct": round(100.0 * 7 / 9, 1),
}


def time_reduction(manual_seconds: float, system_seconds: float) -> dict:
    if manual_seconds <= 0:
        raise ValueError("manual_seconds must be > 0")
    return {
        "manual_seconds": manual_seconds,
        "manual_minutes": round(manual_seconds / 60.0, 2),
        "system_seconds": system_seconds,
        "absolute_reduction_seconds": round(manual_seconds - system_seconds, 3),
        "speedup_x": round(manual_seconds / system_seconds, 1),
        "pct_time_saved": round(100.0 * (1.0 - system_seconds / manual_seconds), 4),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manual-seconds",
        type=float,
        required=True,
        help="Elapsed seconds from one timed manual review of the Madison scenario",
    )
    parser.add_argument(
        "--system-seconds",
        type=float,
        default=SYSTEM_MEDIAN_NO_LLM_S,
        help=f"System median seconds (default {SYSTEM_MEDIAN_NO_LLM_S} without LLM)",
    )
    parser.add_argument("--trust", type=float, default=None, help="Mean trust Likert (Q1–Q4)")
    parser.add_argument(
        "--usefulness", type=float, default=None, help="Mean usefulness Likert (U1–U3)"
    )
    parser.add_argument(
        "--write-json",
        type=Path,
        default=Path("docs/addendum/business_evaluation_results.json"),
        help="Output JSON path",
    )
    args = parser.parse_args()

    metric1 = time_reduction(args.manual_seconds, args.system_seconds)
    out = {
        "metric_1_review_time_reduction": {
            **metric1,
            "system_median_with_llm_seconds": SYSTEM_MEDIAN_WITH_LLM_S,
            "note": "Compare same scenario: Madison Ave 40-unit multifamily",
        },
        "metric_2_constraint_completeness": COMPLETENESS,
        "metric_3_user_confidence_trust": {
            "mean_likert": args.trust,
            "scale": "1–5",
            "status": "measured" if args.trust is not None else "pending_survey",
        },
        "metric_4_usefulness_vs_manual": {
            "mean_likert": args.usefulness,
            "scale": "1–5",
            "status": "measured" if args.usefulness is not None else "pending_survey",
        },
    }

    print("=== Metric 1: Review time reduction ===")
    print(
        f"Manual: {metric1['manual_minutes']} min ({metric1['manual_seconds']} s)  |  "
        f"System: {metric1['system_seconds']} s"
    )
    print(
        f"Reduction: {metric1['absolute_reduction_seconds']} s  |  "
        f"Speedup: {metric1['speedup_x']}×  |  "
        f"Time saved: {metric1['pct_time_saved']}%"
    )
    print()
    print("=== Metric 2: Constraint completeness (Madison checklist) ===")
    print(
        f"Weighted: {COMPLETENESS['weighted_pct']}%  |  "
        f"Strict: {COMPLETENESS['strict_pct']}%  "
        f"({COMPLETENESS['identified']} identified, "
        f"{COMPLETENESS['partial']} partial, "
        f"{COMPLETENESS['missing']} missing / {COMPLETENESS['items_total']})"
    )
    print()
    print("=== Metric 3: Trust ===")
    print(out["metric_3_user_confidence_trust"])
    print("=== Metric 4: Usefulness ===")
    print(out["metric_4_usefulness_vs_manual"])

    args.write_json.parent.mkdir(parents=True, exist_ok=True)
    args.write_json.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {args.write_json}")


if __name__ == "__main__":
    main()
