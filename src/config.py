"""Central paths and constants for Austin SiteFeasibility AI."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_REGULATIONS = DATA_DIR / "raw" / "regulations"
RAW_STRUCTURED = DATA_DIR / "raw" / "structured"
DATA_PROCESSED = DATA_DIR / "processed"
INDEX_DIR = DATA_DIR / "index"
# Generated evaluation/QA evidence lives next to whatever produces it.
# Deliberately NOT named "reports" — the system's end product is a
# feasibility *report*, and the two must not be confused.
EVAL_DIR = PROJECT_ROOT / "evaluation"
PREPROCESSING_RESULTS = EVAL_DIR / "preprocessing" / "results"
RETRIEVAL_RESULTS = EVAL_DIR / "retrieval" / "results"
TOOLS_RESULTS = EVAL_DIR / "tools" / "results"
# Downloadable feasibility reports produced by Task 6 export.
REPORT_OUTPUT_DIR = DATA_PROCESSED / "feasibility_reports"

# Raw source files
ZONING_CSV = RAW_STRUCTURED / "Zoning_By_Address_20260807.csv"
PERMITS_CSV = RAW_STRUCTURED / "IssuedConstructionPermits.csv"
SITE_PLANS_CSV = RAW_STRUCTURED / "Site_Plan_Cases_20260807.csv"
PLAN_REVIEW_CSV = RAW_STRUCTURED / "Plan_Review_Cases_20260807.csv"
WATERSHEDS_GEOJSON = RAW_STRUCTURED / "Watershed_Boundaries_20260807.geojson"
FLOODPLAIN_GEOJSON = RAW_STRUCTURED / "Greater_Austin_Fully_Developed_Floodplain_20260807.geojson"

LDC_DOCX = RAW_REGULATIONS / "TITLE_25.___LAND_DEVELOPMENT..docx"
DCM_DOCX = RAW_REGULATIONS / "DRAIANAGE.docx"
TCM_DOCX = RAW_REGULATIONS / "TRANSPORTATION.docx"

# Processed outputs
ZONING_PARQUET = DATA_PROCESSED / "zoning_by_address.parquet"
PERMITS_PARQUET = DATA_PROCESSED / "permits.parquet"
SITE_PLANS_PARQUET = DATA_PROCESSED / "site_plan_cases.parquet"
PLAN_REVIEW_PARQUET = DATA_PROCESSED / "plan_review_cases.parquet"
WATERSHEDS_PARQUET = DATA_PROCESSED / "watersheds.parquet"
FLOODPLAIN_PARQUET = DATA_PROCESSED / "floodplain.parquet"
REG_SECTIONS_JSON = DATA_PROCESSED / "regulatory_sections.json"
REG_CHUNKS_JSON = DATA_PROCESSED / "regulatory_chunks.json"
SOURCE_MANIFEST = DATA_PROCESSED / "source_manifest.json"

# Coordinate reference systems
CRS_WGS84 = "EPSG:4326"           # lat/lon storage
CRS_TX_CENTRAL_FT = "EPSG:2277"   # Texas Central State Plane (US survey feet) - all distance math

# Embedding / retrieval
EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"
# BGE model card recommends this instruction for short query -> passage retrieval;
# its benefit is measured in tests/test_retrieval_benchmark.py, not assumed.
BGE_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "
CHROMA_COLLECTION = "austin_regulations"

# Chunking (counts are BGE tokenizer tokens, breadcrumb included)
CHUNK_TARGET_TOKENS = 420
CHUNK_MAX_TOKENS = 450
CHUNK_OVERLAP_TOKENS = 64

# Source documents metadata (approved source list feed)
SOURCE_DOCS = {
    "LDC": {
        "name": "Austin Land Development Code (Title 25)",
        "short": "LDC",
        "url": "https://library.municode.com/tx/austin/codes/land_development_code",
    },
    "DCM": {
        "name": "Austin Drainage Criteria Manual",
        "short": "DCM",
        "url": "https://library.municode.com/tx/austin/codes/drainage_criteria_manual",
    },
    "TCM": {
        "name": "Austin Transportation Criteria Manual",
        "short": "TCM",
        "url": "https://library.municode.com/tx/austin/codes/transportation_criteria_manual",
    },
}
