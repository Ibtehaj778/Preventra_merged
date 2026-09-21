# Preventra: CMS Claims Migration & Implementation Guide

This guide outlines how to transition the **Preventra (NeuroShield)** clinical readmission dashboard from the static, single-disease **UCI Diabetic Patient Dataset** to the longitudinal, multi-disease **CMS DE-SynPUF (Medicare Claims) Dataset**.

---

## 1. High-Level Comparison: Diabetes vs. CMS Data

| Dimension | UCI Diabetes Dataset (Current) | CMS DE-SynPUF Dataset (Target) |
| :--- | :--- | :--- |
| **Population** | Hospitalized patients diagnosed with diabetes. | Multi-disease Medicare cohort (elderly 65+ and disabled). |
| **Data Format** | Single flat file (`diabetic_data.csv`). | 5 relational claims tables (Inpatient, Outpatient, Carrier, Part D, Beneficiary). |
| **Lab/Clinical Data** | Direct lab results (`A1Cresult`, `max_glu_serum`). | None. Severity must be proxied by diagnosis/procedure codes and DRGs. |
| **Longitudinality** | Single-encounter snapshots. | 3-year linked longitudinal history per patient. |
| **Pharmacy Data** | Self-reported medications during stay (23 drugs). | Part D pharmacy event fill dates, quantity, and supply length. |
| **Readmission Target** | Self-contained `readmitted` field (`<30`, `>30`, `NO`). | Algorithmically derived from subsequent inpatient admission dates. |

---

## 2. Relational Schema & Ingestion Spine

To build the dataset, we must construct an **Inpatient Discharge Spine** and left-join demographics, prior utilization, and pharmacy fills:

```
    ┌────────────────────────────────────────────────────────┐
    │          Inpatient Claims (sample1_3.csv)              │  ◄── Inpatient Spine
    │  (Index discharge date t0, DRG, diagnosis codes, LOS)  │
    └───────────────────────────┬────────────────────────────┘
                                │
          Left Join on          │ Left Join on
          DESYNPUF_ID           │ DESYNPUF_ID &
          & Year                │ 365-day Lookback Window
                                │
    ┌───────────────────────────▼────────┐  ┌───────────────────────────▼────────┐
    │  Beneficiary Summary (sample1_0)   │  │   Prior Carrier / Outpatient       │
    │  (Age, Sex, Chronic Condition      │  │   Claims (sample1_1, 1_2, 1_4)     │
    │   demographic baseline)            │  │  (Prior PCP/ED visits, procedures) │
    └────────────────────────────────────┘  └────────────────────────────────────┘
```

### Joining Logic Rules
1. **Primary Entity:** Each row in the Inpatient Claims file (`sample1_3.csv`) represents a discharge at time $t_0$ (`NCH_BENE_DSCHRG_DT`).
2. **Demographics:** Left-join demographic details from Beneficiary Summaries (`sample1_0.csv`, etc.) using `DESYNPUF_ID` and matching the year of $t_0$.
3. **Lookback Features:** Aggregate Outpatient/Carrier visits and Part D prescription fills occurring in the $365$ days prior to the admission date (`CLM_ADMSN_DT`).

---

## 3. Feature Mapping & Code Implementation

Here is how the existing feature set from `features/engineer.py` maps to the new CMS schema:

### 3.1 Feature Map

| Current Diabetes Feature | CMS Equivalent Data Source | Calculation Logic |
| :--- | :--- | :--- |
| `ip_admissions_365d_prior` | Inpatient Claims (`sample1_3.csv`) | Count admissions for `DESYNPUF_ID` where `CLM_ADMSN_DT` is within 365 days prior. |
| `ed_visits_90d_prior` | Carrier Claims (`sample1_1.csv`/`1_2.csv`) | Count visits with ED procedure codes (`99281–99285`) in 90 days prior. |
| `length_of_stay_days` | Inpatient Claims (`sample1_3.csv`) | `NCH_BENE_DSCHRG_DT` $-$ `CLM_ADMSN_DT`. |
| `medication_count_at_discharge` | Part D Events (`sample1_5.csv`) | Count unique `PROD_SRVC_ID` filled in 90 days prior to admission. |
| `high_risk_medication_flag` | Part D Events (`sample1_5.csv`) | Flag if pharmacy records show active fills for high-risk classes (e.g., insulin, anticoagulants). |
| `behavioral_health_flag` | Inpatient Claims (`sample1_3.csv`) | Flag if any of `ICD9_DGNS_CD_1` to `10` fall in range `291–319`. |
| `frailty_proxy` | Beneficiary Summary | Flag if patient age (computed from `BENE_BIRTH_DT` at admission) $\ge 75$. |
| `no_show_proxy` | Carrier Claims (`sample1_1.csv`/`1_2.csv`) | Ratio of ED visits/ambulance calls to scheduled outpatient E&M visits (`99211–99215`). |

### 3.2 Python Feature Engineering Example

```python
import pandas as pd
import numpy as np

def build_cms_features(inpatient_path, beneficiary_path, carrier_path, pde_path):
    # Load Tables
    df_ip = pd.read_csv(inpatient_path)
    df_bene = pd.read_csv(beneficiary_path)
    df_car = pd.read_csv(carrier_path)
    df_pde = pd.read_csv(pde_path)
    
    # Parse dates
    df_ip['CLM_ADMSN_DT'] = pd.to_datetime(df_ip['CLM_ADMSN_DT'].astype(str), format='%Y%m%d')
    df_ip['NCH_BENE_DSCHRG_DT'] = pd.to_datetime(df_ip['NCH_BENE_DSCHRG_DT'].astype(str), format='%Y%m%d')
    df_bene['BENE_BIRTH_DT'] = pd.to_datetime(df_bene['BENE_BIRTH_DT'].astype(str), format='%Y%m%d')
    df_car['CLM_FROM_DT'] = pd.to_datetime(df_car['CLM_FROM_DT'].astype(str), format='%Y%m%d')
    df_pde['SRVC_DT'] = pd.to_datetime(df_pde['SRVC_DT'].astype(str), format='%Y%m%d')
    
    # 1. Base Spine: Inpatient Length of Stay
    df_ip['length_of_stay_days'] = (df_ip['NCH_BENE_DSCHRG_DT'] - df_ip['CLM_ADMSN_DT']).dt.days
    
    # 2. Join Demographics & Calculate Age
    df_ip = df_ip.merge(df_bene[['DESYNPUF_ID', 'BENE_BIRTH_DT', 'BENE_SEX_IDENT_CD', 'SP_CHF', 'SP_COPD', 'SP_DIABETES']], on='DESYNPUF_ID', how='left')
    df_ip['age_at_admission'] = ((df_ip['CLM_ADMSN_DT'] - df_ip['BENE_BIRTH_DT']).dt.days / 365.25).astype(int)
    df_ip['frailty_proxy'] = (df_ip['age_at_admission'] >= 75).astype(int)
    
    # 3. Comorbidity (Charlson Comorbidity Index from 10 Diagnosis Columns)
    dx_cols = [f'ICD9_DGNS_CD_{i}' for i in range(1, 11)]
    # Use existing CCI mapping logic on dx_cols instead of diag_1..3
    
    # 4. Aggregations (Prior Admissions, ED Visits, and Rx Counts)
    prior_ips = []
    prior_eds = []
    prior_meds = []
    
    for idx, row in df_ip.iterrows():
        p_id = row['DESYNPUF_ID']
        adm_dt = row['CLM_ADMSN_DT']
        
        # Inpatient lookback
        ips = df_ip[(df_ip['DESYNPUF_ID'] == p_id) & (df_ip['CLM_ADMSN_DT'] < adm_dt) & (df_ip['CLM_ADMSN_DT'] >= adm_dt - pd.Timedelta(days=365))]
        prior_ips.append(len(ips))
        
        # ED visit lookback (HCPCS 99281-99285 in carrier claims)
        eds = df_car[(df_car['DESYNPUF_ID'] == p_id) & (df_car['CLM_FROM_DT'] < adm_dt) & (df_car['CLM_FROM_DT'] >= adm_dt - pd.Timedelta(days=90))]
        # Check HCPCS columns in Carrier Claims
        ed_count = 0
        for i in range(1, 46):
            col = f'HCPCS_CD_{i}'
            if col in eds.columns:
                ed_count += eds[col].astype(str).isin(['99281', '99282', '99283', '99284', '99285']).sum()
        prior_eds.append(ed_count)
        
        # Meds count (Part D fills in prior 90 days)
        rx = df_pde[(df_pde['DESYNPUF_ID'] == p_id) & (df_pde['SRVC_DT'] < adm_dt) & (df_pde['SRVC_DT'] >= adm_dt - pd.Timedelta(days=90))]
        prior_meds.append(rx['PROD_SRVC_ID'].nunique())
        
    df_ip['ip_admissions_365d_prior'] = prior_ips
    df_ip['ed_visits_90d_prior'] = prior_eds
    df_ip['medication_count_at_discharge'] = prior_meds
    
    return df_ip
```

---

## 4. Derived Label (Ground Truth Outcome)

Readmission is derived by comparing discharge dates of index stays with admission dates of subsequent stays:

```python
def label_readmissions(df_ip):
    df_ip = df_ip.sort_values(by=['DESYNPUF_ID', 'CLM_ADMSN_DT'])
    df_ip['readmitted_30d'] = 0
    
    for p_id, group in df_ip.groupby('DESYNPUF_ID'):
        group_indices = group.index
        for idx in range(len(group_indices) - 1):
            curr_idx = group_indices[idx]
            next_idx = group_indices[idx + 1]
            
            curr_dschrg = df_ip.loc[curr_idx, 'NCH_BENE_DSCHRG_DT']
            next_admit = df_ip.loc[next_idx, 'CLM_ADMSN_DT']
            
            days_to_readmit = (next_admit - curr_dschrg).days
            if 0 <= days_to_readmit <= 30:
                df_ip.loc[curr_idx, 'readmitted_30d'] = 1
                
    return df_ip
```

---

## 5. Required Backend & API Code Changes

Because manual updates and score-calculation logic are duplicated, we must modify the backend API in the following places:

### 5.1 MongoDB Collections Schema Update
MongoDB documents in `patient_worklist` must be restructured to accommodate the CMS features.
* **Fields to Remove**: `race`, `gender`, `max_glu_serum`, `A1Cresult`, and the 23 oral diabetes medications.
* **Fields to Add**: `age_at_admission`, `SP_CHF` (Congestive Heart Failure), `SP_COPD` (COPD), `SP_DIABETES` (Diabetes chronic flag), `SP_CHRNKIDN` (Chronic Kidney Disease), `DRG_CODE`, and `medication_possession_ratio` (for Phase 2).

### 5.2 Manual Scoring Endpoints in `api/main.py`
The `/api/patients/predict` and `/api/patients/update` endpoints contain an inline copy of the feature-engineering pipeline.
1. Update the Pydantic schema `PatientData` to match the CMS feature schema:
   ```python
   class PatientData(BaseModel):
       age_at_admission: int
       length_of_stay_days: int
       ip_admissions_365d_prior: int
       ed_visits_90d_prior: int
       medication_count_at_discharge: int
       charlson_comorbidity_index: int
       sp_chf: int  # 1 = Yes, 2 = No
       sp_copd: int
       sp_diabetes: int
       drg_code: str
   ```
2. Refactor the manual feature-mapping logic in `predict_score()` to compute standard scaling and score predictions using the newly trained MLflow model using these parameters.

### 5.3 Chatbot Queries in `api/chatbot_queries.py`
The chatbot queries must be updated to reference the new fields:
* Update `get_risk_patients_by_threshold` and `get_patient_details` to return and query chronic conditions (`SP_CHF`, `SP_COPD`, etc.) and `DRG_CODE` rather than diabetes medications.
* Register new queries (e.g., summarizing patients by chronic disease flag or average Medicare expenditure).

---

## 6. Frontend Dashboard Updates

The React frontend components must be updated to align with the CMS schema:

### 6.1 Patient Detail Views & Worklists
* **`frontend/src/components/dashboard/PatientWorklist.jsx`**:
  * Replace the "Diabetes Meds" indicator with a badge showing the patient's primary chronic condition (e.g., CHF, COPD, Diabetes) or DRG Category.
* **`frontend/src/pages/PatientDetail.jsx` & `PatientDetailPanel.jsx`**:
  * Display a summary cards grid for the patient's chronic condition flags.
  * Render a timeline chart of Medicare payments/spend if desired.

### 6.2 Manual Forms (`ManualEntry.jsx` & `UpdatePatient.jsx`)
* Modify form controls to collect the new patient profile:
  * Drop input selectors for diabetes medication details.
  * Add dropdowns for chronic conditions, DRG code, and count fields for prior inpatient admissions / ED visits.
  * Ensure payload validation aligns with the new FastAPI Pydantic schema.

---

## 7. Migration Timeline (2-Week Plan Integration)

To integrate this migration seamlessly, follow this action schedule:

* **Week 1 (Days 1–5): ML Pipeline & Model Training**
  * Stand up claims ingestion & join tables (`Inpatient` + `Beneficiary` + `Carrier`).
  * Train and register the CMS Decision Tree / XGBoost classifier. Calibrate bands.
* **Week 2 (Days 6–10): Weekly Dynamic Snapshots & Dashboard Integration**
  * Generate post-discharge features (PCP follow-up visits, Rx refill gaps from Part D).
  * Update MongoDB schemas, FastAPI endpoints (including manual scoring), and chatbot queries.
  * Refactor React pages (`PatientDetail`, `ManualEntry`, `UpdatePatient`) to utilize CMS fields.
