# Data directory

`processed/` (cleaned datasets) and `index/` (vector index) **are committed**,
so after cloning you can immediately use the structured-data tools and the
regulatory retriever and run the tests — no regeneration needed.

Only `raw/` is excluded from git: Plan_Review_Cases (~123 MB) and the
floodplain GeoJSON (~128 MB) exceed GitHub's 100 MB per-file hard limit. You
only need `raw/` if you want to re-run preprocessing or re-build the index.

## Getting the raw data (optional for most workstreams)

Download `austin_raw_data.zip` from the team Google Drive:

> **Google Drive link:** [austin_raw_data.zip](https://drive.google.com/file/d/1BCKckddsYS7d_sqof1Fvi6uUoeJ4GUhP/view?usp=sharing)

Unzip it inside this `data/` directory (it extracts to `raw/…`) so the layout
matches:

```
data/
├── README.md                     # this file
├── raw/                          # original source files (NOT in git) — never modified
│   ├── regulations/              # Municode DOCX exports
│   │   ├── TITLE_25.___LAND_DEVELOPMENT..docx
│   │   ├── DRAIANAGE.docx
│   │   └── TRANSPORTATION.docx
│   └── structured/               # Austin Open Data exports (2026-08-07 snapshot)
│       ├── Zoning_By_Address_20260807.csv
│       ├── IssuedConstructionPermits.csv
│       ├── Site_Plan_Cases_20260807.csv
│       ├── Plan_Review_Cases_20260807.csv
│       ├── Watershed_Boundaries_20260807.geojson
│       └── Greater_Austin_Fully_Developed_Floodplain_20260807.geojson
├── processed/                    # Task 1 output (committed)
└── index/                        # Task 2 output (committed)
```

Original sources: Municode (LDC Title 25, Drainage Criteria Manual,
Transportation Criteria Manual) and data.austintexas.gov — full provenance,
URLs, and known limitations are recorded in `processed/source_manifest.json`
after the first preprocessing run.

## Regenerate everything (requires raw/)

```bash
python -m src.preprocessing.run_all        # -> data/processed/
python -m src.rag.indexer                  # -> data/index/ + chunk/section JSON
python -m pytest tests/                    # full test suite
python -m evaluation.retrieval.run_benchmark   # RAG metrics -> evaluation/retrieval/results/
python -m evaluation.tools.run_latency         # tool latency -> evaluation/tools/results/
```
