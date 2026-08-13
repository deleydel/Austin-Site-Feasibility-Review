# Business Evaluation Addendum

**Project:** Austin SiteFeasibility AI  
**Purpose:** Measure the four business metrics committed in the project proposal  
**Scenario used for comparison:** 1714 Madison Avenue, Austin, TX — proposed 40-unit multifamily residential  
**Date:** 2026-08-13

This addendum addresses only the business-evaluation gap. Technical metrics (guardrail compliance, groundedness, report completeness) remain in `evaluation/results/EVALUATION.md`.

---

## Metrics overview

| # | Proposal metric | How measured | Status |
|---|-----------------|--------------|--------|
| 1 | Reduction in review time | System median vs same-scenario manual task-hour estimate | **Complete** |
| 2 | Completeness of identified constraints | Pre-defined constraint checklist vs system findings/report | **Complete** |
| 3 | User confidence and trust | Short Likert survey after reading one system report | **Skipped** (optional; not required for time-reduction response) |
| 4 | Usefulness vs manual document review | Same survey + checklist coverage vs effort | **Skipped** (optional; completeness + time already measured) |

---

## Metric 1 — Reduction in review time

### System time (already measured)

From `evaluation/scenarios/results/end_to_end_timing.json` (5 scenario runs each):

| Mode | Median wall-clock | Notes |
|------|-------------------|--------|
| Without LLM synthesis | **0.305 s** | Structured tools + RAG + guardrails + report |
| With LLM synthesis | **2.738 s** | Same pipeline plus generative synthesis |

For business comparison we use the **without-LLM** median (**0.305 s**), matching the figure already reported in the evaluation scorecard. The Madison demo wall-clock on one machine was ~3.7 s (cold path / network); use the evaluation median for apples-to-apples scenario timing.

### Manual effort (same scenario)

Team estimate of **work specific to this proposal** for a full preliminary review of **1714 Madison Avenue — 40-unit multifamily** (without the SiteFeasibility AI app). Hours are task effort for the same checks the system automates (site facts, code research, findings, report), not wall-clock of a single continuous sitting.

| Task | Work specific to this proposal | Hours |
|------|-------------------------------|------:|
| Site data collection | Confirm parcel/address; collect SF-3-NP zoning, coordinates, Shoal Creek watershed, floodplain, nearby permit/case records | 8 |
| Zoning and regulatory research | Whether 40-unit multifamily is permissible under SF-3-NP; entitlement pathways; applicable LDC provisions | 10 |
| Drainage and environmental review | Confirm no mapped floodplain intersection; ~1,320 ft floodplain proximity; Shoal Creek drainage / water-quality / environmental requirements | 10 |
| Transportation and access review | Driveway access, circulation, parking, frontage; whether additional transportation analysis may be triggered for 40 units | 10 |
| Utilities and development-history review | General water/wastewater requirements; screen ~90 permits within 800 ft plus nearby site-plan / plan-review cases for historical context | 7 |
| Findings and citation validation | Verify regulatory citations; separate confirmed site facts from assumptions; flag City/professional verification needs | 5 |
| Report preparation | Full preliminary report (zoning, site plan, drainage, transportation, utilities, historical context, constraints, missing info) | 10 |
| Senior review and final revision | Technical accuracy, inconsistencies, client-ready version | 5 |
| **Total** | | **65** |

### Time reduction (measured)

| Manual effort | System median (no LLM) | Absolute reduction | Speedup | % time saved |
|---------------|------------------------|--------------------|---------|--------------|
| **65 h = 234,000 s** | **0.305 s** | ~233,999.7 s (~65 h) | ~767,213× | ~99.9999% |

With LLM synthesis (median **2.738 s**): still ~65 h saved; speedup ~85,464×; % time saved ~99.9988%.

```bash
python docs/addendum/compute_business_metrics.py --manual-seconds 234000
```

**Interpretation:** The system is a **preliminary screening** aid, not a substitute for professional due diligence or the senior-review hours above. The comparison shows order-of-magnitude reduction in packaging a first-pass constraint screen; Metric 2 checks whether that speed trades away constraint coverage.

---

## Metric 2 — Completeness of identified constraints

### Method

Before looking at the system output, we fixed an a priori checklist of constraint categories a preliminary Austin multifamily screening should cover for this scenario. After one system run (LLM synthesis **off**, same Madison scenario), each item was scored:

- **Identified** — explicit finding, site_summary field, or dedicated report section with a clear statement  
- **Partial** — relevant retrieval / sources present, but no clear constraint finding  
- **Missing** — not surfaced

### Checklist results (Madison Ave, 40-unit MF)

| ID | Expected constraint / check | System outcome | Evidence |
|----|----------------------------|----------------|----------|
| C1 | Resolve / report zoning district | **Identified** | `SF-3-NP` from Open Data; zoning finding |
| C2 | Flag land-use conflict (MF on SF-3-NP) | **Identified** | Finding: potential zoning/use conflict for 40-unit MF |
| C3 | Floodplain intersection screening | **Identified** | `intersects_floodplain: false` + drainage finding |
| C4 | Watershed / drainage context | **Identified** | Shoal Creek + drainage/environmental citations |
| C5 | Transportation / access requirements | **Partial** | TCM/LDC citations retrieved; no dedicated “potential constraint” finding in guardrail summary |
| C6 | Water / wastewater service considerations | **Partial** | Dedicated review node + report section; screening-level, not capacity determination |
| C7 | Historical permits/cases ≠ approval precedent | **Identified** | Explicit historical-context finding + disclaimer |
| C8 | Verification / missing-info callouts | **Identified** | “verification required” labels + report missing-info section |
| C9 | Scope / preliminary-only disclaimer | **Identified** | Report disclaimer + guardrails |

### Score

| Metric | Value |
|--------|--------|
| Items identified | 7 / 9 |
| Items partial | 2 / 9 |
| Items missing | 0 / 9 |
| **Completeness (identified + 0.5×partial)** | **(7 + 1.0) / 9 = 88.9%** |
| **Strict completeness (identified only)** | **7 / 9 = 77.8%** |

**Takeaway:** Core zoning conflict, flood/watershed screening, historical-context caution, and verification needs are covered. Transportation and utilities are present as retrieval/sections but weaker as explicit constraint findings — a useful product improvement, not a silent miss of the whole category.

---

## Metric 3 — User confidence and trust

**Status: skipped** for this addendum (no Likert survey run).

Related technical proxies already in the evaluation scorecard (not a substitute for a user study):

- Guardrail compliance: **100%** (20/20 adversarial cases)  
- Citations verified on Madison demo run: **20**; rejected: **0**; unsupported claims removed: **0** (structured synthesis path)  
- Historical context explicitly labeled non-precedent  

Survey instrument retained at `docs/addendum/USER_TRUST_USEFULNESS_SURVEY.md` if the team later wants to add ratings.

---

## Metric 4 — Usefulness vs manual document review

**Status: skipped** for this addendum (no Likert survey run).

Objective signals already measured that support usefulness claims without a survey:

- Constraint completeness: **88.9%** weighted / **77.8%** strict  
- Review-time reduction: **65 h** manual → **0.305 s** system  

---

## Summary for graders

| Metric | Current evidence |
|--------|------------------|
| 1. Review-time reduction | Manual task-hour estimate **65 h** vs system median **0.305 s** (no LLM) → ~**767,213×** / ~**99.9999%** time saved on the Madison MF scenario |
| 2. Constraint completeness | **88.9%** weighted / **77.8%** strict on fixed 9-item checklist for Madison MF scenario |
| 3. Confidence / trust | **Skipped** (instrument available; technical proxies noted) |
| 4. Usefulness vs manual | **Skipped** (instrument available; completeness + time reduction stand in as objective signals) |

This addresses the TA’s Part 2 ask for **measured review-time reduction** (with the same-scenario manual baseline) and **constraint completeness**.
