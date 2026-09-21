# Feature Engineering Data Dictionary

This document outlines the end-to-end transformation of features from the original dataset through the feature engineering pipeline, culminating in the final feature dimensions used for modeling.

## Table 1: Original Features Transformation

Each column in the original `diabetic_data.csv` dataset is listed below, describing its original meaning and how it was treated or transformed in the final dataset.

| Original Feature | Representation | Feature Engineering Outcome |
| :--- | :--- | :--- |
| `encounter_id` | Unique administrative ID for the encounter | **Dropped completely** during cleaning (administrative, non-clinical). |
| `patient_nbr` | Unique patient ID number | **Dropped completely** during cleaning to avoid data leakage. |
| `race` | Patient's race | **One-hot encoded** into `race_*` variables. Original column dropped. |
| `gender` | Patient's gender | **One-hot encoded** into `gender_*` variables. Original column dropped. |
| `age` | Patient's age segment bracket | Used to compute `frailty_proxy` and `probabilistic_no_show`. Original dropped. |
| `weight` | Patient's weight | **Dropped completely** (> 95% missing values, unusable). |
| `admission_type_id` | Integer identifier for type of admission | Transformed to binary `admission_acuity_flag`. Original column dropped. |
| `discharge_disposition_id` | Integer identifier for discharge destination | **Passed through** without change. |
| `admission_source_id` | Integer identifier for admission source | **Passed through** without change. |
| `time_in_hospital` | Number of days between admission and discharge | Renamed to `length_of_stay_days`. Used for `complex_discharge_flag`. Original dropped. |
| `payer_code` | Payer type administrative code | **Dropped completely** during cleaning (administrative, non-clinical). |
| `medical_specialty` | Specialty of the admitting physician | **Dropped completely** during cleaning (high cardinality, unmapped). |
| `num_lab_procedures` | Total lab tests performed during the encounter | **Passed through** without change. |
| `num_procedures` | Non-lab procedures during the encounter | **Passed through** without change. |
| `num_medications` | Total distinct medications administered | Renamed to `medication_count_at_discharge`. Used for `complex_discharge_flag`. Original dropped. |
| `number_outpatient` | Total outpatient visits in the year prior | **Passed through**. Also used to derive `no_show_proxy`. |
| `number_emergency` | Total emergency visits in the year prior | Renamed to `ed_visits_90d_prior`. Used for `high_utilizer_flag` and `no_show_proxy`. Original dropped. |
| `number_inpatient` | Total inpatient admissions in the year prior | Renamed to `ip_admissions_365d_prior`. Used for `high_utilizer_flag` and `no_show_proxy`. Original dropped. |
| `diag_1` | Primary ICD-9 diagnosis code | Used to compute `charlson_comorbidity_index`, `behavioral_health_flag`, and `probabilistic_no_show`. Original dropped. |
| `diag_2` | Secondary ICD-9 diagnosis code | (Same as diag_1). Original dropped. |
| `diag_3` | Additional secondary ICD-9 diagnosis code | (Same as diag_1). Original dropped. |
| `number_diagnoses` | Number of diagnoses entered to the system | Used in calculating `complex_discharge_flag` and `no_show_proxy`. Original dropped. |
| `max_glu_serum` | Results of max glucose serum test | **One-hot encoded** into `max_glu_serum_*` variables. Original dropped. |
| `A1Cresult` | Results of A1c test | **One-hot encoded** into `A1Cresult_*` variables. Original dropped. |
| `change` | Indicates if diabetic medications were changed | Transformed to binary `medication_change_flag`. Original dropped. |
| `diabetesMed` | Indicates if any diabetic med was prescribed | **Binary encoded** (1 for Yes, 0 for No). |
| `readmitted` | Days to inpatient readmission (<30, >30, NO) | Transformed to the binary target variable `label`. Original dropped. |
| `insulin` | Insulin prescribed / changed | Transformed to `high_risk_medication_flag`. Dropped completely as raw medication. |
| `metformin`, `repaglinide`, `nateglinide`, `chlorpropamide`, `glimepiride`, `acetohexamide`, `glipizide`, `glyburide`, `tolbutamide`, `pioglitazone`, `rosiglitazone`, `acarbose`, `miglitol`, `troglitazone`, `tolazamide`, `examide`, `citoglipton`, `glyburide-metformin`, `glipizide-metformin`, `glimepiride-pioglitazone`, `metformin-rosiglitazone`, `metformin-pioglitazone` | Raw diabetic medication status (steady/up/down/no) | **Dropped completely**. Deemed raw medication specifics unnecessary for these proxies; the pipeline instead aggregates them into broader concepts like changes and high risk med flags. |

*(Note: Every medication listed above under "Raw diabetic medication status" accounts for 22 individual columns that were fully removed from the analysis).*

---

## Table 2: Final Model Features

The following table documents each engineered, derived, or passed-through feature present in the final `features.csv` dataset, describing its finalized representation.

| Final Feature Name | Representation / Meaning |
| :--- | :--- |
| `discharge_disposition_id` | Integer ID corresponding to the patient's discharge destination. |
| `admission_source_id` | Integer ID corresponding to the source of the patient's admission. |
| `num_lab_procedures` | Total count of lab tests performed during the patient's hospital stay. |
| `num_procedures` | Total count of non-lab procedures performed during the patient's hospital stay. |
| `number_outpatient` | Total number of outpatient visits by the patient in the year prior to the encounter. |
| `diabetesMed` | Binary indicator (1=Yes, 0=No) denoting whether any diabetic medication was prescribed. |
| `label` | Binary target variable (1/0) indicating whether the patient was flagged for readmission. |
| `charlson_comorbidity_index` | Clinical measure weighting the severity of patient comorbidities, derived from `diag_1`, `diag_2`, and `diag_3` ICD-9 codes. |
| `ip_admissions_365d_prior` | Unchanged integer count (renamed from `number_inpatient`) representing inpatient admissions in the prior year. |
| `ed_visits_90d_prior` | Proxy count representing emergency visits in an assumed 90-day window (renamed from `number_emergency`). |
| `medication_count_at_discharge` | Total distinct medications listed at discharge (renamed from `num_medications`). |
| `length_of_stay_days` | Number of days passed between hospital admission and discharge (renamed from `time_in_hospital`). |
| `medication_change_flag` | Binary indicator (1=Yes, 0=No) denoting whether any change was made to diabetic medications. |
| `admission_acuity_flag` | Binary indicator denoting if the admission type was high-acuity (Emergency/Urgent admission types correspond to 1). |
| `high_utilizer_flag` | Binary indicator representing a high previous utilization of hospital resources (>= 2 previous inpatient OR emergency visits). |
| `high_risk_medication_flag` | Binary indicator denoting the presence of a high-risk medication regime (proxied specifically using `insulin`). |
| `complex_discharge_flag` | Binary indicator showing if a discharge was complicated: LOS > 7 days AND medications > 10 AND diagnosis codes > 7. |
| `behavioral_health_flag` | Binary indicator denoting an underlying mental/behavioral health condition (derived from any diagnosis code in the 291-319 ICD-9 range). |
| `frailty_proxy` | Binary indicator acting as a proxy for frailty, flagged to 1 if the patient's age bracket lower bound is >= 75. |
| `no_show_proxy` | Continuous score [0, 1] acting as a heuristic proxy for appointment no-show likelihood, combining low engagement, emergency ratios, and visit gaps. |
| `probabilistic_no_show` | Probability score [0, 1] predicting no-show behavior via transfer learning from a separate cross-domain `noshow.csv` model. |
| `race_AfricanAmerican`, `race_Asian`, `race_Caucasian`, `race_Hispanic`, `race_Other` | Categorical one-hot encoded variables capturing the patient's racial demographic. |
| `gender_Female`, `gender_Male`, `gender_Unknown/Invalid` | Categorical one-hot encoded variables capturing the patient's gender demographic. |
| `max_glu_serum_>200`, `max_glu_serum_>300`, `max_glu_serum_Norm` | Categorical one-hot encoded variables documenting the max glucose serum levels. |
| `A1Cresult_>7`, `A1Cresult_>8`, `A1Cresult_Norm` | Categorical one-hot encoded variables documenting the patient's A1c blood test indicators. |
