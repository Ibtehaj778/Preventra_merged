# NeuroShield — Feature Notes (Week 2)

## Null Handling Decisions

| Column | Null Marker | Strategy | Rationale |
|--------|------------|----------|-----------|
| All columns | `'?'` (string) | Replace with `pd.NA` | Dataset-specific null marker |
| Numeric columns | `NaN` | Fill with `0` | Missing counts/values conservatively assumed zero |
| Categorical columns | `NaN` | Fill with column mode | Most frequent value is safest default |
| Remaining NaN | Any | Forward-fill then back-fill | Safety net for any stragglers |

## Dropped Columns

### During Cleaning Phase
| Column | Reason |
|--------|--------|
| `encounter_id` | Administrative ID, not a clinical feature |
| `patient_nbr` | Patient ID, would cause data leakage |
| `weight` | >95% missing — unusable |
| `payer_code` | Administrative, not clinical |
| `medical_specialty` | High cardinality, not mapped to any NeuroShield feature |

### After Feature Transformation (to avoid duplicates)
| Column | Reason |
|--------|--------|
| `readmitted` | Transformed to `label` binary column |
| `number_inpatient` | Renamed to `ip_admissions_365d_prior` |
| `number_emergency` | Renamed to `ed_visits_90d_prior` |
| `num_medications` | Renamed to `medication_count_at_discharge` |
| `time_in_hospital` | Renamed to `length_of_stay_days` |
| `change` | Transformed to `medication_change_flag` binary column |
| `admission_type_id` | Transformed to `admission_acuity_flag` binary column |
| `insulin` | Transformed to `high_risk_medication_flag` binary column |
| `number_diagnoses` | Used in `complex_discharge_flag` calculation |
| `diag_1`, `diag_2`, `diag_3` | Used to compute `charlson_comorbidity_index` |
| `age` | Used to compute `frailty_proxy` |

## Feature Gap Documentation

The following NeuroShield features are **not available** in the Diabetes 130 dataset
and are excluded from the MVP model:

| Feature | Reason |
|---------|--------|
| `pcp_assigned_flag` | No primary care assignment data in dataset |
| `social_risk_index` | No social determinant fields available |
| `days_to_first_appointment` | No appointment scheduling data available |

These are documented as future data requirements for clinical client integration.

## CCI Implementation Notes

- ICD-9 codes are read from `diag_1`, `diag_2`, `diag_3` columns.
- Decimal suffixes are stripped before matching (e.g. `250.01` -> `25001`).
- Duplicate categories across diagnosis columns are counted only once per patient.
- The Charlson weights used follow the original 1987 Charlson et al. classification.
- V-codes and E-codes (non-numeric ICD-9 prefixes) are skipped and return weight 0.

## Partial Proxy Features

| Feature | Limitation |
|---------|-----------|
| `ed_visits_90d_prior` | `number_emergency` column does not guarantee a 90-day window — used as proxy |
| `medication_change_flag` | Only captures whether any change occurred, not which drug |
| `high_risk_medication_flag` | Insulin is used as a representative high-risk drug; other high-risk drugs are not captured |
| `frailty_proxy` | Age bracket is used as a frailty surrogate; no functional status or clinical frailty score available |