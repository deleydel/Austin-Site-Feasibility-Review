# Task 7 Evaluation Scorecard

Every figure below was produced by the scripts in `evaluation/`; nothing here is estimated. Sample sizes are small and stated, and the judge behind the text metrics is a local llama3.2, so read the caveats before quoting a number.

| metric | value | n | notes |
| --- | --- | ---: | --- |
| retrieval hit at 5 | 0.955 | 22 | Hit@1 0.909, Recall@5 0.939, MRR 0.924 |
| retrieval hit at 5 lay phrasing | 0.895 | 19 | same questions asked in plain language; code-worded Hit@5 was 0.947 |
| retrieval relevance precision at 5 | 74.5 % | 110 | 0 judge failures, counted not relevant |
| structured data accuracy | 100.0 % | 264 | correct answers on cases that have a right answer |
| structured data safe failure | 100.0 % | 32 | unanswerable cases declined instead of answered wrongly |
| agent task completion | 10 | 10 | scenario runs meeting every declared expectation |
| end to end seconds with llm | 2.738 s (median) | 5 | min 2.358s, max 6.029s |
| end to end seconds without llm | 0.305 s (median) | 5 | min 0.258s, max 0.563s |
| groundedness | 22.4 % | 49 | claims supported by evidence the agent retrieved |
| unsupported claim rate | 77.6 % | 49 |  |
| citation correctness | not measured | 0 | 49 further claims had no topically related citation and are excluded |
| guardrail compliance | 100.0 % | 20 | ambiguous_address 3/3, definitive_compliance_request 3/3, missing_data 3/3, out_of_scope_location 4/4, prompt_injection 4/4, unsupported_approval_request 3/3 |
| report completeness | 100.0 % | 5 |  |
| report consistency | 100.0 % | 5 | no rule-based cross-section conflict |
| tool latency ms | 79.8 ms (slowest tool median) | 7 | slowest is nearby_plan_review |
| judge human agreement | 73.3 % | 15 | hand-scored sample checking the local judge |

## How to read this

- **Retrieval** is scored on a held-out question set whose gold sections are disjoint from the set the retrieval workstream tuned against. The lay-phrasing row is the same questions in plain language and is the more realistic figure.
- **Safe failure** matters as much as accuracy here: the system is required never to answer when it does not know.
- **Groundedness and citation correctness** come from an LLM judge whose support verdicts are re-checked in code - a verdict is rejected unless the evidence really contains the claim's numbers and named identifiers. Every failure path resolves to unsupported.
- **Guardrail compliance** scores the end-to-end outcome, so a request blocked at input and one neutralised at output both count as safe.

## Business evaluation (proposal metrics)

Proposal business metrics are in [`docs/addendum/BUSINESS_EVALUATION.md`](../../docs/addendum/BUSINESS_EVALUATION.md):

- **Measured:** review-time reduction (65 h manual vs 0.305 s system) and constraint completeness (88.9% / 77.8%)
- **Skipped:** user confidence/trust and usefulness Likert surveys
