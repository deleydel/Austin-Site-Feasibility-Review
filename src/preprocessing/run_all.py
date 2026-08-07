"""Task 1 entry point: clean every dataset, write processed outputs,
the source manifest, and the data-quality report.

Run:  python -m src.preprocessing.run_all
"""
from __future__ import annotations

import json
import time

from src import config
from src.preprocessing import geo, structured
from src.preprocessing.manifest import write_manifest


def _md_stats(title: str, stats: dict) -> str:
    lines = [f"### {title}", "", "| metric | value |", "| --- | --- |"]
    for k, v in stats.items():
        lines.append(f"| {k} | {v} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    config.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    config.PREPROCESSING_RESULTS.mkdir(parents=True, exist_ok=True)
    all_stats: dict[str, dict] = {}
    t0 = time.time()

    print("cleaning zoning ...")
    df, all_stats["Zoning by Address"] = structured.clean_zoning()
    df.to_parquet(config.ZONING_PARQUET, index=False)

    print("cleaning permits ...")
    df, all_stats["Issued Construction Permits"] = structured.clean_permits()
    df.to_parquet(config.PERMITS_PARQUET, index=False)

    print("cleaning site plans ...")
    df, all_stats["Site Plan Cases"] = structured.clean_site_plans()
    df.to_parquet(config.SITE_PLANS_PARQUET, index=False)

    print("cleaning plan review ...")
    df, all_stats["Plan Review Cases"] = structured.clean_plan_review()
    df.to_parquet(config.PLAN_REVIEW_PARQUET, index=False)

    print("cleaning watersheds ...")
    gdf, all_stats["Watershed Boundaries"] = geo.clean_watersheds()
    gdf.to_parquet(config.WATERSHEDS_PARQUET, index=False)

    print("cleaning floodplain ...")
    gdf, all_stats["Fully Developed Floodplain"] = geo.clean_floodplain()
    gdf.to_parquet(config.FLOODPLAIN_PARQUET, index=False)

    write_manifest()
    print(f"wrote {config.SOURCE_MANIFEST}")

    report = [
        "# Data Quality Report (Task 1 preprocessing QA)",
        "",
        "Preprocessing QA evidence for Tasks 1-3. Project-level evaluation",
        "(groundedness, citation correctness, guardrails, report completeness)",
        "is owned by the evaluation workstream and is out of scope here.",
        "",
        "Deduplication rules applied:",
        "- Zoning: exact (address, zoning) duplicates removed; addresses with",
        "  multiple distinct zoning designations are KEPT and flagged",
        "  `has_multiple_zoning` (returned as `multiple_records` by the lookup tool).",
        "- Permits: exact duplicate rows removed; rows sharing a permit_number are",
        "  collapsed only when identical across audit fields (status, dates,",
        "  description, valuation, coordinates, work class); genuine variants are",
        "  retained and flagged `duplicate_permit_number`.",
        "- Plan review: VOID/test records retained with `exclude_from_search=True`.",
        "- Site plan / plan review outputs contain only allow-listed fields;",
        "  applicant, owner, and contact columns are removed.",
        "",
    ]
    for title, stats in all_stats.items():
        report.append(_md_stats(title, stats))
    report.append(f"\nTotal preprocessing time: {time.time() - t0:.1f}s\n")

    out = config.PREPROCESSING_RESULTS / "data_quality_report.md"
    out.write_text("\n".join(report))
    (config.DATA_PROCESSED / "quality_stats.json").write_text(
        json.dumps(all_stats, indent=2, default=str)
    )
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
