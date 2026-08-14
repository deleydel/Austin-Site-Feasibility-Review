# Citation Evaluation Note

This note documents the citation-related evaluation results for the five cached `with_llm` scenarios and clarifies the difference between the existing grounding metric and the citation checks performed by the final guardrail stage.

## Evaluation Inputs

The review used the cached scenario states in:

`evaluation/scenarios/results/states/with_llm/`

Scenarios reviewed:

- `s1_normal`
- `s2_floodplain_constraint`
- `s3_multi_zoning`
- `s4_unresolvable_site`
- `s5_injection_carrier`

No scenario was re-run for this review.

## Guardrail Citation Results

The final guardrail results across the five scenarios were:

| Scenario | Verified citations | Rejected citations | Unsupported-claim detections |
|---|---:|---:|---:|
| s1_normal | 2 | 0 | 0 |
| s2_floodplain_constraint | 4 | 0 | 0 |
| s3_multi_zoning | 1 | 1 | 0 |
| s4_unresolvable_site | 8 | 0 | 0 |
| s5_injection_carrier | 5 | 0 | 12 |
| **Total** | **20** | **1** | **12** |

The guardrail therefore evaluated 21 candidate citations and retained 20.

**Citation verification acceptance rate: 20 / 21 = 95.2%.**

The one rejected citation was excluded from the supported citation set before the final guarded report was produced.

## Retained Citation Support

The 20 citations retained in the five final reports were also checked using their stored support fields.

Results:

- Retained citations: **20**
- Retained citations marked as supporting: **20**
- Retained citation support rate: **100%**

Therefore:

**Post-guardrail retained citation support rate: 100% (20/20).**

This metric describes the citations that survived the application's citation-verification and support filtering process.

## Why the Existing Citation Correctness Metric Is `null`

The existing grounding evaluation in:

`evaluation/grounding/results/grounding.json`

reports:

`citation_correctness_percent: null`

This result should not be replaced with 100%.

The grounding evaluator in `evaluation/grounding/run_grounding.py` extracts individual claims from the free-text `llm_synthesis` field and attempts to associate each extracted claim with a final-report citation.

In the recorded evaluation, those extracted synthesis claims did not have explicit claim-to-citation associations. As a result, the evaluator classified the claims as uncited and had no cited claim set from which to compute citation correctness.

This is a different measurement from the final guardrail citation checks.

## Interpretation

The results therefore support two separate conclusions:

1. **Claim-level citation correctness for extracted LLM synthesis claims was not measurable in the existing evaluation design.**

2. **The application's final guardrail citation process was measurable.**
   - 21 candidate citations were evaluated.
   - 20 were retained as verified/supporting.
   - 1 was rejected.
   - All 20 citations retained in the final reports were marked as supporting their associated review context.

The system also recorded 12 unsupported-claim detections in the injection-carrier scenario. These detections are part of the guardrail sanitization process and are not counted as successfully supported citations.

## Limitation

The current state does not persist a unique one-to-one `finding_id → citation_id` relationship for every synthesized claim.

Because of this, the project should not describe the 100% retained citation support rate as equivalent to 100% claim-level citation correctness.

A future improvement would be to persist explicit claim-to-citation provenance during synthesis so that citation correctness can be evaluated directly for every generated finding.

## Reportable Metrics

For the current project, the citation metrics that can be reported without overstating the evaluation are:

- **Citation verification acceptance rate: 95.2% (20/21)**
- **Post-guardrail retained citation support rate: 100% (20/20)**
- **Claim-level citation correctness: not measurable under the current claim-to-citation evaluation design**