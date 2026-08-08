"""Manual verification sheet and judge-agreement measurement.

A local model is a weak judge. Rather than presenting its verdicts as fact,
this samples them into a sheet a person scores by hand, then reports how often
the judge and the person agreed. The agreement rate is what licenses the
automated numbers.

Run:  python -m evaluation.manual.build_sheet          # write the blank sheet
      python -m evaluation.manual.build_sheet --score  # fold in your answers
"""

from __future__ import annotations

import argparse
import csv
import random
import re
from pathlib import Path
from typing import Any

from evaluation.common import pct, read_json, write_json
from src import config

SEED = 11
PER_STRATUM = 5

SHEET = config.MANUAL_REVIEW_DIR / "manual_review_sheet.csv"
COMPLETED = config.MANUAL_REVIEW_DIR / "manual_review_completed.csv"
KEY = config.MANUAL_REVIEW_DIR / "manual_review_key.json"

# The sheet is deliberately blind: showing the automated verdict next to the
# box the reviewer fills in biases them toward agreeing, and agreement is the
# quantity being measured. Verdicts are held in KEY and joined at scoring time.
COLUMNS = [
    "item_id",
    "stratum",
    "question_or_claim",
    "evidence_or_answer",
    "your_verdict",
    "your_note",
]

INSTRUCTIONS = {
    "retrieval_relevance": "relevant / not_relevant",
    "structured_data": "correct / incorrect",
    "citation_support": "supported / partially_supported / unsupported / uncited",
}


_SECTION_RE = re.compile(r"\b([A-Z]{3})\s+([\w.\-]+)")


def _section_index() -> dict[tuple[str, str], dict[str, Any]]:
    """Section text keyed by (doc_id, section_number).

    Read straight from the processed corpus rather than through the retriever,
    so building the packet needs no vector index and no embedding model.
    """

    try:
        sections = read_json(config.REG_SECTIONS_JSON)
    except Exception:
        return {}
    return {(s["doc_id"], s["section_number"]): s for s in sections}


def _cited_text(reference: str, index: dict, limit: int = 1200) -> str:
    """Resolve 'LDC 25-7-151 TITLE' to that section's actual wording."""

    match = _SECTION_RE.search(reference or "")
    if not match:
        return ""
    section = index.get((match.group(1), match.group(2)))
    if not section:
        return ""
    body = " ".join(str(section.get("text") or "").split())
    return body[:limit] + (" [...]" if len(body) > limit else "")


def write_packet(items: list[dict[str, Any]]) -> Path:
    """A readable packet carrying the text needed to judge each item."""

    index = _section_index()
    lines = [
        "# Manual review packet",
        "",
        "One entry per row of `manual_review_sheet.csv`. The regulation text is "
        "included so each item can be judged without looking anything up. What "
        "the automated evaluation decided is deliberately not shown.",
        "",
    ]
    for item in items:
        lines += [
            f"## {item['item_id']} - {item['stratum']}",
            "",
            f"**{'Question' if item['stratum'] == 'retrieval_relevance' else 'Claim'}:** "
            f"{item['question_or_claim']}",
            "",
            f"**Evidence offered:** {item['evidence_or_answer']}",
        ]
        body = _cited_text(item["evidence_or_answer"], index)
        if body:
            lines += ["", "> " + body.replace("\n", " ")]
        lines += [
            "",
            f"Allowed answers: `{INSTRUCTIONS[item['stratum']]}`",
            "",
            "Your verdict: ______",
            "",
            "---",
            "",
        ]

    path = config.MANUAL_REVIEW_DIR / "review_packet.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _sample(rows: list[dict], rng: random.Random) -> list[dict]:
    if len(rows) <= PER_STRATUM:
        return rows
    return rng.sample(rows, PER_STRATUM)


def collect_items(rng: random.Random) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    retrieval_path = config.RETRIEVAL_RESULTS / "retrieval_task7.json"
    if retrieval_path.exists():
        payload = read_json(retrieval_path)
        candidates = []
        for entry in ((payload.get("relevance") or {}).get("per_question") or []):
            for passage in entry["passages"]:
                candidates.append(
                    {
                        "stratum": "retrieval_relevance",
                        "question_or_claim": entry["question"],
                        "evidence_or_answer": (
                            f"{passage['doc_id']} {passage['section_number']} "
                            f"{passage['section_title']}"
                        ),
                        "automated_verdict": (
                            "relevant" if passage["relevant"] else "not_relevant"
                        ),
                    }
                )
        items += _sample(candidates, rng)

    accuracy_path = config.TOOLS_RESULTS / "tool_accuracy.json"
    if accuracy_path.exists():
        payload = read_json(accuracy_path)
        candidates = []
        for tool, entry in (payload.get("per_tool") or {}).items():
            for failure in entry.get("failures", []):
                candidates.append(
                    {
                        "stratum": "structured_data",
                        "question_or_claim": f"{tool}: {failure['case']}",
                        "evidence_or_answer": (
                            f"expected {failure['expected']} / got {failure['got']}"
                        ),
                        "automated_verdict": "incorrect",
                    }
                )
        # With no failures there is nothing contested, so sample individual
        # passing cases. Each carries the input, what the tool answered and
        # what the dataset says, which is something a person can actually
        # check; a per-tool score line is not.
        for tool, entry in (payload.get("per_tool") or {}).items():
            for case in entry.get("samples", []):
                answerable = case.get("answerable", True)
                candidates.append(
                    {
                        "stratum": "structured_data",
                        "question_or_claim": (
                            f"{tool}({case['case']}) -> returned {case['got']}"
                        ),
                        "evidence_or_answer": (
                            f"ground truth: {case['expected']}"
                            if answerable
                            else (
                                f"this input has no valid answer; the tool must "
                                f"decline rather than answer. Expected: "
                                f"{case['expected']}"
                            )
                        ),
                        "automated_verdict": "correct",
                    }
                )
        items += _sample(candidates, rng)

    grounding_path = config.GROUNDING_RESULTS / "grounding.json"
    if grounding_path.exists():
        payload = read_json(grounding_path)
        candidates = []
        for scenario, entry in (payload.get("per_scenario") or {}).items():
            for row in entry.get("rows", []):
                candidates.append(
                    {
                        "stratum": "citation_support",
                        "question_or_claim": row["claim"],
                        "evidence_or_answer": (
                            f"cited {row.get('citation')} - {row.get('citation_reason')}"
                        ),
                        "automated_verdict": row["citation_verdict"],
                    }
                )
        items += _sample(candidates, rng)

    for index, item in enumerate(items, start=1):
        item["item_id"] = f"m{index:02d}"
        item["your_verdict"] = ""
        item["your_note"] = ""
    return items


def _content_key(row: dict[str, Any]) -> tuple[str, str, str]:
    """Identity of a review item by what it asks, not by its row number."""

    return (
        str(row.get("stratum", "")).strip(),
        " ".join(str(row.get("question_or_claim", "")).split()),
        " ".join(str(row.get("evidence_or_answer", "")).split()),
    )


def _existing_answers() -> dict[tuple[str, str, str], dict[str, str]]:
    """Verdicts already entered in the sheet, keyed by item content.

    Regenerating the sheet must never destroy work already done. Answers are
    carried forward for any item whose wording is unchanged; an item whose
    content changed genuinely needs re-judging and comes back blank.
    """

    if not SHEET.exists():
        return {}
    answers = {}
    with open(SHEET, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if (row.get("your_verdict") or "").strip():
                answers[_content_key(row)] = {
                    "your_verdict": row["your_verdict"].strip(),
                    "your_note": (row.get("your_note") or "").strip(),
                }
    return answers


def write_sheet(items: list[dict[str, Any]]) -> tuple[Path, int, int]:
    """Write the sheet, preserving verdicts already entered.

    Returns (path, carried_over, needing_answer).
    """

    preserved = _existing_answers()
    if preserved:
        backup = SHEET.with_suffix(".csv.bak")
        backup.write_text(SHEET.read_text(encoding="utf-8"), encoding="utf-8")

    carried = 0
    SHEET.parent.mkdir(parents=True, exist_ok=True)
    with open(SHEET, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        for item in items:
            row = {k: item.get(k, "") for k in COLUMNS}
            prior = preserved.get(_content_key(item))
            if prior:
                row["your_verdict"] = prior["your_verdict"]
                row["your_note"] = prior["your_note"]
                carried += 1
            writer.writerow(row)

    write_json(KEY, {i["item_id"]: i["automated_verdict"] for i in items})
    return SHEET, carried, len(items) - carried

    guide = config.MANUAL_REVIEW_DIR / "HOW_TO_SCORE.md"
    guide.write_text(
        "\n".join(
            [
                "# Manual verification",
                "",
                f"Open `{SHEET.name}`, fill the `your_verdict` column for every "
                "row, save it as `manual_review_completed.csv` in this folder, "
                "then run:",
                "",
                "```",
                "python -m evaluation.manual.build_sheet --score",
                "```",
                "",
                "Allowed values by stratum:",
                "",
                *(f"- `{k}`: {v}" for k, v in INSTRUCTIONS.items()),
                "",
                "The sheet does not show what the automated evaluation "
                "decided. That is deliberate: seeing the machine's answer "
                "next to your box would pull your answer toward it, and the "
                "agreement between the two is exactly what is being measured. "
                "The verdicts are held in `manual_review_key.json` and joined "
                "in when you run `--score`.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return SHEET


def score() -> dict[str, Any]:
    if not COMPLETED.exists():
        raise SystemExit(
            f"{COMPLETED} not found. Fill in {SHEET.name}, save it under that "
            "name, then re-run with --score."
        )

    if not KEY.exists():
        raise SystemExit(
            f"{KEY} not found. Regenerate the sheet before scoring it."
        )
    key = read_json(KEY)

    with open(COMPLETED, newline="", encoding="utf-8") as handle:
        rows = [r for r in csv.DictReader(handle)]

    scored = [r for r in rows if (r.get("your_verdict") or "").strip()]

    def agrees(row: dict) -> bool:
        automated = str(key.get(row["item_id"], "")).strip().lower()
        return bool(automated) and row["your_verdict"].strip().lower() == automated

    agreements = [r for r in scored if agrees(r)]

    by_stratum: dict[str, dict[str, Any]] = {}
    for row in scored:
        entry = by_stratum.setdefault(
            row["stratum"], {"scored": 0, "agreed": 0, "disagreements": []}
        )
        entry["scored"] += 1
        if agrees(row):
            entry["agreed"] += 1
        else:
            entry["disagreements"].append(
                {
                    "item_id": row["item_id"],
                    "item": row["question_or_claim"][:160],
                    "automated": key.get(row["item_id"]),
                    "manual": row["your_verdict"],
                    "note": row.get("your_note", ""),
                }
            )
    for entry in by_stratum.values():
        entry["agreement_percent"] = pct(entry["agreed"], entry["scored"])

    payload = {
        "items_in_sheet": len(rows),
        "items_scored": len(scored),
        "items_agreed": len(agreements),
        "agreement_percent": pct(len(agreements), len(scored)),
        "by_stratum": by_stratum,
    }
    write_json(config.MANUAL_REVIEW_DIR / "manual_agreement.json", payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--score", action="store_true")
    parser.add_argument(
        "--packet-only",
        action="store_true",
        help="write the reading packet and answer key, leaving the CSV alone "
             "(useful when the sheet is open in a spreadsheet application)",
    )
    args = parser.parse_args()

    if args.score:
        payload = score()
        print(
            f"{payload['items_agreed']}/{payload['items_scored']} agreed "
            f"({payload['agreement_percent']}%)"
        )
        for stratum, entry in payload["by_stratum"].items():
            print(f"  {stratum}: {entry['agreed']}/{entry['scored']}")
        return

    items = collect_items(random.Random(SEED))
    if not items:
        raise SystemExit(
            "no results to sample; run the evaluation stages first"
        )
    if args.packet_only:
        write_json(KEY, {i["item_id"]: i["automated_verdict"] for i in items})
        packet = write_packet(items)
        print(f"wrote {packet} with {len(items)} items")
        print(f"wrote {KEY} (answer key, joined in at scoring time)")
        print("left the CSV untouched (--packet-only)")
        return

    path, carried, blank = write_sheet(items)
    packet = write_packet(items)
    print(f"wrote {path} with {len(items)} items")
    if carried:
        print(
            f"  carried forward {carried} verdict(s) you had already entered; "
            f"previous sheet copied to {SHEET.with_suffix('.csv.bak').name}"
        )
    print(f"  {blank} item(s) still need a verdict")
    print(f"wrote {packet} (regulation text inline, for judging without lookups)")
    print(f"see {config.MANUAL_REVIEW_DIR / 'HOW_TO_SCORE.md'}")


if __name__ == "__main__":
    main()

