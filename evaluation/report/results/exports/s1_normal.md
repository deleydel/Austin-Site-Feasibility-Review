# Preliminary Development Feasibility Report

Generated: 2026-08-09
Status: validated

## Project and Site Description

- Address: 1714 Madison Avenue, Austin, TX
- Proposed land use: Multifamily residential
- Development description: Proposed 40-unit multifamily residential development on an infill lot.
- Units: 40
- Site area (acres): 0.8

### Synthesis

This is a JSON response from an API, specifically a permit search API. It contains information about permits and plans submitted in the past.

Here's a breakdown of the structure:

* The top-level object has three properties:
	+ `permit`: an array of objects containing information about individual permits
	+ `note`: a string providing context or additional information about the permits
	+ `summary`: an object with summary statistics about the permits (number of permits, site plans, and plan reviews)
* The `permit` array contains objects with the following properties:
	+ `distance_ft`: the distance from the property line to the nearest point on the permit boundary
	+ `permit_number`: a unique identifier for the permit
	+ `case_type`: the type of case (e.g. "Plan Review", "Site Plan")
	+ `work_class`: the type of work being done (e.g. "Addition and Remodel", "Repair")
	+ `project_name`: a descriptive name for the project
	+ `folder_description`: a brief description of the permit boundary
	+ `status_current`: the current status of the permit (e.g. "Approved", "Expired")
* The `note` string provides additional context or information about the permits.
* The `summary` object contains summary statistics about the permits:
	+ `permit_count`: the total number of permits
	+ `site_plan_count`: the number of site plans submitted
	+ `plan_review_count`: the number of plan reviews submitted

Overall, this API provides a way to search for and retrieve information about past permits and plans in a given area.

## Sources Consulted

- **Austin Land Development Code, Title 25** — https://library.municode.com/tx/austin/codes/land_development_code
  - Limitation: Snapshot export; ordinances adopted after the export date are not reflected.
- **Austin Drainage Criteria Manual** — https://library.municode.com/tx/austin/codes/drainage_criteria_manual
  - Limitation: Partial manual; other DCM sections are out of scope for this system.
- **Austin Transportation Criteria Manual** — https://library.municode.com/tx/austin/codes/transportation_criteria_manual
  - Limitation: Partial manual; other TCM sections are out of scope for this system.
- **Zoning by Address** — https://data.austintexas.gov/ (search: Zoning by Address)
  - Limitation: Preliminary reported zoning only; not an official zoning determination. No coordinates; matching is by address string.
- **Issued Construction Permits** — https://data.austintexas.gov/Building-and-Development/Issued-Construction-Permits/3syk-w9eu
  - Limitation: Issued permits 2021+ only. Historical proximity context; not approval precedent.
- **Site Plan Cases** — https://data.austintexas.gov/ (search: Site Plan Cases)
  - Limitation: Some records lack coordinates. Applicant/owner contact fields removed during preprocessing (privacy).
- **Plan Review Cases** — https://data.austintexas.gov/ (search: Plan Review Cases)
  - Limitation: Contains VOID/test records (retained but flagged exclude_from_search). Contact fields removed (privacy).
- **Watershed Boundaries** — https://data.austintexas.gov/ (search: Watershed Boundaries)
  - Limitation: 76 named watersheds within the Austin planning area.
- **Greater Austin Fully Developed Floodplain** — https://data.austintexas.gov/ (search: Greater Austin Fully Developed Floodplain)
  - Limitation: City of Austin fully developed floodplain model (Atlas 14); not the FEMA effective floodplain. Preliminary screening only.

## Zoning and Land-Use Context

- Preliminary reported zoning: SF-3-NP (status: found)
- Preliminary Open Data zoning only; not an official determination.

Zoning context is preliminary. Designations are stated only when the lookup returns an exact single match.

Regulatory references for this section:
- LDC § 25-2-1534 DEVELOPMENT REQUIREMENTS
- LDC § 25-2-563 MULTIFAMILY RESIDENCE MODERATE-HIGH DENSITY (MF-4) AND MULTIFAMILY RESIDENCE HIGH DENSITY (MF-5) DISTRICT REGULATIONS
- LDC § 25-2-1523 DEVELOPMENT PLAN APPROVAL CRITERIA
- LDC § 25-2-771 SINGLE-FAMILY RESIDENTIAL USE IN A MULTIFAMILY DISTRICT
- LDC § 25-2-1532 RESIDENTIAL INFILL PERMITTED IN CERTAIN ZONING DISTRICTS

## Site-Plan Considerations

Site-plan applicability depends on proposed use, zoning, and project characteristics; confirm with Development Services. Citations below are limited to site-plan provisions (LDC Chapter 25-5) when available.

## Drainage, Flood, and Environmental Considerations

- Floodplain intersection: False
- Watershed: Shoal Creek

Regulatory references for this section:
- DCM § 1.2.2 General
- LDC § 25-7-66 SUPPLEMENTAL REQUIREMENTS FOR DEVELOPMENT APPLICATIONS IN CERTAIN PLANNING AREAS

## Transportation and Access Considerations

Regulatory references for this section:
- DCM § 1.2.2 General

## General Water and Wastewater Considerations

Regulatory language does not establish utility service availability or capacity. Verification with the appropriate utility authority is required.

Regulatory references for this section:
- LDC § 25-9-33 SERVICE EXTENSION APPLICATION
- LDC § 25-9-412 RECLAIMED WATER CONNECTION REQUIREMENTS
- LDC § 25-9-384 RECLAIMED WATER SERVICE APPLICATION
- LDC § 25-9-93 APPLICATION FOR TAP PERMIT; FEES; CAPACITY
- LDC § 25-9-31 APPLICABILITY

## Historical Permit and Case Context

Nearby permits and cases are historical context only. They are not approval precedent and do not indicate future permitting outcomes for the proposed development.

Summary: Permit count: 20, Site plan count: 0, Plan review count: 20

## Potential Constraints

- [potential constraint] zoning: Reported zoning is SF-3-NP, while the proposed land use is multifamily residential for the proposed 40-unit development. This combination presents a potential zoning/use conflict that requires verification against the applicable Austin Land Development Code requirements. No approval or prohibition determination is made here.

## Missing Information and Required Verification

- Verification required (zoning): Preliminary reported zoning was retrieved from Open Data and requires official verification.
- Verification required (historical_context): Nearby permits and cases are historical context only. They are not approval precedent and do not indicate future permitting outcomes for the proposed development.

## Source Citations

1. DCM — § 1.2.2 General (Section 1) | https://library.municode.com/tx/austin/codes/drainage_criteria_manual
2. LDC — § 25-7-66 SUPPLEMENTAL REQUIREMENTS FOR DEVELOPMENT APPLICATIONS IN CERTAIN PLANNING AREAS (Chapter 25-7) | https://library.municode.com/tx/austin/codes/land_development_code

## Preliminary-Review Disclaimer

This is a preliminary site-feasibility screening only. It is not an official zoning determination, code-compliance decision, development approval, or guarantee of utility service. Nearby permits and cases are historical context only and are not approval precedent. All findings require verification by qualified professionals and City of Austin authorities.
