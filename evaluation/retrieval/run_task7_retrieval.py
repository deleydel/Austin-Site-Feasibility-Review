"""Retrieval quality on the Task 7 held-out question set.

Hit@1/Hit@5/Recall@5/MRR come from Task 2's scoring function, applied to
questions whose gold sections that work never saw. Retrieval relevance is
added on top: the judge scores each returned passage, so a question that
"hit" while surfacing four irrelevant passages is visible as low precision.

Run:  python -m evaluation.retrieval.run_task7_retrieval
      python -m evaluation.retrieval.run_task7_retrieval --no-judge
"""

from __future__ import annotations

import argparse
from typing import Any

from evaluation.common import load_benchmark, pct, write_json
from evaluation.judge import get_judge, prompts
from evaluation.retrieval.run_benchmark import evaluate
from src import config
from src.rag.retriever import RegulatoryRetriever

K = 5


def calibrate_relevance_judge(
    retriever: RegulatoryRetriever, questions: list[dict], judge, sample: int = 8
) -> dict[str, Any]:
    """Measure the relevance judge before trusting its verdicts.

    Each question is paired with its own gold section, which must read as
    relevant, and with an unrelated section, which must not. A judge that
    fails this cannot be quoted: a first run of this metric returned 0/110
    relevant while Hit@5 was 0.955, which was the judge, not the retriever.
    """

    gold_correct = gold_total = distractor_correct = distractor_total = 0
    for index, question in enumerate(questions[:sample]):
        doc_id, section_number = question["gold"][0]
        resolved = retriever.get_section(doc_id, section_number)
        if resolved.get("status") != "found":
            continue
        match = resolved["matches"][0]

        call = prompts.passage_relevance(
            question["question"],
            {
                "text": match.get("text"),
                "doc_id": doc_id,
                "section_number": section_number,
                "section_title": match.get("section_title"),
            },
        )
        verdict = judge.ask_or_default(
            call.system, call.user, call.default, call.required_keys, call.task
        )
        gold_total += 1
        gold_correct += int(bool(verdict.get("relevant")))

        # An unrelated question's gold section is a known-irrelevant passage.
        other = questions[(index + len(questions) // 2) % len(questions)]
        other_doc, other_section = other["gold"][0]
        if (other_doc, other_section) == (doc_id, section_number):
            continue
        other_resolved = retriever.get_section(other_doc, other_section)
        if other_resolved.get("status") != "found":
            continue
        other_match = other_resolved["matches"][0]
        call = prompts.passage_relevance(
            question["question"],
            {
                "text": other_match.get("text"),
                "doc_id": other_doc,
                "section_number": other_section,
                "section_title": other_match.get("section_title"),
            },
        )
        verdict = judge.ask_or_default(
            call.system, call.user, call.default, call.required_keys, call.task
        )
        distractor_total += 1
        distractor_correct += int(not verdict.get("relevant"))

    return {
        "gold_passages_tested": gold_total,
        "gold_called_relevant": gold_correct,
        "sensitivity_percent": pct(gold_correct, gold_total),
        "distractors_tested": distractor_total,
        "distractors_called_irrelevant": distractor_correct,
        "specificity_percent": pct(distractor_correct, distractor_total),
    }


def score_relevance(retriever: RegulatoryRetriever, questions: list[dict], judge) -> dict[str, Any]:
    """Judge whether each retrieved passage addresses its question."""

    per_question = []
    relevant = judged = failed = 0
    for question in questions:
        passages = retriever.retrieve(question["question"], k=K)
        verdicts = []
        for passage in passages:
            call = prompts.passage_relevance(question["question"], passage)
            verdict = judge.ask_or_default(
                call.system, call.user, call.default, call.required_keys, call.task
            )
            is_relevant = bool(verdict.get("relevant"))
            judged += 1
            relevant += int(is_relevant)
            failed += int(bool(verdict.get("judge_failed")))
            verdicts.append(
                {
                    "doc_id": passage.get("doc_id"),
                    "section_number": passage.get("section_number"),
                    "section_title": passage.get("section_title"),
                    "relevant": is_relevant,
                    "reason": verdict.get("reason"),
                    "judge_failed": bool(verdict.get("judge_failed")),
                }
            )
        hits = sum(1 for v in verdicts if v["relevant"])
        per_question.append(
            {
                "id": question["id"],
                "question": question["question"],
                "precision_at_5": round(hits / len(verdicts), 3) if verdicts else None,
                "passages": verdicts,
            }
        )
        print(f"  {question['id']}: {hits}/{len(verdicts)} relevant", flush=True)

    return {
        "passages_judged": judged,
        "passages_relevant": relevant,
        "precision_at_5_percent": pct(relevant, judged),
        "judge_failures": failed,
        "per_question": per_question,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    core = payload["ranking"]
    lines = [
        "# Retrieval Quality - Task 7 held-out set",
        "",
        f"{payload['n_questions']} questions, k={K}, hybrid retrieval with the "
        "measured-best configuration (no BGE query instruction). Gold sections "
        "are disjoint from Task 2's benchmark.",
        "",
        "| metric | value |",
        "| --- | --- |",
        f"| Hit@1 | {core['hit_at_1']} |",
        f"| Hit@5 | {core['hit_at_5']} |",
        f"| Recall@5 | {core['recall_at_5']} |",
        f"| MRR | {core['mrr']} |",
        f"| median latency (ms) | {core['median_latency_ms']} |",
    ]
    calibration = payload.get("judge_calibration")
    relevance = payload.get("relevance")
    if relevance and relevance.get("precision_at_5_percent") is not None:
        lines.append(
            f"| judged relevance, precision@5 | "
            f"{relevance['precision_at_5_percent']}% "
            f"({relevance['passages_relevant']}/{relevance['passages_judged']}) |"
        )

    if calibration:
        lines += [
            "",
            "## Relevance judge calibration",
            "",
            "The judge is measured before its verdicts are used: gold sections "
            "should read as relevant, unrelated sections should not.",
            "",
            f"- sensitivity: {calibration['sensitivity_percent']}% "
            f"({calibration['gold_called_relevant']}/"
            f"{calibration['gold_passages_tested']} gold passages called relevant)",
            f"- specificity: {calibration['specificity_percent']}% "
            f"({calibration['distractors_called_irrelevant']}/"
            f"{calibration['distractors_tested']} unrelated passages rejected)",
        ]

    lines += ["", "## Hit@5 by question type", ""]
    for qtype, value in core["hit_at_5_by_type"].items():
        lines.append(f"- {qtype}: {value}")

    sensitivity = payload.get("phrasing_sensitivity")
    if sensitivity:
        code = sensitivity["code_worded"]
        lay = sensitivity["lay_worded"]
        lines += [
            "",
            "## Sensitivity to question phrasing",
            "",
            "These questions were written while reading the regulations, so "
            "their wording matches the source vocabulary. The same "
            f"{sensitivity['n_questions']} questions were rescored in lay "
            "developer language against identical gold labels.",
            "",
            "| phrasing | Hit@1 | Hit@5 | Recall@5 | MRR |",
            "| --- | --- | --- | --- | --- |",
            f"| as written (code vocabulary) | {code['hit_at_1']} | "
            f"{code['hit_at_5']} | {code['recall_at_5']} | {code['mrr']} |",
            f"| lay paraphrase | {lay['hit_at_1']} | {lay['hit_at_5']} | "
            f"{lay['recall_at_5']} | {lay['mrr']} |",
            "",
            "Questions the lay phrasing missed:",
            "",
        ]
        if not lay["misses"]:
            lines.append("None.")
        for miss in lay["misses"]:
            lines.append(f"- **{miss['id']}** {miss['question']}")
            lines.append(f"  - gold: {miss['gold']}")
            lines.append(f"  - retrieved: {miss['got']}")

    lines += ["", "## Questions with no gold section in the top 5", ""]
    if not core["misses"]:
        lines.append("None.")
    for miss in core["misses"]:
        lines.append(f"- **{miss['id']}** {miss['question']}")
        lines.append(f"  - gold: {miss['gold']}")
        lines.append(f"  - retrieved: {miss['got']}")

    if relevance:
        lines += ["", "## Judged relevance per question", ""]
        for entry in relevance["per_question"]:
            lines.append(
                f"- **{entry['id']}** precision@5 = {entry['precision_at_5']} "
                f"- {entry['question']}"
            )
            for passage in entry["passages"]:
                mark = "relevant" if passage["relevant"] else "not relevant"
                lines.append(
                    f"  - [{mark}] {passage['doc_id']} {passage['section_number']} "
                    f"{(passage['section_title'] or '')[:60]} - {passage['reason']}"
                )
        if relevance["judge_failures"]:
            lines += [
                "",
                f"{relevance['judge_failures']} passage verdicts could not be "
                "obtained and were counted as not relevant (fail closed).",
            ]

    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--no-judge",
        action="store_true",
        help="skip judged relevance and report ranking metrics only",
    )
    args = parser.parse_args()

    questions = load_benchmark("regulatory_questions.json")["questions"]
    retriever = RegulatoryRetriever(use_query_instruction=False)

    print(f"scoring {len(questions)} held-out questions ...", flush=True)
    ranking = evaluate(retriever, questions, mode="hybrid", k=K)

    # The benchmark's questions were authored while reading the corpus, so
    # their wording tracks the regulations' own vocabulary. Scoring the lay
    # paraphrases against the same gold labels shows how much of the ranking
    # score comes from that terminology match rather than from retrieval.
    paraphrased = [
        {**q, "question": q["paraphrase"]} for q in questions if q.get("paraphrase")
    ]
    lay = evaluate(retriever, paraphrased, mode="hybrid", k=K) if paraphrased else None
    realistic = [q for q in questions if q.get("paraphrase")]
    code_worded = evaluate(retriever, realistic, mode="hybrid", k=K) if realistic else None

    relevance = None
    calibration = None
    if not args.no_judge:
        judge = get_judge()
        judge.require()
        print("calibrating the relevance judge ...", flush=True)
        calibration = calibrate_relevance_judge(retriever, questions, judge)
        print(f"  {calibration}", flush=True)
        print("judging passage relevance ...", flush=True)
        relevance = score_relevance(retriever, questions, judge)

    payload = {
        "n_questions": len(questions),
        "k": K,
        "ranking": ranking,
        "phrasing_sensitivity": {
            "n_questions": len(paraphrased),
            "code_worded": code_worded,
            "lay_worded": lay,
        }
        if lay
        else None,
        "relevance": relevance,
        "judge_calibration": calibration,
    }
    write_json(config.RETRIEVAL_RESULTS / "retrieval_task7.json", payload)
    markdown = render_markdown(payload)
    (config.RETRIEVAL_RESULTS / "retrieval_task7.md").write_text(
        markdown, encoding="utf-8"
    )
    print("\n".join(markdown.splitlines()[:14]))
    print(f"\nwrote {config.RETRIEVAL_RESULTS / 'retrieval_task7.md'}")


if __name__ == "__main__":
    main()
