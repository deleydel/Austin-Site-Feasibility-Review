# Task 8 Implementation — Austin SiteFeasibility AI

Implementation of workstream **8 (Streamlit frontend)**. This is the user-
facing entry point on top of the already-implemented Task 4–6 workflow: it
collects the proposal, runs the compiled review graph, and displays the
guarded findings, citations, and a downloadable report. It adds no new
review logic — it only calls the existing `review_graph`, `report_document`,
and `export_report` interfaces described in the README.

## What's here

```
app/
├── __init__.py
└── streamlit_app.py   # single-page Streamlit frontend
```

- **Input form**: Austin street address, proposed land use, development
  description, approximate units, approximate site area, optional manual
  lat/lon fallback.
- **Progress display**: a step list mirroring the LangGraph node sequence
  (`validate_input` → ... → `build_report`) plus a spinner while the graph
  runs.
- **Findings + citations display**: summary, potential constraints,
  verification-required items, missing information, per-section retrieved
  passages, source citations, and the preliminary-review disclaimer —
  rendered from the guarded `report_document` produced by
  `src.report.build_report_document`.
- **Report download**: Markdown, HTML, DOCX, and PDF, generated with
  `src.report.export.export_report`.
- Requests outside scope or missing required fields are shown via the
  existing `stop_reason` / `missing_information` fields instead of running
  the workflow.

## Setup

```bash
pip install -r requirements.txt   # includes streamlit

python -m pytest tests/test_app.py -v

streamlit run app/streamlit_app.py
```

`tests/test_app.py` covers the non-widget logic (`run_review`, export byte
generation, finding-text extraction, workflow step list) without needing a
running Streamlit session.

## Results at a glance

| What | Result |
| --- | --- |
| Correctness tests (Task 8) | **6 / 6 pass** |
| Full suite regression | **99 / 99 pass** at time of writing (93 existing + 6 new); the suite has since grown — see the current pytest output (109 as of the latest main) |
| Live smoke: valid proposal | `input_valid=True`, `schema_complete=True` |
| Live smoke: missing fields | blocked with `missing_information=[address, proposed_land_use]` |
| Live smoke: out-of-scope address | blocked with scope `stop_reason` |
| Export formats verified | Markdown, HTML, DOCX (valid zip), PDF (valid `%PDF`) |
| Local server | `streamlit run app/streamlit_app.py` serves HTTP 200 |

## Notes

- No changes were made to `src/`, `data/`, `evaluation/`, or Tasks 1–7 code
  or docs; this workstream only adds `app/`, `tests/test_app.py`, this file,
  and one line to `requirements.txt` (`streamlit>=1.38`).
- LLM synthesis in the report summary is optional and controlled by the
  existing Task 4 environment variables (`OPENAI_API_KEY`,
  `ENABLE_LLM_SYNTHESIS`); the app works without them, with `llm_synthesis`
  omitted from the summary section.
