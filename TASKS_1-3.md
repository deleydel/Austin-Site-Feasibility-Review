# Tasks 1–3 Implementation — Austin SiteFeasibility AI

Implementation of workstreams 1 (data preprocessing), 2 (regulatory RAG), and
3 (structured-data tools). Correctness tests live in `tests/`, development
performance evaluation (retrieval benchmark, tool latency) in `evaluation/`,
and generated evidence in `reports/` — these verify Tasks 1-3 work;
full-framework evaluation (groundedness, citation correctness, guardrails,
report completeness) is the evaluation workstream's job, not covered here.

## Setup

```bash
pip install -r requirements.txt
python -m src.preprocessing.run_all             # Task 1: clean data -> data/processed/
python -m src.rag.indexer                       # Task 2: parse DOCX, chunk, embed, index
python -m pytest tests/ -v                      # correctness tests (45)
python -m evaluation.retrieval.run_benchmark    # Task 2 retrieval metrics -> reports/
python -m evaluation.tools.run_latency          # Task 3 latency -> reports/
```

Raw data lives in `data/raw/` (not committed; see `data/README.md`).

## Task 1 — preprocessing (`src/preprocessing/`)

- All four CSVs cleaned to Parquet; watershed/floodplain GeoJSON repaired
  (3 invalid geometries) and stored in EPSG:2277 (US survey feet) — the CRS
  used for every distance computation.
- Zoning: addresses normalized; the 8 addresses with multiple distinct zoning
  designations are kept and flagged, never collapsed.
- Permits: exact duplicates removed; duplicate permit numbers audited (0 after
  audit); variants would be retained and flagged.
- Site-plan / plan-review outputs contain **only allow-listed fields** — all
  applicant/owner/contact columns are dropped. VOID/test plan-review records
  (1,222) are retained with `exclude_from_search=True`.
- `data/processed/source_manifest.json` records provenance and limitations per
  source (seed for the guardrail team's approved-source list).
- QA evidence: `reports/data_quality_report.md`.

## Task 2 — regulatory RAG (`src/rag/`)

- **Loader** walks each DOCX in true XML order (tables land inside their
  sections) and classifies every paragraph
  (`mapped_to_section | document_metadata | history_note | table_caption |
  intentionally_excluded | unresolved`); the build fails if any paragraph is
  unresolved (currently 0 across all three documents; 1,356 sections).
- **Chunking**: one legal section per chunk, never crossing section
  boundaries; long sections split at subsection boundaries with 64-token
  intra-section overlap; sized with the BGE tokenizer itself —
  1,940 chunks, max 448 tokens incl. breadcrumb (hard cap 450 < 512 model
  limit). Split tables repeat their title and column-header rows in every
  piece; merged cells collapse by XML identity only, so column alignment is
  preserved (verified: § 25-2-492 SF-3 impervious cover reads 45%).
- **Embeddings**: `BAAI/bge-base-en-v1.5`, L2-normalized, cosine space,
  persistent ChromaDB.
- **Retriever**: weighted RRF fusion of dense (×2) + BM25 (×1), plus a
  deterministic citation fast path (explicit section numbers in the query
  resolve exactly). `doc_ids`/`chapters` filters let agent nodes scope
  retrieval. Every result carries full citation metadata.
- `get_section(source, section_number)` is namespaced and returns
  `found | ambiguous | not_found` (section numbers repeat across manuals and
  LDC subchapters).
- The BGE model card's short-query instruction was tested as recommended and
  **lowered** Hit@1/MRR on this corpus, so it is off by default.
- A cross-encoder reranker was evaluated as unnecessary at current numbers.

Measured (18-question internal benchmark, multiple acceptable gold sections —
`reports/retrieval_benchmark.md`):

| config (default) | Hit@1 | Hit@5 | Recall@5 | MRR |
| --- | --- | --- | --- | --- |
| hybrid, no instruction | 0.722 | 0.944 | 0.721 | 0.824 |

Regeneration from raw data only (`data/processed/`, `data/index/` deleted
first) was verified end to end: preprocessing → indexing → full test suite.
Manual inspection (random chunks, split tables, split prose sections, history
notes, retrieval results) confirmed citations, breadcrumbs, table alignment,
and subsection boundaries stay understandable; it also caught and fixed three
defects: equal-valued table columns being collapsed (alignment shift),
ARTICLE headings styled at division level stacking in breadcrumbs, and two
section headings without the § prefix failing to parse.

Known hard case: the § 25-2-492 site-development table for "max impervious
cover in SF-3" ranks below prose sections for the generic phrasing; the query
shape agent nodes will use ("SF-3 site development regulations") retrieves it,
and `get_section` fetches it exactly.

## Task 3 — structured-data tools (`src/tools/`)

All tools return JSON with explicit status and provenance; nothing is guessed.

- `normalize_address` — usaddress + USPS suffix canonicalization.
- `zoning_lookup` — exact → `found`; multi-designation address →
  `multiple_records` (all designations, none auto-selected); same-street-number
  high-similarity → `fuzzy_match` + warning; different street number → only
  `ambiguous` candidates (a neighbor's zoning is never returned as the
  subject's). Always `verification_required: true`.
- `geocode` — manual override → local permit/site-plan records (conflicts
  > 200 ft return `ambiguous`, never silently averaged; source, method,
  confidence, record count, disagreement reported) → US Census geocoder.
- `floodplain_check` — STRtree point-in-polygon; if clear, distance to nearest
  floodplain in feet, labeled "informational proximity only; no regulatory
  conclusion" (no invented distance threshold).
- `watershed_lookup` — boundary points report all intersecting watersheds.
- `nearby_permits` / `nearby_site_plan_cases` / `nearby_plan_review_cases` —
  EPSG:2277 radius search; allow-listed output fields (no PII); VOID/test
  records excluded; results labeled historical context, not approval precedent.

Measured tool latency (this machine, warm caches): 0.3–80 ms per call
(`reports/tool_latency_ms.json`, from `evaluation/tools/run_latency.py`).

## Test and evaluation coverage

`tests/` (45 pytest checks): preprocessing rules (multi-zoning preservation,
permit-dedup audit, PII allow-lists, VOID retention, geometry validity,
EPSG:2277), chunk token limits, citation-metadata completeness,
one-section-per-chunk, zero unresolved paragraphs, namespaced/ambiguous
section lookup, zoning false-positive and multi-record behavior, conflicting
geocode records, floodplain inside/outside/boundary points, watershed boundary
handling, nearby-distance math verified independently, PII allow-list, VOID
exclusion.

`evaluation/`: retrieval benchmark (Hit@1/Hit@5/Recall@5/MRR with
hybrid/dense/BM25 × instruction on/off ablations) and measured tool latency.
