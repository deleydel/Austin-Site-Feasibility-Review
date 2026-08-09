# Tasks 5–6 Implementation — Austin SiteFeasibility AI

Implementation of workstreams **5 (guardrails and citation validation)** and
**6 (report formatting and export)**. These sit after the Task 4 agentic
synthesis node: guardrails validate and sanitize the workflow output, then the
report package turns the guarded payload into a downloadable document.

Full-framework evaluation of groundedness, citation correctness, and guardrail
compliance belongs to Task 7 and is not covered here.

## Setup

```bash
pip install -r requirements.txt   # includes fpdf2 for PDF export

python -m pytest tests/test_guardrails.py tests/test_report.py -v
```

End-to-end smoke (uses Tasks 1–4 outputs already committed in `data/`):

```bash
python - <<'EOF'
from src.agents.graph import review_graph
from src.report.export import export_report

result = review_graph.invoke({
    "proposal": {
        "address": "1714 Madison Avenue, Austin, TX",
        "proposed_land_use": "Multifamily residential",
        "development_description": "Proposed 40-unit multifamily residential development",
        "units": 40,
    }
})
print(result["final_report"]["status"])
print(result["guardrail_result"])
export_report(result["final_report"], "data/processed/feasibility_reports/demo.docx")
export_report(result["final_report"], "data/processed/feasibility_reports/demo.html")
EOF
```

Optional LLM synthesis (Task 4) only runs when both are set:

```bash
export OPENAI_API_KEY=...
export ENABLE_LLM_SYNTHESIS=true
```

---

## Results at a glance

| What | Result |
| --- | --- |
| Correctness tests (Tasks 5–6) | **19 / 19 pass** |
| Workflow integration | `synthesize_review → apply_guardrails → build_report → END` |
| Scope hardening | Rejects non-Austin cities (e.g. Round Rock) and foreign addresses (e.g. Paris) |
| Citation verification | Section must **exist and support** the claim/context (term-overlap check) |
| Report quality | Section-scoped citations, no ambiguous single-zoning claim, stable historical disclaimer |
| Export formats | DOCX, HTML, PDF, Markdown |

---

## Task 5 — Guardrails and citation validation (`src/guardrails/`)

**What it does.** Validates that a request stays inside Austin preliminary-review
scope, accepts regulatory claims only from the approved source list, verifies
citations against the section index, neutralizes unsupported definitive claims,
scrubs contact information, and classifies findings with cautious labels.

| Module | Role |
| --- | --- |
| `scope.py` | Austin-only scope; rejects out-of-city sites and approval/permit requests |
| `sources.py` | Approved-source whitelist from `data/processed/source_manifest.json` + `SOURCE_DOCS` |
| `citations.py` | Extract citations from retrieved evidence; verify section numbers via the regulatory section index (no ChromaDB required for verification) |
| `claims.py` | Detect/sanitize definitive approval, compliance, feasibility, utility-capacity, and historical-precedent claims; classify site findings |
| `privacy.py` | Redact emails, phone numbers, and labeled contact fields |
| `validate.py` | Orchestrator used as the LangGraph `apply_guardrails` node |

**Key rules:**

- Scope validation also runs early inside Task 4 `validate_input`.
- Addresses are parsed for city/state/country; any non-Austin city or foreign
  country is blocked (not only a hard-coded major-city list).
- Zoning Open Data results remain preliminary (`verification required`).
  Ambiguous / multi-record zoning never populates a single `reported_zoning`.
- Nearby permits / cases use a fixed historical-context note (not approval
  precedent). Claim sanitization is negation-aware so that cautionary wording
  is not corrupted.
- Citations must be on the approved source list, resolve in the section index,
  **and** pass a claim/context support check against section text.
- Finding labels are restricted to:
  - `potential constraint`
  - `verification required`
  - `insufficient information`
  - `no major issue identified from available data`
- Failed claims are removed, revised, or marked for verification before export.
- Blocked / invalid requests still produce a guarded `final_report` with
  `status="blocked"` so Task 6 can package a cautious response.

**Primary interface:**

```python
from src.guardrails import apply_guardrails, validate_scope
```

`apply_guardrails(state)` writes:

- `final_report` — guarded report payload
- `citations` — verified citation list
- `guardrail_result` — counts / status summary
- updated `warnings` and `execution_trace`

---

## Task 6 — Report formatting and export (`src/report/`)

**What it does.** Converts the guarded `final_report` into a stable document
schema, renders a consistent template (including disclaimer and formatted
citations), and exports downloadable files. Layout and file creation are plain
Python — not LLM-generated.

| Module | Role |
| --- | --- |
| `schema.py` | Required report sections and `build_report_document(...)` |
| `template.py` | Citation formatting + Markdown rendering |
| `export.py` | DOCX / HTML / PDF / Markdown writers |
| `build.py` | LangGraph `build_report` node → `report_document` |

**Required report sections:**

1. Project and site description  
2. Sources consulted  
3. Zoning and land-use context  
4. Site-plan considerations  
5. Drainage, flood, and environmental considerations  
6. Transportation and access considerations  
7. General water and wastewater considerations  
8. Historical permit and case context  
9. Potential constraints  
10. Missing information and required verification  
11. Source citations  
12. Preliminary-review disclaimer  

**Primary interface:**

```python
from src.report import build_report_document, export_report

document = build_report_document(result["final_report"])
export_report(result["final_report"], "out/feasibility.docx")
export_report(result["final_report"], "out/feasibility.html")
export_report(result["final_report"], "out/feasibility.pdf")
```

Default export directory constant: `src.config.REPORT_OUTPUT_DIR`
(`data/processed/feasibility_reports/`).

---

## Workflow wiring

Updated Task 4 graph path:

```text
START
  → validate_input          # includes Task 5 scope check
  → collect_site_context
  → zoning / drainage / transportation / water / historical review nodes
  → synthesize_review
  → apply_guardrails        # Task 5
  → build_report            # Task 6
  → END
```

Invalid or out-of-scope input skips site tools and still runs
`apply_guardrails` + `build_report` so the UI can show a blocked, source-aware
response.

---

## Test coverage

`tests/test_guardrails.py` (Task 5):

- Austin scope accept / out-of-city reject / unsupported approval request reject
- Approved-source whitelist from the committed manifest
- Citation verification for a known LDC section
- Rejection of unapproved sources
- Unsupported-claim sanitization
- Privacy redaction
- Finding-label classification
- End-to-end `apply_guardrails` on a synthetic synthesis payload

`tests/test_report.py` (Task 6):

- Required sections present (`schema_complete`)
- Citation formatting and Markdown render
- HTML / DOCX / PDF / Markdown export file creation

`tests/test_agents.py` was updated so the full graph expects
`apply_guardrails` and `build_report` in the execution trace.
