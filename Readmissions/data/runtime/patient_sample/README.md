# Patient sample — 10 patients

Exported 2026-09-11 05:39 UTC from the `neuroshield` MongoDB database.

Every file here is filtered to the same patient ids, so the folder is a
coherent slice rather than five unrelated extracts. Each collection is
written twice: `.csv` for spreadsheets, `.json` where nested fields
(weekly observations, group evidence) need to stay intact.

## Patients

| Patient | Band | Score | Weeks | Group |
|---|---|---:|---:|---|
| `MIMIC-16466602` | High | 77.8 | 5 | cardiac_other |
| `MIMIC-19014451` | Medium | 39.5 | 5 | cardiac_other |
| `MIMIC-11145160` | Low | 18.9 | 5 | cardiac_other |
| `MIMIC-10758777` | High | 83.2 | 5 | diabetes |
| `MIMIC-10672726` | Medium | 39.3 | 5 | diabetes |
| `MIMIC-15446497` | Low | 19.8 | 5 | diabetes |
| `MIMIC-18284271` | High | 94.0 | 5 | general |
| `MIMIC-17170079` | Medium | 39.7 | 5 | general |
| `MIMIC-16548419` | Low | 19.9 | 5 | general |
| `MIMIC-12892273` | High | 96.0 | 5 | heart_failure |

Bands: High 4, Medium 3, Low 3  
Groups: cardiac_other 3, diabetes 3, general 3, heart_failure 1

## Files

| File | Rows | Notes |
|---|---:|---|
| `patient_worklist.csv` / `.json` | 10 | one row per patient — discharge score, current band, drivers, diagnoses, clinical group |
| `weekly_monitoring.csv` / `.json` | 50 | one row per patient per week — week 0 is the model, weeks 1-4 the rule layer |
| `risk_registry.csv` / `.json` | 85 | score history across scoring batches |
| _(not written)_ | 0 | `care_actions` — coordinator assignments and notes; none for these patients |
| `executive_summary.csv` / `.json` | 5 | band counts per batch |
| `patients.json` | 10 | the selection itself, with why each was picked |

## Joining them

Everything keys on `patient_id`:

```python
import pandas as pd
wl = pd.read_csv('patient_worklist.csv')
wk = pd.read_csv('weekly_monitoring.csv').sort_values(['patient_id', 'week_number'])
wk.merge(wl[['patient_id', 'clinical_group', 'primary_diagnosis']], on='patient_id')
```

In the CSV the nested `monitoring` object is flattened to dotted columns —
`monitoring.adherence_pct`, `monitoring.spo2`, `monitoring.weight_change_kg` and
so on. The JSON keeps it nested. `driver_1..3` are
`label: value (explanation)` strings in both.

## Provenance

Discharge scores and their SHAP drivers are real model output over MIMIC-IV.
The weekly observations are augmented — MIMIC holds no post-discharge data —
with trajectories drawn from the model's own calibrated probability. Every
weekly row carries `source` saying so.
