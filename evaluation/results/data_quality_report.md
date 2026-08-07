# Data Quality Report (Task 1 preprocessing QA)

Preprocessing QA evidence for Tasks 1-3. Project-level evaluation
(groundedness, citation correctness, guardrails, report completeness)
is owned by the evaluation workstream and is out of scope here.

Deduplication rules applied:
- Zoning: exact (address, zoning) duplicates removed; addresses with
  multiple distinct zoning designations are KEPT and flagged
  `has_multiple_zoning` (returned as `multiple_records` by the lookup tool).
- Permits: exact duplicate rows removed; rows sharing a permit_number are
  collapsed only when identical across audit fields (status, dates,
  description, valuation, coordinates, work class); genuine variants are
  retained and flagged `duplicate_permit_number`.
- Plan review: VOID/test records retained with `exclude_from_search=True`.
- Site plan / plan review outputs contain only allow-listed fields;
  applicant, owner, and contact columns are removed.

### Zoning by Address

| metric | value |
| --- | --- |
| rows_in | 263326 |
| regex_fallback_parses | 16 |
| normalized_empty | 7 |
| exact_dup_address_zoning_removed | 15 |
| addresses_with_multiple_zoning | 8 |
| null_zoning | 0 |
| rows_out | 263311 |

### Issued Construction Permits

| metric | value |
| --- | --- |
| rows_in | 60395 |
| exact_duplicate_rows_removed | 0 |
| duplicate_permit_numbers_before_audit | 0 |
| dup_permit_rows_identical_on_audit_fields_removed | 0 |
| permit_numbers_retained_with_variants | 0 |
| rows_missing_coordinates | 0 |
| rows_out | 60395 |

### Site Plan Cases

| metric | value |
| --- | --- |
| rows_in | 23630 |
| columns_in | 65 |
| columns_dropped_by_allowlist | 24 |
| exact_duplicate_rows_removed | 0 |
| rows_missing_coordinates | 4389 |
| rows_out | 23630 |

### Plan Review Cases

| metric | value |
| --- | --- |
| rows_in | 160135 |
| columns_in | 61 |
| columns_dropped_by_allowlist | 33 |
| exact_duplicate_rows_removed | 0 |
| rows_missing_coordinates | 32 |
| rows_flagged_excluded | 1222 |
| rows_out | 160135 |

### Watershed Boundaries

| metric | value |
| --- | --- |
| features_in | 76 |
| invalid_geometries_repaired | 0 |
| features_out | 76 |
| crs_out | EPSG:2277 |

### Fully Developed Floodplain

| metric | value |
| --- | --- |
| features_in | 12039 |
| invalid_geometries_repaired | 3 |
| null_flood_zone | 0 |
| flood_zone_values | ['A', 'AE', 'AO Depth 1ft', 'AO Depth 2ft', 'AO Depth 3ft', 'City of Austin Fully Developed 100-Year Floodplain', 'City of Austin Fully Developed 25-Year Floodplain', 'City of Austin Master Plan 25-Year Floodplain', 'Shallow'] |
| features_out | 12039 |
| crs_out | EPSG:2277 |


Total preprocessing time: 21.7s
