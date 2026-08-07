# Data directory (contents not committed to git)

Raw inputs are too large for GitHub (Plan_Review_Cases ~123 MB and the
floodplain GeoJSON ~128 MB exceed GitHub's 100 MB per-file hard limit), and
`processed/` + `index/` are fully regenerated from them.

## Getting the data

Download `austin_raw_data.zip` from the team Google Drive:

> **Google Drive link:** [austin_raw_data.zip](https://drive.google.com/file/d/1BCKckddsYS7d_sqof1Fvi6uUoeJ4GUhP/view?usp=sharing)

Unzip it inside this `data/` directory (it extracts to `raw/…`) so the layout
matches:

```
data/
├── README.md                     # this file (the only committed item)
├── raw/                          # original source files — never modified
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
├── processed/                    # Task 1 output (generated)
└── index/                        # Task 2 output (generated)
```

Original sources: Municode (LDC Title 25, Drainage Criteria Manual,
Transportation Criteria Manual) and data.austintexas.gov — full provenance,
URLs, and known limitations are recorded in `processed/source_manifest.json`
after the first preprocessing run.

## Regenerate everything

```bash
python -m src.preprocessing.run_all        # -> data/processed/
python -m src.rag.indexer                  # -> data/index/ + chunk/section JSON
python -m pytest tests/                    # correctness tests (45)
python -m evaluation.retrieval.run_benchmark   # RAG metrics -> reports/
python -m evaluation.tools.run_latency         # tool latency -> reports/
```
