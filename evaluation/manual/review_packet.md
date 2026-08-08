# Manual review packet

One entry per row of `manual_review_sheet.csv`. The regulation text is included so each item can be judged without looking anything up. What the automated evaluation decided is deliberately not shown.

## m01 - retrieval_relevance

**Question:** Must a property owner dedicate drainage easements or rights-of-way when developing?

**Evidence offered:** LDC 25-7-151 STORMWATER CONVEYANCE AND DRAINAGE FACILITIES

> (A) The owner or developer of property to be developed is responsible for the conveyance of all stormwater flowing through the property, including stormwater that: (1) is directed to the property by other developed property; or (2) naturally flows through the property because of the topography. (B) Future upstream development shall be accounted for as determined under the Drainage Criteria Manual. (C) If the construction or improvement of a storm drainage facility is required along a property line that is common to more than one property owner, the owner proposing to develop the property is, at the time the property is developed, responsible for each required facility on either side of the common property line. (D) The responsibility of the owner proposing to develop the property includes the responsibility to dedicate or obtain the dedication of any right-of-way or easement necessary to accommodate the required construction or improvement of the storm drainage facility. (E) If an owner of property proposes to develop only a portion of that property, a stormwater drainage facility to serve that portion of the property proposed for immediate development or use is required, unless th [...]

Allowed answers: `relevant / not_relevant`

Your verdict: ______

---

## m02 - retrieval_relevance

**Question:** What are the location requirements for short-term and long-term bicycle parking?

**Evidence offered:** TCM 9.8.2 SHORT-TERM BICYCLE PARKING

> Short-term bicycle parking serves people who park their bicycles for less than 4 hours in a publicly accessible and convenient location. This type of bicycle parking encourages shoppers, customers, patients, and other visitors to use bicycles as a mode of transportation by providing visible, convenient, and secure parking. Required short-term bicycle parking must meet the following standards: A. Shall be located at ground level within 50 ft. of the principal building entrance. 1. For sites with more than one primary building, the required bicycle parking shall be dispersed at principal entrances of all primary buildings. B. Shall be publicly accessible. C. Shall be visible from the lobby or windows of the building. D. Shall not compromise pedestrian access or mobility. E. If possible, protected from severe weather, including full sun or rain, by existing structures, such as overhangs or awnings, or by natural elements such as tree canopy. F. All public entrances must have at least 2 bicycle parking spaces unless this exceeds the total requirement from the Land Development Code. G. Short-term bicycle parking is typically placed within the right-of-way, near the curb or near building [...]

Allowed answers: `relevant / not_relevant`

Your verdict: ______

---

## m03 - retrieval_relevance

**Question:** Drainage Criteria Manual section 8.3.3 safety criteria for stormwater management ponds

**Evidence offered:** DCM 8.3.3 Safety Criteria for SWM Ponds

> All ponds shall meet or exceed all specified safety criteria. Use of these criteria shall in no way relieve the engineer of the responsibility for the adequacy and safety of all aspects of the design of the SWM pond. A. The spillway, outfall, embankment, and appurtenant structures shall be designed to safely pass the design storm hydrograph with the freeboard shown in the table below. All contributing on-site drainage areas, and off-site areas which are routed through the SWM pond, shall be assumed to be fully developed in order to properly size the spillway, outfall, embankment and appurtenant structures. Any orifice with a dimension smaller than or equal to 12 inches shall be assumed to be fully blocked in order to properly size the spillway, outfall, embankment and appurtenant structures. For all spillways (especially enclosed conduits), the ability to adequately convey the design flows must take into account any submergence of the outlet, any existing or potential obstructions in the system and the capacity of the downstream system. | DETENTION POND CLASS | DESIGN STORM EVENT | FREEBOARD ON TOP OF ENBANKMENT, FT | | --- | --- | --- | | On-site/Off-site | | | | Small (DA < 25 ac [...]

Allowed answers: `relevant / not_relevant`

Your verdict: ______

---

## m04 - retrieval_relevance

**Question:** What does LDC section 25-5-81 provide?

**Evidence offered:** TCM 10.4.5 PROPORTIONALITY OF TRANSPORTATION IMPROVEMENTS

> As a condition of approval for a new development, the City may require applicants to construct, dedicate or contribute towards transportation facilities. The City shall determine Rough Proportionality in accordance with state law and the LDC by comparing the required system infrastructure facilities' supply to the demand created by the new development. The LDC defines eligible improvements, in addition to right-of-way dedications, that are applicable to supply provided by a development. Any contributions toward a Street Impact Fee, as defined in the LDC, shall be applicable to supply provided by a development. Nexus standards for required improvements are identified in Section 10.4.4. Demand generated by the development shall be based on the unadjusted trips generated by a development per the TIA Determination in Section 10.2.1 multiplied by the average trip length in the City for each associated land use, resulting in vehicles of demand generated or VMT. Demand may be reduced by the percentage resulting from an approved TDM plan, as specified in Section 10.3.4.3. The supply and demand will be compared in dollars based on cost per VMT. Unless the supply calculated exceeds demand ge [...]

Allowed answers: `relevant / not_relevant`

Your verdict: ______

---

## m05 - retrieval_relevance

**Question:** Must a property owner dedicate drainage easements or rights-of-way when developing?

**Evidence offered:** LDC 25-7-31 REQUIREMENT FOR DRAINAGE STUDIES

> (A) For a preliminary plan or plat application to demonstrate that the proposed development would not result in an adverse impact to adjacent properties, the director may require the owner of real property to provide, at the owner's expense, a drainage study for the total area to be developed to demonstrate compliance with applicable drainage regulations. (B For all other applications, the director may require the owner of real property to provide, at the owner's expense and as a condition for development application approval, a drainage study for the total area to be ultimately developed. (C) The drainage study must be in accordance with the Drainage Criteria Manual. (D) If a drainage study is required under this section, the City may not accept for review a development application for any portion of the proposed development until the director has received the required drainage study.

Allowed answers: `relevant / not_relevant`

Your verdict: ______

---

## m06 - structured_data

**Claim:** watershed_lookup(Taylor Slough North at 30.32202,-97.76194) -> returned found/Taylor Slough North

**Evidence offered:** ground truth: Taylor Slough North

Allowed answers: `correct / incorrect`

Your verdict: ______

---

## m07 - structured_data

**Claim:** watershed_lookup(outside coverage at 31.14936,-96.69319) -> returned not_found

**Evidence offered:** this input has no valid answer; the tool must decline rather than answer. Expected: no watershed

Allowed answers: `correct / incorrect`

Your verdict: ______

---

## m08 - structured_data

**Claim:** nearby_searches(nearby_permits at 30.34167,-97.74981) -> returned 20 record(s), sorted by distance, all within 800 ft

**Evidence offered:** ground truth: 43 record(s) within 800 ft; the tool returns at most 20 (result cap), nearest first

Allowed answers: `correct / incorrect`

Your verdict: ______

---

## m09 - structured_data

**Claim:** geocode(505 BARTON SPRINGS RD) -> returned found/30.25750586

**Evidence offered:** ground truth: 30.25751,-97.74920

Allowed answers: `correct / incorrect`

Your verdict: ______

---

## m10 - structured_data

**Claim:** geocode(6117 JANEY DR) -> returned found/30.34167027

**Evidence offered:** ground truth: 30.34167,-97.74981

Allowed answers: `correct / incorrect`

Your verdict: ______

---

## m11 - citation_support

**Claim:** The project must comply with parking requirements, including adequate drives, aisles, and turning areas for access and usability.

**Evidence offered:** cited None - no cited section was topically related to the claim

Allowed answers: `supported / partially_supported / unsupported / uncited`

Your verdict: ______

---

## m12 - citation_support

**Claim:** Water and wastewater capacity are confirmed available for the proposed development.

**Evidence offered:** cited LDC 25-9-93 APPLICATION FOR TAP PERMIT; FEES; CAPACITY - The evidence states that water and wastewater capacity are confirmed available for the proposed development, as it explicitly mentions that the director of the Water and Wastewater Utility will not approve an application if existing facilities do not have actual capacity to serve the new connection.

> (A) An applicant for a tap permit must apply to the Water and Wastewater Utility on a form approved by the director of the Water and Wastewater Utility. (B) An application for a tap permit must include: (1) the name, title, address and telephone number of the applicant; (2) a description of the property for which the tap permit is to be issued; (3) documentation demonstrating that the property that is the subject of the tap permit application is: (a) a legal lot under state law and local subdivision requirements; and (b) located in: (i) the City's water and wastewater impact fee service area; or (ii) an area covered by an agreement for the wholesale sale of water between the City and another utility service provider that authorizes the City to issue tap permits under the agreement; (4) if applicable, documentation that the applicant's service extension has been approved; and (5) other information that the director of the Water and Wastewater Utility determines is necessary to process the application. (C) An application for a tap permit must be accompanied by the payment of: (1) the tap permit fee, connection fee, and capital recovery fee set by the council under separate ordinance; [...]

Allowed answers: `supported / partially_supported / unsupported / uncited`

Your verdict: ______

---

## m13 - citation_support

**Claim:** The site does not intersect with the floodplain, but there are nearby properties that have experienced flooding issues.

**Evidence offered:** cited None - no cited section was topically related to the claim

Allowed answers: `supported / partially_supported / unsupported / uncited`

Your verdict: ______

---

## m14 - citation_support

**Claim:** Floodplain regulations may require additional mitigation measures.

**Evidence offered:** cited LDC 25-2-563 MULTIFAMILY RESIDENCE MODERATE-HIGH DENSITY (MF-4) AND MULTIFAMILY RESIDENCE HIGH DENSITY (MF-5) DISTRICT REGULATIONS - claim and cited section share only 0% of the claim's content terms

> (A) This section applies in a multifamily residence moderate-high density (MF-4) or multifamily residence high density (MF-5) district. (B) The minimum site area for each dwelling unit is: (1) 800 square feet, for an efficiency dwelling unit; (2) 1,000 square feet, for a one bedroom dwelling unit; and (3) 1,200 square feet, for a dwelling unit with two or more bedrooms.

Allowed answers: `supported / partially_supported / unsupported / uncited`

Your verdict: ______

---

## m15 - citation_support

**Claim:** The proposed development is consistent with the SF-3-NP zoning designation.

**Evidence offered:** cited LDC 25-2-567 SPECIAL REQUIREMENTS FOR AFFORDABLE HOUSING IN CERTAIN MULTIFAMILY DISTRICTS - claim and cited section share only 17% of the claim's content terms

> (A) This section applies in a multifamily residence low density (MF-2) district, multifamily residence medium density (MF-3) district, multifamily residence moderate-high density (MF-4) district, or multifamily residence high density (MF-5) district on property that either has not been developed or that has been developed only with an agricultural use. (B) Except as provided in Subsection (C), a development may comply with multifamily residence highest density (MF-6) district site development regulations if the director of the Neighborhood Housing and Community Development Department certifies that the development complies with the City's S.M.A.R.T. Housing Program, and: (1) for a rental development, ten percent of the residential units in the development are reserved as affordable for a minimum of 40 years following the issuance of a certificate of occupancy for rental by a household earning not more that 60 percent of the median family income for the Austin metropolitan statistical area; or (2) for an owner-occupied development: (a) five percent of the residential units in the development are reserved as affordable for a minimum of 99 years following the issuance of a certificate [...]

Allowed answers: `supported / partially_supported / unsupported / uncited`

Your verdict: ______

---
