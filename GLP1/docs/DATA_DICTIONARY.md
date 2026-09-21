# GLP-1 Adherence Analytics â€” Data Dictionary

> **Project:** GLP-1 Adherence Analytics Platform  
> **Stack:** FastAPI Â· MongoDB Atlas Â· React (Vite)  
> **Last updated:** 2026-07-29

---

## Table of Contents

1. [Segment Definitions](#1-segment-definitions)
2. [MongoDB Collections](#2-mongodb-collections)
3. [CSV Source Files](#3-csv-source-files)
4. [API Endpoints](#4-api-endpoints)
5. [Pydantic Response Schemas](#5-pydantic-response-schemas)
6. [Frontend Constants & API Client](#6-frontend-constants--api-client)
7. [Key Derived Metrics](#7-key-derived-metrics)

---

## 1. Segment Definitions

The ML model assigns every patient to one of four clusters. These cluster IDs are used as foreign keys across all collections and CSV files.

| Cluster ID | Full Label | Short Label | Color |
|---|---|---|---|
| 0 | Low Urgency Dropout Risk | Low Urgency Dropout | `#EF5350` (red) |
| 1 | Financial Barrier Dropout Risk | Financial Barrier Dropout | `#FF7043` (orange) |
| 2 | Low Friction Strong Adherer | Low Friction Adherer | `#43A047` (green) |
| 3 | Moderate Risk Moderate Adherer | Moderate Risk Adherer | `#1E88E5` (blue) |

---

## 2. MongoDB Collections

Database name: `glp1_analytics` (configurable via `MONGO_DB` env var).

All collections are populated by `Backend/scripts/migrate_csv_to_mongo.py`.

---

### 2.1 `patients`

**Source:** `GLP1_FINAL_WITH_SURVIVAL.csv` merged with `shap_patient_drivers.csv` on `patient_idx`  
**Indexes:** `patient_idx` (unique), `cluster`, `dropout_prob`, `assigned_molecule`  
**Row count:** ~7,566

| Field | Type | Description |
|---|---|---|
| `patient_idx` | int | Unique patient identifier (row index from source CSV) |
| `dropout_prob` | float | Model-predicted probability of dropout (0â€“1) |
| `prediction` | str | `"Dropout Risk"` if prob â‰¥ 0.5, else `"Likely Adherent"` |
| `cluster` | int | Segment assignment (0â€“3) |
| `segment` | str | Human-readable cluster label |
| `assigned_molecule` | str | GLP-1 drug: `SEMAGLUTIDE`, `TIRZEPATIDE`, `LIRAGLUTIDE`, `DULAGLUTIDE` |
| `avg_oop_cost` | float | Average annual out-of-pocket cost (USD) |
| `RIDAGEYR` | int | Patient age (years) |
| `BMXBMI` | float | Body Mass Index |
| `LBXGH` | float | HbA1c level (%) |
| `comorbidity_score` | int | Count of comorbid conditions |
| `bio_friction` | float | Side-effect burden intensity score |
| `income_cost_pressure` | float | Financial barrier metric (0â€“1) |
| `system_refill_score` | float | Pharmacy/provider reliability score (0â€“1) |
| `drug_generation` | int | `1` = older drug, `2` = newer drug |
| `is_adherent` | int | Actual adherence outcome: `1` = adherent, `0` = dropout |
| `event_occurred` | int | `1` if dropout event observed, `0` if censored |
| `time_to_dropout` | int | Days until dropout event or censoring |
| `driver_1` | str | Top SHAP feature name driving the prediction |
| `driver_1_direction` | str | `"increases dropout risk"` or `"reduces dropout risk"` |
| `driver_1_shap` | float | SHAP value for top driver |
| `driver_2` | str \| null | Second SHAP driver feature name |
| `driver_2_direction` | str \| null | Direction for driver 2 |
| `driver_2_shap` | float \| null | SHAP value for driver 2 |
| `driver_3` | str \| null | Third SHAP driver feature name |
| `driver_3_direction` | str \| null | Direction for driver 3 |
| `driver_3_shap` | float \| null | SHAP value for driver 3 |

---

### 2.2 `segment_profiles`

**Source:** Computed from `patients` collection during migration  
**Index:** `cluster` (unique)  
**Row count:** 4

| Field | Type | Description |
|---|---|---|
| `cluster` | int | Cluster ID (0â€“3) |
| `label` | str | Full cluster label |
| `short` | str | Short cluster label |
| `n` | int | Number of patients in segment |
| `adherence` | float | Proportion of adherent patients (0â€“1) |
| `age` | float | Mean patient age |
| `bmi` | float | Mean BMI |
| `hba1c` | float | Mean HbA1c |
| `oop_cost` | float | Mean annual out-of-pocket cost (USD) |
| `cost_pressure` | float | Mean income/cost pressure score |
| `bio_friction` | float | Mean bio-friction score |
| `refill_score` | float | Mean system refill score |
| `comorbidity` | float | Mean comorbidity score |
| `wasted_per_pt` | int | Annual wasted spend per dropout patient (USD) |
| `cost_per_hba1c` | int | Drug cost per 1-point HbA1c reduction (USD) |
| `cost_per_weight` | int | Drug cost per 1% weight loss (USD) |

---

### 2.3 `cost_effectiveness`

**Source:** `cost_effectiveness.csv` joined with `icer_by_segment.csv` (pivoted on comparator)  
**Index:** `cluster` (unique)  
**Row count:** 4

| Field | Type | Description |
|---|---|---|
| `cluster` | int | Cluster ID |
| `label` | str | Segment label |
| `segment` | str | Segment name |
| `n` | int | Patient count |
| `adherence_rate` | float | Proportion adherent |
| `annual_cost` | float | Mean annual drug cost (USD) |
| `avg_oop_cost` | float | Mean out-of-pocket cost (USD) |
| `weight_loss` | float | Mean weight loss (%) |
| `hba1c_reduction` | float | Mean HbA1c reduction (percentage points) |
| `cost_per_weight` | float | Cost per 1% weight reduction (USD) |
| `cost_per_hba1c` | float | Cost per 1-point HbA1c reduction (USD) |
| `wasted_spend_per_pt` | float | Annual wasted spend per dropout patient (USD) |
| `total_annual_spend` | float | Total annual population spend (USD) |
| `icer_insulin_weight` | float | ICER vs. insulin glargine, weight endpoint (USD/% weight) |
| `icer_insulin_hba1c` | float | ICER vs. insulin glargine, HbA1c endpoint (USD/1-pt HbA1c) |
| `icer_sglt2_weight` | float | ICER vs. SGLT2 inhibitor, weight endpoint |
| `icer_sglt2_hba1c` | float | ICER vs. SGLT2 inhibitor, HbA1c endpoint |

---

### 2.4 `survival_checkpoints`

**Source:** `survival_checkpoints.csv`  
**Index:** `cluster` (unique)  
**Row count:** 4

| Field | Type | Description |
|---|---|---|
| `cluster` | int | Cluster ID |
| `segment` | str | Segment label |
| `day30` | float | Kaplan-Meier survival probability at day 30 (0â€“1) |
| `day60` | float | Survival probability at day 60 |
| `day90` | float | Survival probability at day 90 |
| `day180` | float | Survival probability at day 180 |

---

### 2.5 `survival_curves`

**Source:** Computed via Kaplan-Meier fit on `patients` collection (requires `lifelines`)  
**Index:** `cluster` (unique)  
**Row count:** 4

| Field | Type | Description |
|---|---|---|
| `cluster` | int | Cluster ID |
| `label` | str | Segment label |
| `color` | str | Hex color string |
| `adherence` | float | Segment-level adherence rate |
| `data` | List[object] | Array of `{ day, survival }` points at days 0, 5, 10, â€¦ 180 |

---

### 2.6 `progression_cost`

**Source:** `progression_cost.csv` â€” Phase 1 of the Consequence Model (Markov projection)  
**Indexes:** `patient_idx` (unique), `cluster`  
**Row count:** ~7,566

| Field | Type | Description |
|---|---|---|
| `patient_idx` | int | Patient identifier |
| `cluster` | int | Cluster ID |
| `segment_short` | str | Short segment label |
| `lbxgh_baseline` | float | Baseline HbA1c at study entry |
| `bmxbmi_baseline` | float | Baseline BMI at study entry |
| `time_to_dropout_days` | float | Days until dropout or censoring |
| `event_occurred` | int | `1` if dropout event observed |
| `entry_state` | int | Initial Markov state: `0` = Controlled, `1` = Uncontrolled |
| `entry_state_name` | str | `"Controlled"` or `"Uncontrolled"` |
| `expected_downstream_cost_5yr` | float | Expected downstream medical cost over 5 years (USD) |
| `expected_downstream_cost_10yr` | float | Expected downstream medical cost over 10 years (USD) |
| `esrd_probability_5yr` | float | Probability of ESRD within 5 years |
| `death_probability_5yr` | float | Probability of death within 5 years |
| `cv_event_probability_5yr` | float | Probability of cardiovascular event within 5 years |
| `primary_cost_driver` | str | Dominant cost driver: `"ESRD"`, `"CV_event"`, or `"Uncontrolled_T2D"` |
| `cost_share_esrd_5yr` | float | Fraction of 5-yr cost attributable to ESRD |
| `cost_share_cv_5yr` | float | Fraction attributable to CV events |
| `cost_share_uncontrolled_t2d_5yr` | float | Fraction attributable to uncontrolled T2D |

---

### 2.7 `rebound_risk`

**Source:** `rebound_risk.csv` â€” Phase 2 of the Consequence Model (per-patient metabolic rebound)  
**Indexes:** `patient_idx` (unique), `cluster`  
**Row count:** ~7,566

| Field | Type | Description |
|---|---|---|
| `patient_idx` | int | Patient identifier |
| `cluster` | int | Cluster ID |
| `segment_short` | str | Short segment label |
| `assigned_molecule` | str | GLP-1 drug assigned |
| `lbxgh_baseline` | float | Baseline HbA1c |
| `bmxbmi_baseline` | float | Baseline BMI |
| `time_to_dropout_days` | float | Days to dropout |
| `dm_status_at_dropout` | str | Diabetes status at dropout: `"normal"`, `"prediabetes"`, `"t2d"` |
| `hba1c_at_dropout` | float | HbA1c at time of dropout |
| `bmi_at_dropout` | float | BMI at time of dropout |
| `expected_hba1c_6mo` | float | Projected HbA1c at 6 months post-dropout |
| `expected_hba1c_12mo` | float | Projected HbA1c at 12 months post-dropout |
| `expected_bmi_6mo` | float | Projected BMI at 6 months post-dropout |
| `expected_bmi_12mo` | float | Projected BMI at 12 months post-dropout |
| `p_new_t2d_12mo` | float \| null | Probability of new T2D diagnosis within 12 months (pre-DM patients only) |
| `p_uncontrolled_12mo` | float \| null | Probability of uncontrolled diabetes within 12 months |
| `months_to_t2d_threshold` | float \| null | Projected months until HbA1c crosses T2D diagnostic threshold |
| `rebound_severity_score` | float | Composite severity index (0â€“1) |

---

### 2.8 `rebound_trajectory`

**Source:** `rebound_trajectory.csv` â€” Phase 2, line-chart data for HbA1c/BMI rebound curves  
**Indexes:** `cluster`, `scenario`  
**Row count:** ~300 (4 clusters Ã— 3 scenarios Ã— ~25 months)

| Field | Type | Description |
|---|---|---|
| `cluster` | int | Cluster ID |
| `scenario` | str | Dropout timing scenario: `"early"`, `"median"`, `"late"` |
| `dropout_day` | float | Representative dropout day for this scenario |
| `month` | float | Month number post-dropout (0â€“24) |
| `avg_hba1c` | float | Mean HbA1c across patients in this cluster/scenario at this month |
| `avg_bmi` | float | Mean BMI at this month |
| `n_patients` | int | Number of patients in this scenario group |

---

### 2.9 `rebound_sensitivity`

**Source:** `rebound_sensitivity.csv` â€” Phase 2, summary table for sensitivity panel  
**Index:** `cluster`, `scenario` (unique compound)  
**Row count:** 12 (4 clusters Ã— 3 scenarios)

| Field | Type | Description |
|---|---|---|
| `cluster` | int | Cluster ID |
| `scenario` | str | `"early"`, `"median"`, or `"late"` |
| `dropout_day` | float | Median dropout day for this scenario |
| `n_patients` | int | Patients in this scenario group |
| `avg_hba1c_at_dropout` | float | Mean HbA1c at time of dropout |
| `avg_expected_hba1c_12mo` | float | Mean projected HbA1c at 12 months |
| `avg_severity_score` | float | Mean rebound severity score |
| `p_new_t2d_12mo_mean` | float \| null | Mean T2D incidence probability (pre-DM patients only) |
| `p_uncontrolled_12mo_mean` | float \| null | Mean uncontrolled diabetes probability |
| `n_pre_dm` | int | Count of pre-diabetic patients in group |
| `n_t2d` | int | Count of T2D patients in group |

---

### 2.10 `payer_roi`

**Source:** `payer_roi.csv` â€” Phase 3 of the Consequence Model (multi-scenario payer ROI)  
**Index:** `payer_type`, `cluster` (unique compound)  
**Row count:** 12 (4 clusters Ã— 3 payer scenarios)

| Field | Type | Description |
|---|---|---|
| `payer_type` | str | Pricing scenario: `"current"`, `"medicare_2028"`, `"post_generic"` |
| `cluster` | int | Cluster ID |
| `n_patients` | int | Patients in cluster |
| `adherence_probability` | float | Baseline adherence rate for cluster (Î±) |
| `avg_annual_drug_cost` | float | Mean annual net drug cost under this pricing scenario (USD) |
| `avg_time_to_dropout_days` | float | Mean days to dropout for this cluster |
| `downstream_dropout_{1â€“10}yr` | float | Per-patient downstream medical cost if dropout, at year N (USD) |
| `downstream_adherent_{1â€“10}yr` | float | Per-patient downstream medical cost if adherent, at year N (USD) |
| `expected_drug_cost_{1â€“10}yr` | float | Discounted cumulative drug cost per patient at year N (USD) |
| `gross_benefit_{1â€“10}yr` | float | Gross medical cost avoidance per patient at year N (USD) |
| `intervention_cost_{1â€“10}yr` | float | Program cost assumption at time of CSV generation (USD) |
| `net_benefit_{1â€“10}yr` | float | `gross_benefit âˆ’ drug_cost âˆ’ intervention_cost` at year N |
| `roi_{1â€“10}yr` | float | Drug economics ROI: `net_benefit / drug_cost` at year N |
| `break_even_adherence_rate` | float \| null | Minimum adherence rate at which ROI turns positive |
| `intervention_cost_threshold_5yr` | float | Max program cost that still yields positive 5-yr net benefit (USD) |
| `time_to_positive_roi_years` | float \| null | Interpolated year when drug-economics ROI crosses zero |

**Payer scenario drug cost assumptions:**

| `payer_type` | Drug cost basis | Approx. net annual cost |
|---|---|---|
| `current` | Commercial WAC Ã— (1 âˆ’ 0.35 rebate) | $5,850 â€“ $10,490 / yr (by cluster) |
| `medicare_2028` | Projected CMS negotiated price (~65% discount off WAC) | $3,150 â€“ $5,649 / yr |
| `post_generic` | Biosimilar/generic market entry | $900 â€“ $1,745 / yr |

---

### 2.11 `payer_roi_yearly`

**Source:** `payer_roi_yearly.csv` â€” Phase 3, annual ROI breakdown for trajectory charts  
**Index:** `payer_type`, `cluster`, `horizon_years` (unique compound)  
**Row count:** ~120 (4 clusters Ã— 10 years Ã— 3 payer types)

| Field | Type | Description |
|---|---|---|
| `cluster` | int | Cluster ID |
| `payer_type` | str | Pricing scenario |
| `horizon_years` | int | Year number (1â€“10) |
| `gross_benefit` | float | Gross benefit at this year (USD) |
| `expected_drug_cost` | float | Cumulative drug cost at this year (USD) |
| `intervention_cost` | float | Program cost at this year (USD) |
| `net_benefit` | float | Net benefit at this year (USD) |
| `roi` | float | Drug economics ROI at this year |

---

### 2.12 `model_meta`

**Source:** Hardcoded in migration script  
**Row count:** 1 (document `_id = "current"`)

| Field | Type | Description |
|---|---|---|
| `name` | str | Model name (e.g., `"XGBoost Dropout Classifier"`) |
| `params` | str | Serialized hyperparameters |
| `threshold` | float | Classification threshold (default 0.5) |
| `train_size` | int | Training set patient count |
| `test_size` | int | Test set patient count |
| `metrics.accuracy` | float | Overall accuracy |
| `metrics.precision` | float | Precision on dropout class |
| `metrics.recall` | float | Recall on dropout class |
| `metrics.f1` | float | F1 score |
| `metrics.auc_roc` | float | AUC-ROC |
| `last_trained` | str | ISO date string |
| `feature_count` | int | Number of input features |

---

## 3. CSV Source Files

All files live in `Backend/data/`.

---

### 3.1 `GLP1_FINAL_WITH_SURVIVAL.csv`
**Purpose:** Main patient dataset â€” inputs, labels, and survival fields  
**Rows:** ~7,566

| Column | Type | Description |
|---|---|---|
| `RIDAGEYR` | int | Age (years) |
| `gender_female` | int | `1` = female, `0` = male |
| `BMXBMI` | float | Body Mass Index |
| `LBXGH` | float | HbA1c (%) |
| `assigned_molecule` | str | GLP-1 drug name |
| `drug_generation` | int | `1` or `2` |
| `is_newer_drug` | int | `1` if generation 2 |
| `avg_oop_cost` | float | Annual out-of-pocket cost (USD) |
| `income_cost_pressure` | float | Financial pressure score (0â€“1) |
| `bio_friction` | float | Side-effect burden score (0â€“1) |
| `system_refill_score` | float | Pharmacy/provider reliability (0â€“1) |
| `comorbidity_score` | int | Number of comorbid conditions |
| `has_dyslipidemia` | int | `1` = yes |
| `has_dysglycemia` | int | `1` = yes |
| `cluster` | int | Assigned segment (0â€“3) |
| `is_adherent` | int | Actual adherence outcome (`1` = adherent) |
| `event_occurred` | int | `1` if dropout event observed |
| `time_to_dropout` | int | Days to event or censoring |
| `dropout_proba` | float | Model predicted dropout probability |
| `prediction` | str | `"Dropout Risk"` or `"Likely Adherent"` |

---

### 3.2 `shap_patient_drivers.csv`
**Purpose:** Per-patient SHAP explanation (test set only, ~1,514 rows)

| Column | Type | Description |
|---|---|---|
| `patient_idx` | int | Patient identifier (join key to main dataset) |
| `dropout_prob` | float | Model prediction on test set |
| `prediction` | str | Classification label |
| `driver_1` | str | Most important feature |
| `driver_1_direction` | str | Effect direction |
| `driver_1_shap` | float | SHAP value |
| `driver_2` | str \| blank | Second driver |
| `driver_2_direction` | str \| blank | Effect direction |
| `driver_2_shap` | float \| blank | SHAP value |
| `driver_3` | str \| blank | Third driver |
| `driver_3_direction` | str \| blank | Effect direction |
| `driver_3_shap` | float \| blank | SHAP value |

---

### 3.3 `segment_profiles.csv`
**Purpose:** Pre-computed summary statistics per segment  
**Rows:** 4

| Column | Type | Description |
|---|---|---|
| `cluster` | int | Cluster ID |
| `segment_label` | str | Full label |
| `{feature}_mean` | float | Mean of feature across segment |
| `{feature}_std` | float | Standard deviation |

Features covered: `RIDAGEYR`, `BMXBMI`, `LBXGH`, `avg_oop_cost`, `income_cost_pressure`, `bio_friction`, `system_refill_score`, `comorbidity_score`, `is_adherent`

---

### 3.4 `cost_effectiveness.csv`
**Purpose:** CEA summary per segment  
**Rows:** 4

| Column | Type | Description |
|---|---|---|
| `cluster` | int | Cluster ID |
| `segment` | str | Label |
| `n` | int | Patient count |
| `adherence_rate` | float | Adherence proportion |
| `avg_annual_cost` | float | Mean annual drug cost (USD) |
| `avg_oop_cost` | float | Mean out-of-pocket cost (USD) |
| `avg_weight_loss_pct` | float | Mean weight loss (%) |
| `avg_hba1c_reduction` | float | Mean HbA1c reduction (pp) |
| `cost_per_weight_pct` | float | Cost per 1% weight loss (USD) |
| `cost_per_hba1c_pt` | float | Cost per 1-point HbA1c reduction (USD) |
| `wasted_spend_per_pt` | float | Annual waste per dropout (USD) |
| `total_annual_spend` | float | Total segment annual spend (USD) |

---

### 3.5 `icer_by_segment.csv`
**Purpose:** ICER vs. alternative therapies  
**Rows:** 8 (4 clusters Ã— 2 comparators)

| Column | Type | Description |
|---|---|---|
| `cluster` | int | Cluster ID |
| `segment` | str | Segment label |
| `comparator` | str | `"insulin_glargine"` or `"sglt2_inhibitor"` |
| `icer_weight` | float | USD per additional 1% weight reduction vs. comparator |
| `icer_hba1c` | float | USD per additional 1-point HbA1c reduction vs. comparator |

---

### 3.6 `survival_checkpoints.csv`
**Purpose:** KM survival probabilities at standard timepoints  
**Rows:** 4

| Column | Type | Description |
|---|---|---|
| `segment` | str | Segment label |
| `day_30` | float | Survival at 30 days |
| `day_60` | float | Survival at 60 days |
| `day_90` | float | Survival at 90 days |
| `day_180` | float | Survival at 180 days |

---

### 3.7 `progression_cost.csv`
**Purpose:** Phase 1 â€” Per-patient 5yr/10yr Markov-projected downstream medical costs  
**Rows:** ~7,566  
_(Columns described in full in Collection 2.6 above)_

---

### 3.8 `rebound_risk.csv`
**Purpose:** Phase 2 â€” Per-patient metabolic rebound projections  
**Rows:** ~7,566  
_(Columns described in full in Collection 2.7 above)_

---

### 3.9 `rebound_trajectory.csv`
**Purpose:** Phase 2 â€” Cluster-level HbA1c/BMI rebound trajectory over 24 months  
**Rows:** ~300  
_(Columns described in Collection 2.8 above)_

---

### 3.10 `rebound_sensitivity.csv`
**Purpose:** Phase 2 â€” Sensitivity summary by dropout timing scenario  
**Rows:** 12  
_(Columns described in Collection 2.9 above)_

---

### 3.11 `payer_roi.csv`
**Purpose:** Phase 3 â€” Per-cluster ROI across payer pricing scenarios  
**Rows:** 12 (4 clusters Ã— 3 payer types)  
_(Columns described in full in Collection 2.10 above)_

---

### 3.12 `payer_roi_yearly.csv`
**Purpose:** Phase 3 â€” Annual ROI breakdown for trajectory charts  
**Rows:** ~120  
_(Columns described in Collection 2.11 above)_

---

### 3.13 `budget_impact.csv`
**Purpose:** Pre-computed budget impact scenarios (used as fallback reference)  
**Rows:** 4

| Column | Type | Description |
|---|---|---|
| `cluster` | int | Cluster ID |
| `segment` | str | Segment label |
| `n` | int | Patient count |
| `baseline_dropout_rate` | float | Current dropout rate |
| `new_dropout_rate` | float | Projected dropout rate after intervention |
| `baseline_wasted_spend` | int | Annual wasted spend before intervention (USD) |
| `intervention_cost` | int | Total intervention cost (USD) |
| `new_wasted_spend` | int | Projected wasted spend after intervention (USD) |
| `waste_saved` | int | Waste recovered (USD) |
| `net_saving` | int | Net saving after subtracting intervention cost (USD) |

---

## 4. API Endpoints

Base URL: `http://localhost:8000` (configurable via `VITE_API_URL`)

---

### Summary

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check â€” returns `{ status, version }` |
| GET | `/api/summary` | Dashboard KPIs, adherence by segment, dropout by time window |

---

### Patients

| Method | Path | Description |
|---|---|---|
| GET | `/api/patients` | Paginated, filtered patient list |
| GET | `/api/patients/{patient_idx}` | Single patient with SHAP drivers and survival data |

**GET `/api/patients` query parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `page` | int | 0 | Page number |
| `page_size` | int | 20 | Records per page (max 10,000) |
| `segment` | int | â€” | Filter by cluster 0â€“3 |
| `molecule` | str | â€” | Filter by drug name |
| `min_risk` | float | â€” | Minimum dropout probability (0â€“1) |
| `prediction` | str | â€” | `"Dropout Risk"` or `"Likely Adherent"` |
| `financial_only` | bool | false | Only patients with financial barrier as top driver |
| `sort_by` | str | `dropout_prob` | Field to sort by |
| `sort_dir` | str | `desc` | `"asc"` or `"desc"` |
| `search` | str | â€” | Search by patient_idx or driver_1 text |

---

### Segments

| Method | Path | Description |
|---|---|---|
| GET | `/api/segments` | All 4 segment profiles |
| GET | `/api/segments/{cluster_id}` | Single segment with live distribution stats |

---

### Clinical Analytics

| Method | Path | Description |
|---|---|---|
| GET | `/api/survival` | Kaplan-Meier curves, checkpoints, log-rank test |
| GET | `/api/cost-effectiveness` | CEA per segment + pharma benchmarks |
| POST | `/api/budget-impact` | Live ROI simulation (accepts BudgetRequest body) |
| GET | `/api/shap/global` | Global feature importance rankings |
| GET | `/api/model/info` | Classifier metadata and performance metrics |

**POST `/api/budget-impact` request body:**

| Field | Type | Default | Validation | Description |
|---|---|---|---|---|
| `dropout_reduction_pct` | float | 15 | 1â€“100 | Target dropout reduction (%) |
| `intervention_cost_per_patient` | float | 500 | â‰¥ 0 | Per-patient program cost (USD/yr) |
| `population_scope_pct` | float | 100 | 1â€“100 | % of population in scope |

---

### Consequence Model

| Method | Path | Description |
|---|---|---|
| GET | `/api/consequence/downstream-cost` | Phase 1 â€” Markov-projected medical costs by cluster |
| GET | `/api/consequence/rebound-risk` | Phase 2 â€” Metabolic rebound severity, trajectories, sensitivity |
| GET | `/api/consequence/payer-scenarios` | Lists available payer_type values in DB |
| GET | `/api/consequence/payer-roi` | Phase 3 â€” Net ROI at 1/3/5/10-year horizons |

**GET `/api/consequence/payer-roi` query parameters:**

| Parameter | Type | Default | Validation | Description |
|---|---|---|---|---|
| `intervention_cost` | float | 500 | 0â€“100,000 | Per-patient program cost (USD/yr) â€” drives the slider |
| `payer_type` | str | `current` | â€” | Pricing scenario: `current`, `medicare_2028`, `post_generic` |
| `adherence_uplift` | float | 0.15 | 0â€“0.5 | Absolute adherence increase the program delivers (e.g., `0.15` = +15pp) |

---

## 5. Pydantic Response Schemas

### 5.1 SummaryResponse

```
SummaryResponse
â”œâ”€â”€ kpis: KPIs
â”‚   â”œâ”€â”€ total_patients: int
â”‚   â”œâ”€â”€ adherence_rate: float
â”‚   â”œâ”€â”€ dropout_rate: float
â”‚   â”œâ”€â”€ avg_annual_cost: int
â”‚   â””â”€â”€ wasted_spend_annual: int
â”œâ”€â”€ adherence_by_segment: List[SegmentAdherence]
â”‚   â””â”€â”€ { cluster, segment, adherence, n, color }
â””â”€â”€ dropout_by_window: List[DropoutWindow]
    â””â”€â”€ { window, seg0, seg1, seg2, seg3 }
```

---

### 5.2 PatientsResponse

```
PatientsResponse
â”œâ”€â”€ total: int
â”œâ”€â”€ page: int
â”œâ”€â”€ page_size: int
â”œâ”€â”€ patients: List[PatientRow]       # see patients collection for fields
â””â”€â”€ summary: PatientSummary
    â”œâ”€â”€ high_risk_count: int
    â””â”€â”€ financial_barrier_count: int
```

---

### 5.3 PatientDetailResponse

```
PatientDetailResponse
â”œâ”€â”€ patient: PatientRow
â”œâ”€â”€ shap_drivers: List[SHAPDriver]
â”‚   â””â”€â”€ { rank, feature, direction, shap_value }
â””â”€â”€ segment_survival: SegmentSurvival
    â””â”€â”€ { day30, day60, day90, day180 }
```

---

### 5.4 SurvivalResponse

```
SurvivalResponse
â”œâ”€â”€ curves: List[KMCurve]
â”‚   â””â”€â”€ { cluster, label, color, adherence, data: [{day, survival}] }
â”œâ”€â”€ checkpoints: List[Checkpoint]
â”‚   â””â”€â”€ { segment, cluster, day30, day60, day90, day180 }
â”œâ”€â”€ median_survival: List[int]       # median days per cluster
â””â”€â”€ logrank: LogRank
    â””â”€â”€ { test_statistic, p_value, significant }
```

---

### 5.5 CostEffectivenessResponse

```
CostEffectivenessResponse
â”œâ”€â”€ cea: List[CEASegment]
â”‚   â””â”€â”€ { cluster, label, n, annual_cost, weight_loss, hba1c_reduction,
â”‚          cost_per_weight, cost_per_hba1c,
â”‚          icer_insulin_weight, icer_insulin_hba1c,
â”‚          icer_sglt2_weight, icer_sglt2_hba1c }
â””â”€â”€ benchmarks: Dict
    â”œâ”€â”€ glp1: { SEMAGLUTIDE, TIRZEPATIDE, LIRAGLUTIDE, DULAGLUTIDE }
    â”‚         each â†’ { weight_loss_pct, hba1c_reduction, annual_cost }
    â”œâ”€â”€ comparators: { insulin_glargine, sglt2_inhibitor }
    â”‚               each â†’ { weight_loss_pct, hba1c_reduction, annual_cost }
    â””â”€â”€ icer_threshold: 50000
```

---

### 5.6 BudgetResponse

```
BudgetResponse
â”œâ”€â”€ total_net_saving: int
â”œâ”€â”€ total_waste_recovered: int
â”œâ”€â”€ total_intervention_cost: int
â”œâ”€â”€ break_even_month: int | null
â””â”€â”€ segments: List[SegmentImpact]
    â””â”€â”€ { cluster, label, n_in_scope, baseline_dropout_rate, new_dropout_rate,
           baseline_wasted_spend, waste_recovered, intervention_cost,
           net_saving, roi_positive }
```

---

### 5.7 PayerROIResponse

```
PayerROIResponse
â”œâ”€â”€ by_cluster: List[PayerROICluster]
â”‚   â”œâ”€â”€ cluster_id, cluster_label, n_patients
â”‚   â”œâ”€â”€ adherence_probability        # baseline Î±
â”‚   â”œâ”€â”€ adherence_with_program       # Î± + Î”Î± (capped at 1.0)
â”‚   â”œâ”€â”€ effective_adherence_uplift   # actual Î”Î± applied
â”‚   â”œâ”€â”€ avg_annual_drug_cost
â”‚   â”œâ”€â”€ avg_time_to_dropout_days
â”‚   â”œâ”€â”€ break_even_adherence_rate
â”‚   â”œâ”€â”€ intervention_cost_threshold_5yr
â”‚   â”œâ”€â”€ time_to_positive_roi_years
â”‚   â”œâ”€â”€ horizons: List[PayerROIHorizon]   # at years 1, 3, 5, 10
â”‚   â”‚   â””â”€â”€ { horizon_years, expected_drug_cost, gross_benefit,
â”‚   â”‚          intervention_cost, net_benefit,
â”‚   â”‚          roi,                       # drug economics ROI
â”‚   â”‚          delta_benefit_medical,     # Î”Î± Ã— (C_dropout âˆ’ C_adherent)
â”‚   â”‚          delta_drug_cost,           # extra drug spend from higher adherence
â”‚   â”‚          intervention_roi_medical,  # program ROI (no drug cost)
â”‚   â”‚          intervention_roi_net }     # program ROI net of drug spend â† responds to payer_type
â”‚   â””â”€â”€ yearly_roi_series: List[PayerROIYearlyPoint]   # years 1â€“10
â”‚       â””â”€â”€ { year, roi, intervention_roi_medical, intervention_roi_net }
â”œâ”€â”€ population_roi_{1,3,5,10}yr
â”œâ”€â”€ population_intervention_roi_medical_{1,5,10}yr
â”œâ”€â”€ population_intervention_roi_net_{1,5,10}yr      â† what the dashboard displays
â”œâ”€â”€ intervention_cost_per_patient
â”œâ”€â”€ adherence_uplift_applied
â””â”€â”€ n_patients_total
```

---

## 6. Frontend Constants & API Client

### `Frontend/src/data/mockData.js` â€” Exported Constants

| Export | Type | Description |
|---|---|---|
| `SEGMENT_COLORS` | string[4] | Hex color per cluster (index = cluster ID) |
| `SEGMENT_LABELS` | string[4] | Full label per cluster |
| `SEGMENT_SHORT` | string[4] | Short label per cluster |
| `summaryKPIs` | object | Mock KPI values (used as fallback) |
| `adherenceBySegment` | object[4] | Mock adherence data per segment |
| `globalSHAPDrivers` | object[9] | Global feature importance `{ feature, importance }` |
| `dropoutByWindow` | object[4] | Dropout counts by time window |
| `patients` | object[200] | Seeded mock patient records |
| `segmentProfiles` | object[4] | Mock segment profiles |
| `survivalCurves` | object[4] | Mock KM curves with computed points |
| `survivalCheckpoints` | object[4] | Mock survival checkpoints |
| `medianSurvival` | int[4] | Median survival days per segment |
| `ceaData` | object[4] | Mock CEA records |
| `modelInfo` | object | Mock model metadata |
| `dataSources` | object[5] | Data source descriptions |
| `calcBudgetImpact(...)` | function | `(dropoutReductionPct, interventionCostPerPt, populationScopePct) â†’ object[4]` |

---

### `Frontend/src/data/api.js` â€” API Client Methods

| Method | HTTP | Path | Parameters |
|---|---|---|---|
| `api.getSummary()` | GET | `/api/summary` | â€” |
| `api.getGlobalSHAP()` | GET | `/api/shap/global` | â€” |
| `api.getPatients(params)` | GET | `/api/patients?...` | URLSearchParams object |
| `api.getPatient(id)` | GET | `/api/patients/{id}` | `id: int` |
| `api.getSegments()` | GET | `/api/segments` | â€” |
| `api.getSegment(id)` | GET | `/api/segments/{id}` | `id: int` |
| `api.getSurvival()` | GET | `/api/survival` | â€” |
| `api.getCostEffectiveness()` | GET | `/api/cost-effectiveness` | â€” |
| `api.getBudgetImpact(body)` | POST | `/api/budget-impact` | `BudgetRequest` object |
| `api.getModelInfo()` | GET | `/api/model/info` | â€” |
| `api.getDownstreamCost()` | GET | `/api/consequence/downstream-cost` | â€” |
| `api.getReboundRisk()` | GET | `/api/consequence/rebound-risk` | â€” |
| `api.getPayerScenarios()` | GET | `/api/consequence/payer-scenarios` | â€” |
| `api.getPayerROI(cost, type, uplift)` | GET | `/api/consequence/payer-roi?...` | `interventionCost`, `payerType`, `adherenceUplift` |

---

## 7. Key Derived Metrics

### ROI Variants (Payer ROI screen)

Three ROI metrics are computed server-side for each cluster Ã— horizon combination:

| Metric | Field | Formula | Responds to `payer_type`? |
|---|---|---|---|
| Drug economics ROI | `roi` | `(gross_benefit âˆ’ drug_cost âˆ’ intervention_cost) / drug_cost` | Yes |
| Program ROI (medical) | `intervention_roi_medical` | `(Î”Î± Ã— (C_dropout âˆ’ C_adherent) âˆ’ intervention_cost) / intervention_cost` | **No** â€” no drug cost term |
| Program ROI (net of drug) | `intervention_roi_net` | `(Î”Î± Ã— (C_dropout âˆ’ C_adherent) âˆ’ Î”Î± Ã— drug_cost Ã— annuity âˆ’ intervention_cost) / intervention_cost` | **Yes** â€” displayed on dashboard |

Where:
- `Î”Î±` = `adherence_with_program âˆ’ adherence_probability` (capped at 1.0)
- `C_dropout` = per-patient downstream medical cost if dropout
- `C_adherent` = per-patient downstream medical cost if adherent
- `annuity` = discounted annuity factor at 3% for the horizon
- `intervention_cost` = program cost per patient (slider value, USD/yr)

### Rebound Severity Score

Composite score (0â€“1) per patient, weighting HbA1c rebound magnitude, diabetes status at dropout, and time-to-T2D-threshold. Higher = worse prognosis post-dropout.

### ICER (Incremental Cost-Effectiveness Ratio)

`ICER = (Cost_GLP1 âˆ’ Cost_comparator) / (Effectiveness_GLP1 âˆ’ Effectiveness_comparator)`

Willingness-to-pay threshold: **$50,000** per unit of clinical improvement.

### Discount Rate

All multi-year cost projections use a **3% annual discount rate** (configured in `Backend/routers/consequence.py` as `_DISCOUNT_RATE`).

---
