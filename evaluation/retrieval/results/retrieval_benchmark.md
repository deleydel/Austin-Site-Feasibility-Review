# Retrieval Sanity Benchmark (Task 2)

18 questions (realistic + direct-citation), gold labels
allow multiple acceptable sections. Metrics at k=5.

| configuration | Hit@1 | Hit@5 | Recall@5 | MRR | median latency (ms) |
| --- | --- | --- | --- | --- | --- |
| hybrid/instruction | 0.667 | 0.944 | 0.74 | 0.782 | 10.6 |
| dense/instruction | 0.667 | 0.889 | 0.647 | 0.759 | 4.7 |
| bm25/instruction | 0.278 | 0.667 | 0.467 | 0.454 | 2.1 |
| hybrid/no_instruction | 0.722 | 0.944 | 0.721 | 0.824 | 10.1 |
| dense/no_instruction | 0.5 | 0.889 | 0.647 | 0.678 | 3.9 |
| bm25/no_instruction | 0.278 | 0.667 | 0.467 | 0.454 | 2.3 |

## Hit@5 by question type (hybrid + no_instruction)

- realistic: 0.933
- citation: 1.0

## Misses (hybrid + no_instruction)

- **q01** What is the maximum impervious cover allowed in an SF-3 family residence zoning district?
  - gold: [('LDC', '25-2-492')]
  - got: [('LDC', '25-2-556'), ('LDC', '25-2-57'), ('LDC', '25-8-64'), ('LDC', '25-2-555'), ('LDC', '25-8-372')]

## Per-question retrieval detail (for manual relevance review)

- **q01** (realistic, MISS) What is the maximum impervious cover allowed in an SF-3 family residence zoning district?
  - LDC 25-2-556 (ADDITIONAL IMPERVIOUS COVER IN SINGLE-FA)
  - LDC 25-2-57 (FAMILY RESIDENCE (SF-3) DISTRICT DESIGNA)
  - LDC 25-8-64 (IMPERVIOUS COVER ASSUMPTIONS)
  - LDC 25-2-555 (FAMILY RESIDENCE (SF-3) DISTRICT REGULAT)
  - LDC 25-8-372 (UPLANDS ZONE)
- **q02** (realistic, gold at rank 1) How is impervious cover measured and what counts toward it?
  - LDC 25-8-64 (IMPERVIOUS COVER ASSUMPTIONS)
  - LDC 25-8-63 (IMPERVIOUS COVER CALCULATIONS)
  - LDC 25-1-23 (IMPERVIOUS COVER MEASUREMENT)
  - LDC 25-8-392 (UPLANDS ZONE)
  - LDC 25-8-366 (IMPERVIOUS COVER RESTRICTIONS FOR EDUCAT)
- **q03** (realistic, gold at rank 2) When is a traffic impact analysis required for a proposed development?
  - LDC 25-6-111 (TRAFFIC IMPACT ANALYSIS DESCRIBED)
  - LDC 25-6-113 (TRAFFIC IMPACT ANALYSIS REQUIRED)
  - LDC 25-6-101 (MITIGATION OF TRANSPORTATION IMPACTS)
  - LDC 25-6-23 (PROPORTIONALITY OF REQUIRED INFRASTRUCTU)
  - LDC 25-6-115 (STANDARDS FOR TRAFFIC IMPACT ANALYSIS)
- **q04** (realistic, gold at rank 1) What development is prohibited or restricted within the 25-year floodplain?
  - LDC 25-7-92 (ENCROACHMENT ON FLOODPLAIN PROHIBITED)
  - LDC 25-7-2 (DEFINITIONS)
  - LDC 25-7-96 (REQUIREMENTS IN THE 25-YEAR FLOODPLAIN)
  - LDC 25-8-452 (WATER QUALITY TRANSITION ZONE)
  - LDC 25-7-7 (DETERMINATION OF THE 25-YEAR FLOODPLAIN)
- **q05** (realistic, gold at rank 2) How is the 25-year floodplain determined and delineated?
  - LDC 25-7-2 (DEFINITIONS)
  - LDC 25-7-7 (DETERMINATION OF THE 25-YEAR FLOODPLAIN)
  - LDC 25-7-33 (FLOODPLAIN MAPS, DELINEATION, AND DEPICT)
  - LDC 25-7-96 (REQUIREMENTS IN THE 25-YEAR FLOODPLAIN)
  - DCM 1.2.6 (Floodplain Delineations)
- **q06** (realistic, gold at rank 1) How is required detention pond storage volume determined?
  - DCM 8.4.0 (DETENTION POND STORAGE DETERMINATION)
  - DCM 8.3.2 (Performance Criteria for SWM Ponds)
  - DCM 2.2.1 (Design Assumptions for Storm Runoff Anal)
  - DCM 1.2.2 (General)
  - DCM 8.3.3 (Safety Criteria for SWM Ponds)
- **q07** (realistic, gold at rank 1) What are the maintenance and equipment access requirements for detention basins?
  - DCM 8.5.0 (DETENTION BASIN MAINTENANCE AND EQUIPMEN)
  - LDC 25-7-153 (DETENTION BASIN MAINTENANCE AND INSPECTI)
  - DCM 1.2.4 (Drainage System)
  - DCM 1.2.2 (General)
  - DCM 2.2.1 (Design Assumptions for Storm Runoff Anal)
- **q08** (realistic, gold at rank 1) What development restrictions apply in a critical water quality zone?
  - LDC 25-8-261 (CRITICAL WATER QUALITY ZONE DEVELOPMENT)
  - LDC 25-8-452 (WATER QUALITY TRANSITION ZONE)
  - LDC 25-8-422 (WATER QUALITY TRANSITION ZONE)
  - LDC 25-8-482 (WATER QUALITY TRANSITION ZONE)
  - LDC 25-8-363 (BLASTING PROHIBITED)
- **q09** (realistic, gold at rank 1) What water quality control standards must proposed development meet?
  - LDC 25-8-213 (WATER QUALITY CONTROL STANDARDS)
  - LDC 25-8-212 (PREVIOUS WAIVERS AND SPECIAL EXCEPTIONS)
  - LDC 25-8-151 (INNOVATIVE MANAGEMENT PRACTICES)
  - LDC 25-8-211 (WATER QUALITY CONTROL REQUIREMENT)
  - LDC 25-8-231 (WATER QUALITY CONTROL MAINTENANCE AND IN)
- **q10** (realistic, gold at rank 2) What are the design requirements for a driveway approach serving a new development?
  - LDC 25-6-295 (REMOVING EXISTING CURB OPENINGS OR DRIVE)
  - LDC 25-6-264 (DRIVEWAY APPROACH DESIGN)
  - TCM 7.7.0 (DRIVEWAY PERMITTING)
  - TCM Section 7 [preamble] ()
  - LDC 25-6-2 (DRIVEWAY APPROACHES DESCRIBED)
- **q11** (realistic, gold at rank 1) When must sidewalks be installed as part of a site plan?
  - LDC 25-6-352 (SIDEWALK INSTALLATION WITH SITE PLANS)
  - LDC 25-6-351 (SIDEWALK INSTALLATION IN SUBDIVISIONS)
  - LDC 25-6-354 (PAYMENT INSTEAD OF SIDEWALK INSTALLATION)
  - LDC 25-6-353 (SIDEWALK INSTALLATION WITH BUILDING OR R)
  - LDC 2.2 (RELATIONSHIP OF BUILDINGS TO STREETS AND)
- **q12** (realistic, gold at rank 1) What compatibility height limits apply near residential property?
  - LDC 25-2-1061 (COMPATIBILITY HEIGHT LIMITS)
  - LDC 25-2-1062 (COMPATIBILITY BUFFERS AND SETBACKS)
  - LDC 25-2-652 (DENSITY BONUS 90 (DB90) COMBINING DISTRI)
  - LDC 25-8-700 (MINIMUM REQUIREMENTS FOR COMPATIBILITY B)
  - LDC 25-2-655 (DENSITY BONUS CREATIVE SPACES (DBCS) COM)
- **q13** (realistic, gold at rank 3) What are the requirements for off-street parking design and pedestrian paths from parking areas?
  - TCM 9.1.0 (GENERAL)
  - TCM 9.4.1 (OFF-STREET GENERAL LOADING REQUIREMENTS)
  - TCM 9.3.3.2 (Pedestrian Parking Paths General Criteri)
  - TCM 9.3.3.3 (Design Strategies)
  - LDC 2.2 (RELATIONSHIP OF BUILDINGS TO STREETS AND)
- **q14** (realistic, gold at rank 1) What stormwater runoff peak flow limits apply to new development discharges?
  - DCM 1.2.2 (General)
  - DCM 1.2.3 (Street Drainage)
  - DCM 8.1.0 (GENERAL)
  - LDC 25-7-67 (MODIFIED DRAINAGE STANDARDS FOR RESIDENT)
  - LDC 25-8-185 (OVERLAND FLOW)
- **q15** (realistic, gold at rank 1) What analysis is required to establish an erosion hazard zone?
  - LDC 25-7-32 (EROSION HAZARD ZONE ANALYSIS REQUIREMENT)
  - DCM Appendix E [preamble] ()
  - LDC 25-8-184 (ADDITIONAL EROSION AND SEDIMENTATION CON)
  - LDC 25-7-31 (REQUIREMENT FOR DRAINAGE STUDIES)
  - LDC 25-8-181 (EROSION AND SEDIMENTATION CONTROL)
- **q16** (citation, gold at rank 1) What does LDC section 25-8-92 establish?
  - LDC 25-8-92 (CRITICAL WATER QUALITY ZONES ESTABLISHED)
  - LDC ARTICLE 5: DEFINITIONS [preamble] ()
  - LDC 25-1-1002 (AREA PLAN)
  - LDC 25-9-164 (CONSTRUCTION OF ARTICLE)
  - LDC 25-2-1601 (APPLICABILITY)
- **q17** (citation, gold at rank 1) Definitions in section 25-1-21 of the Land Development Code
  - LDC 25-1-21 (DEFINITIONS)
  - LDC ARTICLE 5: DEFINITIONS [preamble] ()
  - LDC 1.4 (CONFLICTING PROVISIONS)
  - LDC 25-1-281 (APPLICABILITY)
  - LDC 25-2-766.01 (CONFLICTS; NONAPPLICABILITY)
- **q18** (citation, gold at rank 1) Drainage Criteria Manual 1.2.2 general drainage policy requirements
  - DCM 1.2.2 (General)
  - DCM 1.1.0 (GENERAL)
  - DCM 1.2.0 (CITY OF AUSTIN DRAINAGE POLICY)
  - DCM 1.2.1 (Application)
  - DCM 1.2.4 (Drainage System)

Latency figures are measured on this machine; they are observations, not guarantees.
A cross-encoder reranker was intentionally NOT added; revisit only if these numbers show a meaningful gap.
This benchmark is an internal sanity check for Tasks 1-3; full-framework evaluation (groundedness, citation correctness, guardrails) is a separate workstream.
