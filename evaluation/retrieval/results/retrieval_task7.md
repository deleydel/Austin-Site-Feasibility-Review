# Retrieval Quality - Task 7 held-out set

22 questions, k=5, hybrid retrieval with the measured-best configuration (no BGE query instruction). Gold sections are disjoint from Task 2's benchmark.

| metric | value |
| --- | --- |
| Hit@1 | 0.955 |
| Hit@5 | 0.955 |
| Recall@5 | 0.939 |
| MRR | 0.955 |
| median latency (ms) | 74.9 |
| judged relevance, precision@5 | 80.0% (88/110) |

## Relevance judge calibration

The judge is measured before its verdicts are used: gold sections should read as relevant, unrelated sections should not.

- sensitivity: 100.0% (8/8 gold passages called relevant)
- specificity: 75.0% (6/8 unrelated passages rejected)

## Hit@5 by question type

- realistic: 0.947
- citation: 1.0

## Sensitivity to question phrasing

These questions were written while reading the regulations, so their wording matches the source vocabulary. The same 19 questions were rescored in lay developer language against identical gold labels.

| phrasing | Hit@1 | Hit@5 | Recall@5 | MRR |
| --- | --- | --- | --- | --- |
| as written (code vocabulary) | 0.947 | 0.947 | 0.93 | 0.947 |
| lay paraphrase | 0.158 | 0.474 | 0.377 | 0.265 |

Questions the lay phrasing missed:

- **h03** Can I make my lot smaller and still build on it?
  - gold: [('LDC', '25-2-512')]
  - retrieved: [('LDC', '25-2-943'), ('LDC', '25-2-779'), ('LDC', '25-2-943'), ('LDC', '25-1-21'), ('LDC', '25-2-779')]
- **h04** How much can I dig out or build up the ground on my land?
  - gold: [('LDC', '25-8-341'), ('LDC', '25-8-342')]
  - retrieved: [('LDC', '2.7'), ('LDC', '25-2-754'), ('LDC', '2.1'), ('LDC', '25-8-301'), ('LDC', '25-2-1569')]
- **h06** Do apartment projects have to give up land for parks or pay something instead?
  - gold: [('LDC', '25-1-603'), ('LDC', '25-1-604'), ('LDC', '25-1-608')]
  - retrieved: [('LDC', '25-6-354'), ('LDC', '25-1-607'), ('LDC', '25-6-656'), ('LDC', '25-1-606'), ('LDC', '25-6-354')]
- **h07** Does my new building need somewhere for trucks to unload?
  - gold: [('LDC', '25-6-531'), ('LDC', '25-6-532')]
  - retrieved: [('TCM', '9.4.1'), ('TCM', '9.4.0'), ('LDC', '25-6-353'), ('LDC', '25-6-472'), ('TCM', '7.3.2')]
- **h08** There is a big old tree in the way. Can I take it down?
  - gold: [('LDC', '25-8-621'), ('LDC', '25-8-622')]
  - retrieved: [('LDC', '25-8-647'), ('LDC', '25-8-625'), ('LDC', '25-8-624'), ('LDC', '25-8-642'), ('LDC', '25-8-641')]
- **h09** There is boggy marshy ground on part of my land. Does that stop me building?
  - gold: [('LDC', '25-8-282')]
  - retrieved: [('LDC', '2.7'), ('LDC', '25-8-392'), ('LDC', '25-8-302'), ('LDC', '25-8-323'), ('LDC', '25-2-1126')]
- **h10** The water line is a long way from my property. What do I have to do to get hooked up?
  - gold: [('LDC', '25-9-33')]
  - retrieved: [('LDC', '25-9-412'), ('LDC', '25-9-32'), ('LDC', '25-9-93'), ('LDC', '25-9-344'), ('LDC', '25-9-96')]
- **h14** Will my project have to do anything about cutting down car trips?
  - gold: [('TCM', '10.2.1'), ('TCM', '10.3.2')]
  - retrieved: [('TCM', '10.3.4.2'), ('LDC', '25-6-114'), ('TCM', '10.3.5.4'), ('LDC', '25-6-667'), ('LDC', '25-6-113')]
- **h18** How many entrances can I have off the street?
  - gold: [('TCM', '7.6.1'), ('TCM', '7.6.2')]
  - retrieved: [('TCM', '7.6.6'), ('LDC', '2.4'), ('LDC', '25-6-174'), ('LDC', '25-6-591'), ('LDC', '2.2')]
- **h19** How many car parking spaces do I have to build?
  - gold: [('LDC', '25-6-471')]
  - retrieved: [('LDC', '25-6-475'), ('LDC', '25-2-1569'), ('LDC', '25-2-1007'), ('TCM', '9.3.4.3.1'), ('LDC', '25-2-1504')]

## Questions with no gold section in the top 5

- **h14** When is a Transportation Demand Management plan required for a development?
  - gold: [('TCM', '10.2.1'), ('TCM', '10.3.2')]
  - retrieved: [('TCM', '10.4.5'), ('TCM', '10.3.0'), ('TCM', '10.4.1.1.3'), ('TCM', '9.5.0'), ('TCM', '10.3.3')]

## Judged relevance per question

- **h01** precision@5 = 0.6 - Which developments are exempt from the site plan requirement?
  - [relevant] LDC 25-5-2 SITE PLAN EXEMPTIONS - The passage states that a site plan is not required for construction or alteration of four or fewer residential units under specific conditions.
  - [relevant] LDC 25-5-2 SITE PLAN EXEMPTIONS - The passage states rule (C) and part of rule (D), which provide exemptions from the site plan requirement.
  - [relevant] LDC 1.2 APPLICABILITY - The passage states that development in certain zoning districts (AG, AV, TN) and specific types of projects (UNO district, public educational facility, Robert Mueller Municipal Airport Redevelopment Plan) are exempt from the site plan requirement.
  - [not relevant] LDC 25-2-721 WATERFRONT OVERLAY (WO) COMBINING DISTRICT REGULATIONS - The passage does not mention exemptions from the site plan requirement.
  - [not relevant] LDC 25-5-1 SITE PLAN REQUIRED - The passage does not mention any exemptions from the site plan requirement.
- **h02** precision@5 = 0.8 - How long is a released site plan valid before it expires, and can the expiration date be extended?
  - [relevant] LDC 25-5-63 EXTENSION OF RELEASED SITE PLAN BY THE LAND USE COMMISSION - The passage states that an extension of the expiration date can be granted under certain conditions and provides procedures for requesting and approving such extensions.
  - [relevant] LDC 25-5-82 EXPIRATION OF A SITE PLAN APPROVED BEFORE JANUARY 1, 1988 - The passage states that a site plan approved before January 1, 1988 expires except in certain circumstances described in Subsections (C) and (D), which provide conditions under which the expiration date can be extended.
  - [not relevant] LDC 25-8-517 EXPIRATION OF PRIOR APPROVALS - The passage does not state how long a released site plan is valid or if its expiration date can be extended.
  - [relevant] LDC 25-5-62 EXTENSION OF RELEASED SITE PLAN BY DIRECTOR - The passage states that the director may extend the expiration date of a released administrative site plan one time for a period of one year if certain conditions are met.
  - [relevant] LDC 25-5-81 SITE PLAN EXPIRATION - The passage states that a site plan expires three years after its approval and provides conditions under which the expiration date can be extended.
- **h03** precision@5 = 1.0 - Can a lot be reduced below the minimum lot size requirements, and what exceptions apply?
  - [relevant] LDC 25-2-512 LOT SIZE MINIMUM - The passage states an exception to the minimum lot size requirements in Subsection (B) that allows for reduced lot sizes under specific conditions.
  - [relevant] LDC 25-2-779 SMALL LOT SINGLE-FAMILY RESIDENTIAL USE - The passage states the minimum lot size requirements for small lot single-family residential use, which directly addresses the question of whether a lot can be reduced below the minimum lot size requirements.
  - [relevant] LDC 25-2-943 SUBSTANDARD LOT - The passage states that a substandard lot may be used for a single-family residential use if it complies with specific requirements.
  - [relevant] LDC 25-2-943 SUBSTANDARD LOT - The passage states a condition that applies to substandard lots aggregated with other property after August 6, 2007.
  - [relevant] LDC 25-2-779 SMALL LOT SINGLE-FAMILY RESIDENTIAL USE - The passage states the minimum lot size requirements and provides conditions under which a lot can be reduced below these sizes.
- **h04** precision@5 = 0.8 - What are the maximum cut and fill depths allowed when grading a development site?
  - [relevant] LDC 25-8-342 FILL REQUIREMENTS - The passage states that fill on a tract of land may not exceed four feet of depth in most cases, except for certain exceptions.
  - [relevant] LDC 25-8-341 CUT REQUIREMENTS - The passage states a rule regarding cut requirements in land development, which directly addresses the maximum cut and fill depths allowed.
  - [relevant] LDC 25-8-342 FILL REQUIREMENTS - The passage states that fill is limited to no more than eight feet in depth, which directly addresses the maximum cut and fill depths allowed when grading a development site.
  - [relevant] LDC 25-8-341 CUT REQUIREMENTS - The passage states the maximum cut depth allowed under specific conditions related to street or driveway construction.
  - [not relevant] LDC 25-8-301 CONSTRUCTION OF A ROADWAY OR DRIVEWAY - The passage does not mention cut and fill depths, but rather construction on slopes with gradients over 15 percent.
- **h05** precision@5 = 0.8 - What construction restrictions apply on slopes with a steep gradient?
  - [relevant] LDC 25-8-301 CONSTRUCTION OF A ROADWAY OR DRIVEWAY - The passage states a condition for constructing on slopes with gradients over 15 percent.
  - [relevant] LDC 25-8-302 CONSTRUCTION OF A BUILDING OR PARKING AREA - The passage states specific construction restrictions for slopes with gradients of more than 15 percent and provides conditions under which construction may be allowed on steeper slopes.
  - [relevant] LDC 25-2-1123 CONSTRUCTION ON SLOPES - The passage provides specific construction restrictions for slopes with a steep gradient, including requirements for pier and beam techniques, vertical wall extensions, and terracing.
  - [relevant] LDC 25-8-303 SUBDIVISION NOTES - The passage states specific requirements for single-family residential lots on slopes with gradients over 15 percent.
  - [not relevant] LDC 25-8-304 APPLICABILITY - The passage does not mention construction restrictions on slopes with a steep gradient, but rather specifies an exception to its applicability.
- **h06** precision@5 = 1.0 - What parkland dedication or fee is required for a multi-family development?
  - [relevant] LDC 25-1-603 MULTI-FAMILY DEDICATION OF PARKLAND - The passage states that for a development application proposing multi-family uses, the director may require the applicant to pay a parkland dedication fee under Section 25-1-608 (Multi-Family Parkland Dedication Fee).
  - [relevant] LDC 25-1-608 MULTI-FAMILY PARKLAND DEDICATION FEE - The passage states a formula for calculating the parkland dedication fee required for a multi-family development.
  - [relevant] LDC 25-1-609 FEE PAYMENT AND EXPENDITURE - The passage states that payment of a parkland dedication fee required under Section 25-1-608 (Multi-Family Parkland Dedication Fee) shall be paid prior to issuance of a certificate of occupancy.
  - [relevant] LDC 25-1-603 MULTI-FAMILY DEDICATION OF PARKLAND - The passage states a rule for calculating the required parkland dedication based on multi-family units and hotel/motel rooms.
  - [relevant] LDC 25-1-608 MULTI-FAMILY PARKLAND DEDICATION FEE - The passage provides a formula for calculating the parkland dedication fee required for multi-family development.
- **h07** precision@5 = 1.0 - When must a development provide an off-street loading facility?
  - [relevant] LDC 25-6-532 OFF-STREET LOADING STANDARDS - The passage states that a person must provide an off-street loading facility for each use in a building or on a site as prescribed in Appendix A (Tables of Off-Street Loading Requirements and Former Off-Street Parking Requirements).
  - [relevant] LDC 25-6-531 OFF-STREET LOADING FACILITY REQUIRED - The passage states that a person must provide an off-street loading facility for new buildings or additions/enlargements of existing uses.
  - [relevant] LDC 25-6-561 APPLICABLE REGULATIONS; GENERAL MAINTENANCE - The passage states that a parking and loading facility must be maintained free of refuse or debris and must be available for the off-street parking or loading use for which the facility is required.
  - [relevant] LDC 25-6-562 DRAINAGE; LIGHTING - The passage states that an area used for primary circulation, frequent idling of vehicle engines, or loading activity must be designed and located to minimize the effect on an adjoining property.
  - [relevant] LDC 25-6-472 PARKING FACILITY STANDARDS - The passage states that a parking facility must be maintained for the duration of the use or existence of the building requiring the facility.
- **h08** precision@5 = 1.0 - Is a permit required to remove a protected tree, and who may apply for one?
  - [relevant] LDC 25-8-621 PERMIT REQUIRED FOR REMOVAL OF PROTECTED TREES; EXCEPTIONS - The passage states that a permit is required to remove a protected tree except in certain circumstances.
  - [relevant] LDC 25-8-624 APPROVAL CRITERIA - The passage states that a permit may be required to remove a protected tree under specific conditions and provides criteria for approval.
  - [relevant] LDC 25-8-622 APPLICATION FOR REMOVAL - The passage states that a permit is required to remove a protected tree and specifies who may apply for one under different circumstances.
  - [relevant] LDC 25-8-625 ACTION ON APPLICATION - The passage states that an application to remove a tree not associated with a pending application is automatically granted if the Planning and Development Review Department does not take action before the applicable deadline.
  - [relevant] LDC 25-8-626 EFFECTIVE DATE AND EXPIRATION OF APPROVAL - The passage states that approval of an application to remove a protected tree is effective immediately and provides conditions under which the approval expires.
- **h09** precision@5 = 1.0 - What wetland protection requirements apply to a development site?
  - [relevant] LDC 25-8-282 WETLAND PROTECTION - The passage states a specific exemption for wetlands located within a certain area and provides general requirements for protection methods.
  - [relevant] LDC 25-2-1001 PROCEDURES - The passage states a rule (Subsection (B)) that governs wetland protection requirements.
  - [relevant] LDC 25-8-261 CRITICAL WATER QUALITY ZONE DEVELOPMENT - The passage states wetland protection requirements for development sites, including distance from shorelines and maintenance plans.
  - [relevant] DCM 1.2.4 Drainage System - The passage defines residential and commercial development, which are terms that apply to wetland protection requirements.
  - [relevant] LDC 25-8-604 DEVELOPMENT APPLICATION REQUIREMENTS - The passage states requirements for tree protection and mitigation in relation to wetland development, which addresses the question of what wetland protection requirements apply to a development site.
- **h10** precision@5 = 0.8 - When is a service extension request required to connect a property to City water or wastewater?
  - [relevant] LDC 25-9-33 SERVICE EXTENSION APPLICATION - The passage states that a service extension request is required to connect a property to City water or wastewater if an accessible main is more than 100 feet from the property's boundary.
  - [relevant] LDC 25-9-35 APPROVAL OF A SERVICE EXTENSION REQUEST - The passage states that city council approval of a service extension request is required for properties in certain zones.
  - [relevant] LDC 25-9-39 EXPIRATION OF SERVICE EXTENSION REQUEST APPROVAL - The passage states that a service extension request is required to connect a property to City water or wastewater within 180 days after its approval, and also mentions that for a project with a recorded plat, the service extension request does not expire.
  - [relevant] LDC 25-9-39 EXPIRATION OF SERVICE EXTENSION REQUEST APPROVAL - The passage states that a service extension request is required to connect a property to City water or wastewater if construction of the service extension has not begun before the second anniversary of its approval and has not been completed and accepted for operation and maintenance by the City within three years.
  - [not relevant] LDC 25-9-41 DEVELOPMENT COMPLIANCE - The passage does not state when a service extension request is required to connect a property to City water or wastewater.
- **h11** precision@5 = 0.6 - What must a wastewater report address?
  - [relevant] LDC 25-8-124 WASTEWATER REPORT - The passage addresses all five required elements of a wastewater report as stated in the question.
  - [not relevant] LDC 25-9-95 TAP PERMIT NOT TRANSFERABLE - The passage discusses tap permits and their transferability, but does not address what a wastewater report must cover.
  - [not relevant] LDC 25-9-33 SERVICE EXTENSION APPLICATION - The passage does not address what a wastewater report must address, it discusses requirements for service extension applications and annexation.
  - [relevant] LDC 25-9-93 APPLICATION FOR TAP PERMIT; FEES; CAPACITY - The passage addresses what information must be included in an application for a tap permit.
  - [relevant] LDC 25-9-386 APPROVAL REQUIRED FOR SYSTEM DESIGN AND OPERATION - The passage mentions 'drawings of the final installed onsite reclaimed water system' which addresses what a wastewater report must address.
- **h12** precision@5 = 1.0 - Must a property owner dedicate drainage easements or rights-of-way when developing?
  - [relevant] LDC 25-7-152 DEDICATION OF EASEMENTS AND RIGHTS-OF-WAY - The passage states rule (A) that requires property owners to dedicate an easement or right-of-way for drainage facilities.
  - [relevant] LDC 25-7-152 DEDICATION OF EASEMENTS AND RIGHTS-OF-WAY - The passage defines conditions under which easements or rights-of-way are exempt from dedication.
  - [relevant] LDC 25-7-151 STORMWATER CONVEYANCE AND DRAINAGE FACILITIES - The passage states that the owner proposing to develop the property includes the responsibility to dedicate or obtain the dedication of any right-of-way or easement necessary to accommodate the required construction or improvement of the storm drainage facility.
  - [relevant] DCM 1.2.4 Drainage System - The passage states that drainage or drainage access easements are required per LDC 25-7-151 and 25-7-152, which implies that a property owner must dedicate such easements when developing.
  - [relevant] LDC 25-7-31 REQUIREMENT FOR DRAINAGE STUDIES - The passage states that for all other applications, the director may require a drainage study at the owner's expense and as a condition for development application approval.
- **h13** precision@5 = 0.8 - What does the city consider when deciding whether to approve a driveway approach construction permit?
  - [relevant] LDC 25-6-263 CONSTRUCTION PERMIT FOR DRIVEWAY APPROACH - The passage states part of the answer by listing specific factors that the city manager shall consider when determining the effect of a proposed driveway.
  - [relevant] LDC 25-6-263 CONSTRUCTION PERMIT FOR DRIVEWAY APPROACH - The passage states that the city manager must approve the construction of a type 2 driveway approach for angle or head-in parking requiring pedestrian way maneuverability.
  - [relevant] LDC 25-6-264 DRIVEWAY APPROACH DESIGN - The passage states that the design of a driveway approach must comply with an approved administrative site plan or be approved by the city manager.
  - [not relevant] TCM 7.7.0 DRIVEWAY PERMITTING - The passage does not state what the city considers when deciding whether to approve a driveway approach construction permit, it only mentions that a right-of-way construction permit must be granted for the driveway approach to be built.
  - [relevant] LDC 25-6-295 REMOVING EXISTING CURB OPENINGS OR DRIVEWAY APPROACHES - The passage states conditions and requirements for constructing a new driveway approach, which are factors the city would consider when deciding whether to approve such a permit.
- **h14** precision@5 = 0.6 - When is a Transportation Demand Management plan required for a development?
  - [relevant] TCM 10.4.5 PROPORTIONALITY OF TRANSPORTATION IMPROVEMENTS - The passage states that a Transportation Demand Management plan is required to reduce demand by a percentage, which implies it is a condition for roughly proportionate transportation improvements.
  - [not relevant] TCM 10.3.0 TRANSPORTATION DEMAND MANAGEMENT - The passage defines Transportation Demand Management (TDM) but does not specify when it is required for a development.
  - [relevant] TCM 10.4.1.1.3 Trip Generation - The passage states that a TDM plan is required for a development when a zoning change is requested, which implies a condition under which a TDM plan is necessary.
  - [relevant] TCM 9.5.0 SHARED-USE PARKING - The passage states that a TDM plan is required for site development and provides an exception to this rule.
  - [not relevant] TCM 10.3.3 TDM ADMINISTRATIVE GUIDELINES - The passage does not mention any specific circumstances under which a Transportation Demand Management plan is required for a development.
- **h15** precision@5 = 0.8 - What are the location requirements for short-term and long-term bicycle parking?
  - [relevant] TCM 9.8.3 LONG TERM BICYCLE PARKING - The passage provides location requirements for long-term bicycle parking, which includes criteria such as proximity to building entryways and accessibility features.
  - [relevant] TCM 9.8.2 SHORT-TERM BICYCLE PARKING - The passage states location requirements for short-term bicycle parking, including proximity to building entrances and visibility from the lobby or windows.
  - [not relevant] TCM 9.8.0 BICYCLE PARKING - The passage does not mention specific location requirements for short-term and long-term bicycle parking.
  - [relevant] TCM 9.8.1 BIKE PARKING LOCATIONS - The passage states location requirements for short-term and long-term bicycle parking, including criteria such as space between rack locations, accessibility, and permissible locations.
  - [relevant] LDC 25-6-477 BICYCLE PARKING - The passage states location requirements for short-term and long-term bicycle parking in sections (E) and (H)
- **h16** precision@5 = 0.4 - How is the runoff curve number selected for the NRCS runoff calculation method?
  - [relevant] DCM 2.5.2 Natural Resources Conservation Service Runoff Curve Numbers - The passage defines the runoff curve number and its relationship to antecedent soil moisture conditions, which helps determine how it is selected for the NRCS runoff calculation method.
  - [relevant] DCM 2.1.0 GENERAL - The passage states that the NRCS curve number method shall be used for drainage areas larger than 100 acres.
  - [not relevant] DCM 2.5.0 THE NATURAL RESOURCES CONSERVATION SERVICE METHOD FOR CALCUL - The passage does not mention how the runoff curve number is selected for the NRCS runoff calculation method.
  - [not relevant] DCM 2.5.3 Time of Concentration - The passage does not mention how the runoff curve number is selected for the NRCS runoff calculation method.
  - [not relevant] DCM 2.5.2 Natural Resources Conservation Service Runoff Curve Numbers - The passage does not provide information on how to select the runoff curve number for the NRCS runoff calculation method.
- **h17** precision@5 = 0.8 - What safety criteria must a stormwater management pond meet?
  - [relevant] DCM 8.3.3 Safety Criteria for SWM Ponds - The passage states safety criteria for stormwater management ponds, including design requirements for spillways, outfalls, embankments, and appurtenant structures.
  - [relevant] DCM 8.3.3 Safety Criteria for SWM Ponds - The passage states rules for pipes discharging into public storm drain systems and outfalls into SWM ponds, which are conditions that must be met by a stormwater management pond.
  - [not relevant] DCM 8.3.1 General - The passage does not mention any safety criteria for stormwater management ponds.
  - [relevant] DCM 8.3.3 Safety Criteria for SWM Ponds - The passage states safety criteria for stormwater management ponds, specifically that any hydraulic structure with a height of 6 feet or more must be designed to safely pass the minimum design flood hydrograph expressed as a percentage of the probable maximum flood.
  - [relevant] DCM 8.3.2 Performance Criteria for SWM Ponds - The passage states that stormwater management ponds must be designed to reduce post-development peak rates of discharge to existing pre-development peak rates of discharge for certain storm events.
- **h18** precision@5 = 0.6 - How many driveways is a site allowed based on its street frontage?
  - [relevant] TCM 7.6.1 PROPERTY FRONTAGE DRIVEWAY REQUIREMENTS - The passage states the allowed number of driveways based on property frontage available.
  - [relevant] TCM 7.6.1.1 Multi-Unit Residential Development accessing Minor Drives on - The passage states a specific rule for driveways on lots with less than 300 feet of street frontage and at least two dwelling units proposed.
  - [relevant] TCM 7.6.1.1 Multi-Unit Residential Development accessing Minor Drives on - The passage states the criteria for allowing three driveways on a corner lot fronting a Level 1 street.
  - [not relevant] TCM 7.6.2 DRIVEWAY PLACEMENT - The passage does not mention the number of driveways allowed based on street frontage.
  - [not relevant] TCM 7.6.2 DRIVEWAY PLACEMENT - The passage does not mention the number of driveways allowed based on street frontage.
- **h19** precision@5 = 0.4 - Is off-street motor vehicle parking required for a new development in Austin?
  - [relevant] LDC 25-6-471 OFF-STREET PARKING - The passage states that off-street motor vehicle parking is not required except in Subsection (B), which requires a minimum of one on-site accessible space.
  - [not relevant] LDC APPENDIX A. TABLES OF OFF-STREET LOADING REQUIREMENTS AND FORMER OFF-STREET PARKING REQUIREMENTS [preamble]  - The passage does not mention off-street motor vehicle parking at all, it only discusses on-site consumption requirements and loading requirements for various activities.
  - [not relevant] LDC 25-6-591 PARKING PROVISIONS FOR DEVELOPMENT IN THE CENTRAL BUSINESS D - The passage does not address the specific requirement for off-street motor vehicle parking in Austin.
  - [not relevant] LDC APPENDIX A. TABLES OF OFF-STREET LOADING REQUIREMENTS AND FORMER OFF-STREET PARKING REQUIREMENTS [preamble]  - The passage does not mention off-street motor vehicle parking for any use classification.
  - [relevant] LDC 25-6-471 OFF-STREET PARKING - The passage states that an accessible space parking requirement applies to sites with more than one use or for adjacent sites served by a common parking facility.
- **h20** precision@5 = 1.0 - What does LDC section 25-5-81 provide?
  - [relevant] LDC 25-5-81 SITE PLAN EXPIRATION - The passage states the expiration date of a site plan and provides conditions under which it does not expire.
  - [relevant] TCM 9.6.0 CALCULATION OF PARKING REQUIREMENTS - The passage states that LDC section 25-5-81 establishes parking reductions allowed for within the City of Austin.
  - [relevant] TCM Section 7 [preamble]  - The passage states that LDC section 25-5-81 provides minimum and desirable design criteria for safe and convenient access to abutting properties along streets and highways.
  - [relevant] TCM 10.4.4 DETERMINATION OF MITIGATIONS - The passage defines system improvements and their requirements, which addresses what LDC section 25-5-81 provides.
  - [relevant] TCM 10.4.5 PROPORTIONALITY OF TRANSPORTATION IMPROVEMENTS - The passage states that the City shall determine Rough Proportionality in accordance with state law and the LDC by comparing the required system infrastructure facilities' supply to the demand created by the new development.
- **h21** precision@5 = 0.8 - Transportation Criteria Manual 9.8.3 long term bicycle parking requirements
  - [relevant] TCM 9.8.3 LONG TERM BICYCLE PARKING - The passage provides specific requirements and conditions for long-term bicycle parking, including location criteria, accessibility standards, and design specifications that directly address the question about long term bicycle parking requirements.
  - [relevant] TCM 9.8.3 LONG TERM BICYCLE PARKING - The passage states rule 5, which specifies that bicycle parking must be located in a well-lit area with a minimum average illumination level of 200 lux.
  - [not relevant] TCM 9.8.0 BICYCLE PARKING - The passage does not mention long-term bicycle parking requirements, it provides general guidelines and standards for bicycle parking facilities.
  - [relevant] TCM 9.8.1 BIKE PARKING LOCATIONS - The passage states long-term bicycle parking requirements and provides specific criteria for bike rack placement, including spacing, accessibility, and location.
  - [relevant] TCM 9.8.4 BIKE PARKING EQUIPMENT AND INSTALLATION REQUIREMENTS - The passage states the requirement for bike racks to support bicycles at two points, including the frame of the bicycle.
- **h22** precision@5 = 1.0 - Drainage Criteria Manual section 8.3.3 safety criteria for stormwater management ponds
  - [relevant] DCM 8.3.3 Safety Criteria for SWM Ponds - The passage states freeboard requirements for stormwater management ponds, which directly relates to the safety criteria specified in section 8.3.3 of the Drainage Criteria Manual.
  - [relevant] DCM 8.3.3 Safety Criteria for SWM Ponds - The passage states a rule regarding the minimum diameter of pipes discharging into public storm drain systems, which is relevant to answering the question about safety criteria for stormwater management ponds.
  - [relevant] DCM 8.3.3 Safety Criteria for SWM Ponds - The passage states the safety criteria for stormwater management ponds, including earthen embankment design and hydraulic calculations, which are relevant to answering the question about drainage criteria manual section 8.3.3.
  - [relevant] DCM 8.3.3 Safety Criteria for SWM Ponds - The passage states a condition for SWM ponds that are considered dams, specifically regarding the vegetation and maintenance requirements.
  - [relevant] DCM 8.3.3 Safety Criteria for SWM Ponds - The passage states the condition that defines what constitutes a dam and must be designed to safely pass the minimum design flood hydrograph expressed as a percentage of the probable maximum flood (PMF).
