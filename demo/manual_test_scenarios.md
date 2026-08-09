# Demo Test Scenarios — Streamlit Frontend

Manual walkthrough scenarios for `streamlit run app/streamlit_app.py`
(served at http://localhost:8501). Run each scenario by filling in the
form and clicking **"Run Preliminary Feasibility Review"**.

---

## Scenario 1 — Valid in-scope proposal (happy path)

| Field | Value |
| --- | --- |
| Austin street address | `301 W 2nd St, Austin, TX 78701` |
| Proposed land use | `Multifamily residential` (dropdown) |
| Development description | `120-unit mixed-income apartment building with ground-floor retail` |
| Approximate number of units | `120` |
| Approximate site area (acres) | `1.5` |

**Expected result:**
- Workflow progress steps advance through all stages
  (`validate_input` → ... → `build_report`).
- Output includes: summary, potential constraints, verification-required
  items, retrieved passages per section, source citations, and the
  preliminary-review disclaimer.
- Markdown / HTML / DOCX / PDF download buttons all produce non-empty
  files.

---

## Scenario 2 — Missing required fields

| Field | Value |
| --- | --- |
| Austin street address | *(leave blank)* |
| Proposed land use | Select `Other` from dropdown, leave the "Specify proposed land use" text box blank |
| Development description | `Small office renovation` |
| Approximate number of units | `0` |
| Approximate site area (acres) | `0.00` |

**Expected result:**
- Workflow does **not** run.
- App shows a blocked/incomplete message listing
  `missing_information: [address, proposed_land_use]`.
- No report or download options are generated.

---

## Scenario 3 — Out-of-scope address (outside Austin)

| Field | Value |
| --- | --- |
| Austin street address | `1600 Pennsylvania Ave, Washington, DC` |
| Proposed land use | `Commercial office` (dropdown) |
| Development description | `New office building` |
| Approximate number of units | `0` |
| Approximate site area (acres) | `2.0` |

**Expected result:**
- Workflow does **not** run.
- App shows a `stop_reason` message indicating the address is outside
  the supported Austin scope.

---

## Scenario 4 — Manual coordinate fallback

| Field | Value |
| --- | --- |
| Austin street address | `123 Fake St, Austin, TX` (an address geocoding may fail on) |
| Proposed land use | `Single-family residential` (dropdown) |
| Development description | `Single-family home with ADU` |
| Approximate number of units | `2` |
| Approximate site area (acres) | `0.25` |
| Optional: manual coordinates | Expand section, enter lat `30.2672`, lon `-97.7431` |

**Expected result:**
- If geocoding fails, the manually entered coordinates are used as a
  fallback instead of blocking the workflow.
- Review completes and produces a report as in Scenario 1.

---

## Scenario 5 — Report download check

Using the completed run from Scenario 1 (or 4):

1. Click **Markdown** download — verify the file opens and contains the
   summary/citations text.
2. Click **HTML** download — verify it opens in a browser and is
   formatted.
3. Click **DOCX** download — verify it opens in Word/Pages as a valid
   document (not corrupted).
4. Click **PDF** download — verify it opens and starts with a valid
   PDF header (`%PDF`).

**Expected result:** all four formats download successfully and contain
matching content.
