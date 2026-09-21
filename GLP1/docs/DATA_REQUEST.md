# GLP-1 Adherence Analytics â€” Data Request

> **Purpose:** This document specifies the patient-level data elements required to run the GLP-1 Adherence Analytics platform. It is intended to be shared with data centers, health systems, pharmacy benefit managers (PBMs), and payer claims sources when requesting a live data extract.
>
> **Do not share:** Model outputs, SHAP scores, segment assignments, or any derived analytics â€” those are generated internally once the raw data is received.
>
> **Patient population in scope:** Adults (18+) who have been prescribed a GLP-1 receptor agonist for weight management and/or Type 2 diabetes management, with at least one fill on record.

---

## Summary of Required Data Elements

| # | Category | Source System | Fields Required |
|---|---|---|---|
| 1 | Patient Demographics | EHR / Registry | 4 fields |
| 2 | Laboratory Results | EHR / Lab | 2 fields |
| 3 | Diagnoses & Comorbidities | EHR / Claims | 4 fields |
| 4 | Prescription & Drug Details | Pharmacy / PBM | 5 fields |
| 5 | Refill & Adherence History | Pharmacy / PBM | 4 fields |
| 6 | Financial & Insurance | Claims / PBM | 4 fields |
| 7 | Side Effect Experience | EHR / Patient-reported | 3 fields |
| 8 | Pharmacy & Provider System | Pharmacy | 4 fields |

**Total: 30 data elements across 8 categories.**

---

## Category 1 â€” Patient Demographics

**Source system:** Electronic Health Record (EHR) or patient registry  
**Granularity:** One row per patient

| Field Name | Data Type | Accepted Values / Format | Purpose |
|---|---|---|---|
| `patient_id` | String | Any de-identified unique ID (UUID, MRN hash, etc.) | Links all records for a single patient across data sources |
| `date_of_birth` OR `age_at_index` | Date / Integer | `YYYY-MM-DD` or age in whole years | Used to compute age at index date; age range in scope is 18â€“80 |
| `sex` | String or Integer | `"M"` / `"F"` or `0` / `1` | Demographic feature used in dropout risk model |
| `height_cm` AND `weight_kg` OR `bmi` | Float | BMI range expected: 18.5â€“70 | Body Mass Index; if BMI is pre-computed by the source system, send that directly |

---

## Category 2 â€” Laboratory Results

**Source system:** EHR lab module, lab information system (LIS)  
**Granularity:** Most recent result within the 12 months prior to index date (GLP-1 prescription start)

| Field Name | Data Type | Accepted Values / Format | Purpose |
|---|---|---|---|
| `hba1c_value` | Float | Percentage (e.g., `6.8`); expected range 3.9â€“17.1 | Glycemic control at baseline; primary clinical input to the dropout risk model and downstream cost projections |
| `hba1c_test_date` | Date | `YYYY-MM-DD` | Used to confirm the result falls within the lookback window |

> **Note:** If multiple HbA1c results exist, send the one closest to and before the index date. If no result exists within 12 months, flag the record â€” the patient may still be included with imputation.

---

## Category 3 â€” Diagnoses & Comorbidities

**Source system:** EHR problem list, claims diagnosis codes (ICD-10-CM)  
**Granularity:** One row per patient; active diagnoses at or before index date

| Field Name | Data Type | Accepted Values / Format | Purpose |
|---|---|---|---|
| `has_dyslipidemia` | Binary | `1` = diagnosed, `0` = no record. ICD-10 codes: E78.x (any lipid disorder) | Comorbidity flag used in risk model; dyslipidemia often co-occurs with GLP-1 indication |
| `has_dysglycemia` | Binary | `1` = diagnosed, `0` = no record. ICD-10 codes: E11.x (T2D), R73.x (prediabetes/impaired glucose), E10.x (T1D â€” exclude if population scope is T2D only) | Confirms diabetes/pre-diabetes status; central to cost-of-inaction projections |
| `comorbidity_count` | Integer | Count of distinct active chronic conditions; expected range 0â€“2+ (e.g., count of conditions from: hypertension I10, CKD N18.x, HF I50.x, ASCVD I25.x, obesity E66.x, OSA G47.3x) | Comorbidity burden; higher scores correlate with greater dropout consequences |
| `active_icd10_codes` | String (list) | Pipe-separated or array of ICD-10-CM codes, e.g., `"E11.9|I10|E78.5"` | Allows us to independently verify and compute comorbidity score if preferred; also used in Markov state assignment for downstream cost model |

---

## Category 4 â€” Prescription & Drug Details

**Source system:** Pharmacy system, PBM claims, e-prescribing platform  
**Granularity:** One row per patient per GLP-1 prescription episode (index prescription only if single episode)

| Field Name | Data Type | Accepted Values / Format | Purpose |
|---|---|---|---|
| `drug_name` OR `ndc_code` | String | Drug name: `SEMAGLUTIDE`, `TIRZEPATIDE`, `LIRAGLUTIDE`, `DULAGLUTIDE`. NDC code also accepted and preferred if available | Identifies which GLP-1 molecule was prescribed; different molecules have different side-effect profiles affecting dropout |
| `drug_generation` | Integer | `1` = first-generation (liraglutide, dulaglutide), `2` = second-generation (semaglutide), `3` = third-generation (tirzepatide). If sending NDC code this will be derived by us | Newer-generation drugs have improved tolerability and efficacy; this is a direct model feature |
| `index_prescription_date` | Date | `YYYY-MM-DD` | Defines the start of the 180-day follow-up observation window |
| `prescribed_dose` | Float | Dose in mg or mg/week (e.g., `0.5`, `1.0`, `2.4`) | Used to contextualize side-effect experience relative to dose escalation |
| `route_of_administration` | String | `"subcutaneous"`, `"oral"` | Oral semaglutide has different adherence dynamics; important to distinguish from injectable forms |

---

## Category 5 â€” Refill & Adherence History

**Source system:** Pharmacy dispensing records, PBM claims  
**Granularity:** One row per fill event for each patient, covering the 180-day window from index date. Send all fill events, not just the first.

| Field Name | Data Type | Accepted Values / Format | Purpose |
|---|---|---|---|
| `fill_date` | Date | `YYYY-MM-DD` | Used to compute time-to-dropout (first gap in therapy > 30 days = dropout event) and Proportion of Days Covered (PDC) |
| `days_supply` | Integer | Number of days the dispensed quantity covers (typically 28, 30, or 90) | Combined with fill dates to identify coverage gaps and compute PDC/adherence |
| `quantity_dispensed` | Float | Number of units dispensed (pens, tablets, etc.) | Cross-validation of days_supply |
| `is_last_fill_in_window` | Binary | `1` if no further fills were recorded within the 180-day window, `0` otherwise. If not pre-computed, we will derive this from fill dates. | Used as the dropout event flag; patients with no fill in the final 60 days of the window are classified as dropout |

> **Alternative accepted format:** If sending one row per patient rather than one row per fill, send `total_fills_180d` (integer), `first_fill_date`, `last_fill_date`, and `pdc_ratio` (float 0â€“1) instead.

---

## Category 6 â€” Financial & Insurance

**Source system:** PBM claims, insurance eligibility files, patient financial records  
**Granularity:** One row per patient; average over the observation window if values vary month to month

| Field Name | Data Type | Accepted Values / Format | Purpose |
|---|---|---|---|
| `avg_oop_cost_per_fill` | Float | USD, average out-of-pocket copay or coinsurance paid per GLP-1 fill (e.g., `21.50`). Expected range $2â€“$425. | Direct measure of financial barrier to adherence; one of the strongest dropout predictors in the model |
| `insurance_type` | String | `"commercial"`, `"medicare"`, `"medicaid"`, `"uninsured"`, `"other"` | Used to contextualize OOP cost and map to payer ROI scenario |
| `annual_household_income` OR `income_poverty_ratio` | Float | Annual income in USD, or ratio of household income to Federal Poverty Level (FPL). Income-to-poverty ratio is preferred (e.g., `2.5` = 250% FPL). | Used to compute income-to-drug-cost pressure ratio; a patient paying $400/month on $30K income has very different risk than one on $150K |
| `prior_auth_denied` | Binary | `1` = at least one prior authorization denial for the GLP-1 during the observation window, `0` = no denial | Access barrier indicator; denials are a strong predictor of therapy interruption |

> **How `income_cost_pressure` is computed internally:** `(avg_oop_cost_per_fill Ã— 12) / annual_household_income Ã— 100`. The higher the ratio, the greater the financial burden. If you cannot provide income, send `insurance_type` and `avg_oop_cost_per_fill` at minimum.

---

## Category 7 â€” Side Effect Experience

**Source system:** EHR clinical notes, patient-reported outcome (PRO) tools, adverse event reports  
**Granularity:** One row per patient; summarized over the observation window

| Field Name | Data Type | Accepted Values / Format | Purpose |
|---|---|---|---|
| `gi_adverse_events_count` | Integer | Number of documented GI adverse event encounters (nausea, vomiting, diarrhea, constipation) during the observation window. `0` if none. | GI side effects are the primary driver of early GLP-1 dropout; higher counts indicate more bio friction |
| `injection_site_reactions` | Binary | `1` = at least one documented injection site reaction, `0` = none. Only relevant for injectable forms. | Secondary side-effect burden indicator |
| `dose_reduction_flag` | Binary | `1` = dose was reduced or escalation was paused due to side effects, `0` = no reduction | Strong signal of intolerance; patients who need dose reductions are at elevated dropout risk |

> **How `bio_friction` is computed internally:** A normalized score (0â€“1) derived from the three fields above, weighted by clinical literature on dropout contribution. If none of these fields are available, bio friction will be imputed from the cluster's mean. Please provide at least `gi_adverse_events_count`.

---

## Category 8 â€” Pharmacy & Provider System Reliability

**Source system:** Pharmacy dispensing system, provider scheduling system, PBM  
**Granularity:** One row per patient; summarized over the observation window

| Field Name | Data Type | Accepted Values / Format | Purpose |
|---|---|---|---|
| `days_to_first_fill` | Integer | Number of days between prescription date and first pharmacy fill | Delays in first fill predict early dropout; > 7 days is a risk signal |
| `pharmacy_type` | String | `"retail"`, `"mail_order"`, `"specialty"`, `"hospital_outpatient"` | Mail-order and specialty pharmacy are associated with better refill continuity for specialty drugs |
| `pharmacy_switches_count` | Integer | Number of times the patient changed dispensing pharmacy during the observation window | Pharmacy instability is a friction indicator; `0` is ideal |
| `follow_up_visit_within_90d` | Binary | `1` = patient had a scheduled follow-up visit with prescribing provider within 90 days of index date, `0` = no follow-up recorded | Provider engagement is a strong adherence enabler; its absence predicts dropout |

> **How `system_refill_score` is computed internally:** A composite score derived from the four fields above. Higher scores indicate a more reliable dispensing and care environment. If these fields are unavailable, the score will be imputed from population averages.

---

## Data Format & Delivery Specifications

### Preferred Format

| Specification | Requirement |
|---|---|
| File format | CSV (UTF-8 encoded) or JSON. Parquet also accepted for large extracts (> 500K patients). |
| Delivery method | Secure SFTP, Azure Blob Storage (private container), or AWS S3 (private bucket with IAM role). Do not email patient data. |
| Compression | GZIP preferred for CSV files over 50 MB |
| One row per | Patient (for summary fields). Separate file for fill events if sending longitudinal refill data. |
| Null handling | Use empty string `""` or `NULL` â€” do not use `0` to represent missing data unless the field is truly zero |
| Date format | `YYYY-MM-DD` throughout |

---

### Required vs. Optional Fields

| Priority | Fields | Impact if missing |
|---|---|---|
| **Required** | `patient_id`, `age`, `sex`, `bmi` or `height+weight`, `hba1c_value`, `assigned_molecule`, `index_prescription_date`, `fill_date` (or PDC), `avg_oop_cost_per_fill` | Model cannot run without these |
| **Strongly recommended** | `has_dyslipidemia`, `has_dysglycemia`, `comorbidity_count`, `drug_generation`, `income_poverty_ratio`, `gi_adverse_events_count`, `days_to_first_fill`, `follow_up_visit_within_90d` | Significant reduction in model accuracy if missing; will be imputed from population averages |
| **Optional (enhances accuracy)** | `active_icd10_codes`, `prescribed_dose`, `route_of_administration`, `prior_auth_denied`, `injection_site_reactions`, `dose_reduction_flag`, `pharmacy_type`, `pharmacy_switches_count` | Used for richer segmentation and downstream cost modelling; model still runs without these |

---

### Minimum Viable Extract (MVE)

If a full extract is not immediately possible, the following 10 fields are sufficient to run an initial cohort analysis:

1. `patient_id`
2. `age_at_index`
3. `sex`
4. `bmi`
5. `hba1c_value`
6. `assigned_molecule`
7. `index_prescription_date`
8. `avg_oop_cost_per_fill`
9. `fill_date` (one row per fill, or `pdc_ratio` + `last_fill_date`)
10. `comorbidity_count`

---

## What We Will Return

Once the data extract is received and processed, we will return the following analytics outputs per patient and per cohort segment â€” **none of these need to be provided by the data center:**

- Dropout risk score (0â€“1) per patient
- Patient segment assignment (1 of 4 behavioral clusters)
- Top 3 dropout risk drivers per patient (SHAP-explained)
- 5-year and 10-year downstream medical cost projections
- Metabolic rebound risk score post-dropout
- Payer ROI estimates under current, Medicare 2028, and post-generic pricing scenarios
- Population-level budget impact simulation

---

## Questions & Contact

For questions about this data request, field definitions, or delivery logistics, please contact the analytics team.

---

*Document version: 1.0 â€” 2026-07-29*
