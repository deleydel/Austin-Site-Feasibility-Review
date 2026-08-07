"""Task 2 sanity benchmark: Hit@5, Recall@5, MRR over the question set,
with ablations (hybrid vs dense-only vs BM25-only; BGE query instruction
on vs off). Writes evaluation/results/retrieval_benchmark.md.

This checks that Tasks 1-2 work; full project evaluation is a separate
workstream.

Run:  python -m evaluation.retrieval.run_benchmark
"""
from __future__ import annotations

import json
import statistics
import time

from src import config
from src.rag.retriever import RegulatoryRetriever


def evaluate(retriever: RegulatoryRetriever, questions: list[dict],
             mode: str = "hybrid", k: int = 5) -> dict:
    hits = hits1 = recalls = 0
    rr = []
    latencies = []
    misses = []
    per_type: dict[str, list[int]] = {}
    detail = []
    for q in questions:
        gold = {(d, s) for d, s in q["gold"]}
        t0 = time.perf_counter()
        if mode == "hybrid":
            res = retriever.retrieve(q["question"], k=k)
        elif mode == "dense":
            ids = retriever._dense(q["question"], k, None, None)
            res = [retriever.by_id[i]["metadata"] for i in ids]
        else:  # bm25
            ids = retriever._lexical(q["question"], k, None)
            res = [retriever.by_id[i]["metadata"] for i in ids]
        latencies.append(time.perf_counter() - t0)

        got = [(r["doc_id"], r["section_number"]) for r in res]
        titles = [f"{d} {s} ({r.get('section_title', '')[:40]})"
                  for (d, s), r in zip(got, res)]
        hit_ranks = [i for i, g in enumerate(got) if g in gold]
        per_type.setdefault(q.get("type", "?"), []).append(1 if hit_ranks else 0)
        if hit_ranks:
            hits += 1
            hits1 += 1 if hit_ranks[0] == 0 else 0
            rr.append(1.0 / (hit_ranks[0] + 1))
        else:
            rr.append(0.0)
            misses.append({"id": q["id"], "question": q["question"],
                           "gold": sorted(gold), "got": got})
        found_gold = {g for g in got if g in gold}
        recalls += len(found_gold) / len(gold)
        detail.append({"id": q["id"], "type": q.get("type"),
                       "question": q["question"],
                       "gold_hit_rank": (hit_ranks[0] + 1) if hit_ranks else None,
                       "retrieved": titles})

    n = len(questions)
    return {
        "mode": mode,
        "hit_at_1": round(hits1 / n, 3),
        "hit_at_5": round(hits / n, 3),
        "recall_at_5": round(recalls / n, 3),
        "mrr": round(statistics.mean(rr), 3),
        "hit_at_5_by_type": {t: round(sum(v) / len(v), 3)
                             for t, v in per_type.items()},
        "median_latency_ms": round(1000 * statistics.median(latencies), 1),
        "misses": misses,
        "detail": detail,
    }


def main() -> None:
    questions_path = __import__("pathlib").Path(__file__).parent / "benchmark_questions.json"
    with open(questions_path) as f:
        questions = json.load(f)["questions"]

    results = {}
    for use_instr in (True, False):
        r = RegulatoryRetriever(use_query_instruction=use_instr)
        label = "instruction" if use_instr else "no_instruction"
        for mode in ("hybrid", "dense", "bm25"):
            results[f"{mode}/{label}"] = evaluate(r, questions, mode)

    lines = [
        "# Retrieval Sanity Benchmark (Task 2)",
        "",
        f"{len(questions)} questions (realistic + direct-citation), gold labels",
        "allow multiple acceptable sections. Metrics at k=5.",
        "",
        "| configuration | Hit@1 | Hit@5 | Recall@5 | MRR | median latency (ms) |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for name, res in results.items():
        lines.append(f"| {name} | {res['hit_at_1']} | {res['hit_at_5']} "
                     f"| {res['recall_at_5']} | {res['mrr']} "
                     f"| {res['median_latency_ms']} |")

    best = results["hybrid/no_instruction"]  # measured best config
    lines += ["", "## Hit@5 by question type (hybrid + no_instruction)", ""]
    for t, v in best["hit_at_5_by_type"].items():
        lines.append(f"- {t}: {v}")

    lines += ["", "## Misses (hybrid + no_instruction)", ""]
    if not best["misses"]:
        lines.append("None — every question had a gold section in the top 5.")
    for m in best["misses"]:
        lines.append(f"- **{m['id']}** {m['question']}")
        lines.append(f"  - gold: {m['gold']}")
        lines.append(f"  - got: {m['got']}")

    lines += ["", "## Per-question retrieval detail (for manual relevance review)", ""]
    for d in best["detail"]:
        rank = d["gold_hit_rank"]
        mark = f"gold at rank {rank}" if rank else "MISS"
        lines.append(f"- **{d['id']}** ({d['type']}, {mark}) {d['question']}")
        for t in d["retrieved"]:
            lines.append(f"  - {t}")

    lines.append("")
    lines.append("Latency figures are measured on this machine; they are "
                 "observations, not guarantees.")
    lines.append("A cross-encoder reranker was intentionally NOT added; "
                 "revisit only if these numbers show a meaningful gap.")
    lines.append("This benchmark is an internal sanity check for Tasks 1-3; "
                 "full-framework evaluation (groundedness, citation "
                 "correctness, guardrails) is a separate workstream.")

    out = config.REPORTS_DIR / "retrieval_benchmark.md"
    out.write_text("\n".join(lines) + "\n")
    (config.REPORTS_DIR / "retrieval_benchmark.json").write_text(
        json.dumps(results, indent=2))
    print("\n".join(lines[:20]))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
