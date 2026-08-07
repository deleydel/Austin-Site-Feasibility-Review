# Tasks 1–3 Implementation — Austin SiteFeasibility AI

Implementation of workstreams **1 (data preprocessing)**, **2 (regulatory
RAG)**, and **3 (structured-data tools)**. Correctness tests live in `tests/`,
development performance evaluation (retrieval benchmark, tool latency) in
`evaluation/`, and generated evidence in `evaluation/results/` — these verify Tasks 1–3
work. Full-framework evaluation (groundedness, citation correctness,
guardrails, report completeness) belongs to the evaluation workstream and is
not covered here.

## Setup

```bash
pip install -r requirements.txt
# put raw data in data/raw/  (see data/README.md for the download link)

python -m src.preprocessing.run_all             # Task 1: clean data -> data/processed/
python -m src.rag.indexer                       # Task 2: parse DOCX, chunk, embed, index
python -m pytest tests/ -v                      # correctness tests (45)
python -m evaluation.retrieval.run_benchmark    # Task 2 retrieval metrics -> evaluation/results/
python -m evaluation.tools.run_latency          # Task 3 latency -> evaluation/results/
```

---

## Results at a glance

| What | Result |
| --- | --- |
| Correctness tests | **45 / 45 pass** |
| Regulatory corpus parsed | 1,356 sections, **0 unclassified paragraphs** |
| Chunks indexed | 1,940 (max 448 BGE tokens — under the 512 model limit) |
| Retrieval Hit@5 / Hit@1 | **0.944** / 0.722 (18-question benchmark) |
| Retrieval MRR / Recall@5 | 0.824 / 0.721 |
| Citation-number queries | **100 %** Hit@5 |
| Tool latency (median) | 0.2 – 80 ms per call |
| Full regeneration from raw data | verified end-to-end (processed/index deleted first) |

Details for each number are below; raw outputs are in `evaluation/results/`.

---

## Task 1 — Data preprocessing (`src/preprocessing/`)

**What it does.** Cleans the four structured CSVs and two GeoJSON layers into
Parquet/GeoParquet, writes a provenance manifest, and generates a data-quality
report.

**Key rules (safety-reviewed):**

- Addresses with multiple distinct zoning designations are **kept and
  flagged**, never collapsed to one.
- Duplicate permit numbers are **audited**, not blindly deduplicated: rows are
  collapsed only when identical across status, dates, description, valuation,
  coordinates, and work class.
- Site-plan / plan-review outputs contain **only allow-listed fields** — all
  applicant, owner, and contact columns are removed (privacy guardrail).
- VOID/test plan-review records are **retained** with
  `exclude_from_search=True` for auditability.
- All geometry is stored in **EPSG:2277** (Texas Central, US survey feet) —
  the CRS used for every distance computation; invalid geometries repaired.
- `data/processed/source_manifest.json` records provenance, snapshot date, and
  limitations per source (seed for the guardrail team's approved-source list).

**Results** (full detail: `evaluation/results/data_quality_report.md`):

| Dataset | Rows in → out | Notable findings |
| --- | --- | --- |
| Zoning by Address | 263,326 → 263,311 | 15 exact dupes removed; **8 multi-zoning addresses flagged**; 0 null zoning |
| Issued Construction Permits | 60,395 → 60,395 | 0 duplicate permit numbers after audit; 100 % have coordinates |
| Site Plan Cases | 23,630 → 23,630 | 24 PII columns dropped; 4,389 rows lack coordinates (flagged, kept) |
| Plan Review Cases | 160,135 → 160,135 | 33 PII columns dropped; **1,222 VOID/test rows flagged**, not deleted |
| Watershed Boundaries | 76 → 76 | 0 invalid geometries |
| Floodplain (fully developed) | 12,039 → 12,039 | **3 invalid geometries repaired** |

---

## Task 2 — Regulatory RAG (`src/rag/`)

**Pipeline:** DOCX → sections → chunks → embeddings → hybrid retrieval.

- **Loader** (`docx_loader.py`): walks each DOCX in true XML order (tables
  land inside their sections) and classifies **every** paragraph as
  `mapped_to_section | document_metadata | history_note | table_caption |
  intentionally_excluded | unresolved`. The build fails if anything is
  unresolved — currently **0** across all three documents:

  | Document | Sections | Mapped paragraphs | History notes | Unresolved |
  | --- | --- | --- | --- | --- |
  | LDC Title 25 (ch. 25-1…25-9) | 1,164 | 10,952 | 1,149 | **0** |
  | Drainage Criteria Manual (§1, 2, 8, App. E) | 42 | 455 | 30 | **0** |
  | Transportation Criteria Manual (§1, 7, 9, 10) | 150 | 685 | 2 | **0** |

- **Chunking** (`chunker.py`): one legal section per chunk, **never crossing
  section boundaries**; long sections split at subsection boundaries with
  64-token intra-section overlap; sized with the BGE tokenizer itself —
  1,940 chunks, max 448 tokens incl. breadcrumb (hard cap 450 < 512 model
  limit). Split tables repeat their title + column-header rows in every piece;
  merged cells collapse by XML identity only, so column alignment is preserved
  (verified: § 25-2-492 reads SF-3 impervious cover = 45 %).
- **Embeddings / index** (`indexer.py`): `BAAI/bge-base-en-v1.5`,
  L2-normalized, cosine space, persistent ChromaDB.
- **Retriever** (`retriever.py`): weighted reciprocal-rank fusion of dense
  (×2) + BM25 (×1), plus a deterministic **citation fast path** (an explicit
  section number in the query resolves exactly). `doc_ids` / `chapters`
  filters let agent nodes scope retrieval. Every result carries full citation
  metadata (source, chapter, section number, title, breadcrumb, URL).
- **`get_section(source, section_number)`** is namespaced and returns
  `found | ambiguous | not_found` — section numbers repeat across manuals and
  LDC subchapters, so exact lookup must never fall through to the wrong
  document.

**Retrieval benchmark** — 18 questions (15 realistic site-development + 3
direct-citation), multiple acceptable gold sections per question, k = 5
(full detail incl. per-question retrievals: `evaluation/results/retrieval_benchmark.md`):

| Configuration | Hit@1 | Hit@5 | Recall@5 | MRR | Median latency |
| --- | --- | --- | --- | --- | --- |
| **Hybrid, no instruction (default)** | **0.722** | **0.944** | **0.721** | **0.824** | 9.5 ms |
| Hybrid, with BGE instruction | 0.667 | 0.944 | 0.721 | 0.782 | 8.8 ms |
| Dense only | 0.500 | 0.889 | 0.647 | 0.678 | 4.2 ms |
| BM25 only | 0.278 | 0.667 | 0.467 | 0.454 | 2.2 ms |

By question type (default config): realistic 0.933 Hit@5, citation **1.000**.

Findings worth knowing:

- The BGE model card's short-query instruction was tested as the card
  recommends — it **lowered** Hit@1/MRR on this corpus, so it is off by
  default.
- Hybrid beats either retriever alone: dense misses exact-citation queries,
  BM25 misses paraphrased ones.
- A cross-encoder reranker was evaluated as unnecessary at these numbers.
- Known hard case: the § 25-2-492 site-development *table* ranks below prose
  sections for the generic phrasing "max impervious cover in SF-3"; the query
  shape agent nodes will actually issue ("SF-3 site development regulations")
  retrieves it, and `get_section("LDC", "25-2-492")` fetches it exactly.
- Regeneration from raw data only (processed/index deleted first) was
  verified, and manual inspection of chunks/tables/splits caught and fixed
  three parsing defects (table column alignment, breadcrumb article stacking,
  two headings missing the § prefix).

---

## Task 3 — Structured-data tools (`src/tools/`)

All tools return JSON with an explicit `status` and provenance; nothing is
guessed, and every uncertain case is surfaced instead of resolved silently.

| Tool | Behavior | Safety rule |
| --- | --- | --- |
| `normalize_address` | usaddress parse + USPS suffix canonicalization | never raises on messy input |
| `zoning_lookup` | exact → `found`; multi-designation → `multiple_records` (all designations returned) | a neighbor's zoning is **never** returned for a different street number — only `ambiguous` candidates; always `verification_required` |
| `geocode` | manual override → local permit/site-plan records → US Census fallback | records disagreeing > 200 ft return `ambiguous` with all candidates — never silently averaged |
| `floodplain_check` | STRtree point-in-polygon; distance to nearest floodplain if clear | proximity labeled "informational only; no regulatory conclusion" — no invented thresholds |
| `watershed_lookup` | point-in-polygon over 76 watersheds | boundary points report **all** intersecting watersheds |
| `nearby_permits` / `nearby_site_plan_cases` / `nearby_plan_review_cases` | radius search in EPSG:2277 feet | allow-listed output fields (no PII); VOID/test excluded; labeled historical context, **not approval precedent** |

**Measured latency** (this machine, warm caches, median of 5 —
`evaluation/results/tool_latency_ms.json`; observations, not guarantees):

| Tool | Median | Max |
| --- | --- | --- |
| watershed_lookup | 0.2 ms | 0.3 ms |
| floodplain_check | 0.5 ms | 0.6 ms |
| geocode (local) | 4.4 ms | 5.0 ms |
| nearby_site_plans | 4.9 ms | 5.6 ms |
| zoning_lookup | 8.2 ms | 8.5 ms |
| nearby_permits | 16.6 ms | 17.5 ms |
| nearby_plan_review | 79.5 ms | 81.0 ms |

---

## Test and evaluation coverage

`tests/` — 45 pytest checks:

- **test_preprocessing.py** (Task 1): multi-zoning preservation, dedup-audit
  flags, PII allow-list enforcement, VOID retention, date parsing, geometry
  validity, EPSG:2277 coordinate ranges, manifest completeness.
- **test_rag.py** (Task 2): chunk token limits, citation-metadata
  completeness, one-section-per-chunk, zero unresolved paragraphs,
  scoped-filter behavior, namespaced/ambiguous section lookup.
- **test_tools.py** (Task 3): zoning ground truth and false-positive checks,
  conflicting geocode records, floodplain inside/outside/**boundary** points,
  watershed boundary handling, nearby-distance math verified independently,
  PII absence, VOID exclusion.

`evaluation/` — retrieval benchmark (Hit@1/Hit@5/Recall@5/MRR with
hybrid/dense/BM25 × instruction on/off ablations) and tool-latency
measurement. Both write their results to `evaluation/results/`.
