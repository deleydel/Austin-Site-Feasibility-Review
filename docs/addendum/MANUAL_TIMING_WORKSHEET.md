# Manual timing worksheet — same scenario as system eval

**Scenario:** 1714 Madison Avenue, Austin, TX  
**Proposal:** 40-unit multifamily residential  
**Rule:** Do **not** use the SiteFeasibility AI app. Time only active review work.

## Steps

1. Start stopwatch.
2. Look up zoning / parcel for the address (Property Profile / GIS).
3. Check floodplain + watershed.
4. Skim code/manual guidance relevant to multifamily on the reported district (LDC / DCM / TCM / utilities as available).
5. Write a short bullet list of potential constraints / verification needs.
6. Stop stopwatch.

## Log

| Field | Value |
|-------|--------|
| Reviewer name | |
| Date | |
| Start time (clock) | |
| End time (clock) | |
| **Elapsed (MM:SS)** | |
| **Elapsed (seconds)** | |
| Sources opened | |
| Constraints you listed (bullets) | |
| | |
| | |
| | |

## After timing

```bash
python docs/addendum/compute_business_metrics.py --manual-seconds YOUR_SECONDS
```

Paste the printed Metric 1 table into `BUSINESS_EVALUATION.md`.
