```python
import glob
import pandas as pd
import os

files = sorted(glob.glob('sample1_*.csv'))
print("Files found:", files)

for f in files:
    try:
        df = pd.read_csv(f, nrows=5)
        full_df = pd.read_csv(f)
        print("="*70)
        print(f"File: {f} | Total Shape: {full_df.shape}")
        print("Columns (first 10 of {}): {}".format(len(full_df.columns), full_df.columns.tolist()[:10]))
        print("Sample data:")
        print(df.iloc[:2, :8])
    except Exception as e:
        print(f"Error reading {f}: {e}")


```

```text
Files found: ['sample1_0.csv', 'sample1_1.csv', 'sample1_2.csv', 'sample1_3.csv', 'sample1_4.csv', 'sample1_5.csv', 'sample1_6.csv', 'sample1_7.csv']
======================================================================
File: sample1_0.csv | Total Shape: (100, 32)
Columns (first 10 of 32): ['DESYNPUF_ID', 'BENE_BIRTH_DT', 'BENE_DEATH_DT', 'BENE_SEX_IDENT_CD', 'BENE_RACE_CD', 'BENE_ESRD_IND', 'SP_STATE_CODE', 'BENE_COUNTY_CD', 'BENE_HI_CVRAGE_TOT_MONS', 'BENE_SMI_CVRAGE_TOT_MONS']
Sample data:
        DESYNPUF_ID  BENE_BIRTH_DT  BENE_DEATH_DT  BENE_SEX_IDENT_CD  BENE_RACE_CD  BENE_ESRD_IND  SP_STATE_CODE  BENE_COUNTY_CD
0  00013D2EFD8E45D1       19230501            NaN                  1             1              0             26             950
1  00016F745862898F       19430101            NaN                  1             1              0             39             230
======================================================================
File: sample1_1.csv | Total Shape: (100, 142)
Columns (first 10 of 142): ['DESYNPUF_ID', 'CLM_ID', 'CLM_FROM_DT', 'CLM_THRU_DT', 'ICD9_DGNS_CD_1', 'ICD9_DGNS_CD_2', 'ICD9_DGNS_CD_3', 'ICD9_DGNS_CD_4', 'ICD9_DGNS_CD_5', 'ICD9_DGNS_CD_6']
Sample data:
        DESYNPUF_ID           CLM_ID  CLM_FROM_DT  CLM_THRU_DT  ICD9_DGNS_CD_1  ICD9_DGNS_CD_2  ICD9_DGNS_CD_3  ICD9_DGNS_CD_4
0  00013D2EFD8E45D1  887733386680966     20090725     20090725            7245          7244.0          6272.0             NaN
1  00013D2EFD8E45D1  887213386947664     20091014     20091014            3598         27541.0             NaN             NaN
======================================================================
File: sample1_2.csv | Total Shape: (100, 142)
Columns (first 10 of 142): ['DESYNPUF_ID', 'CLM_ID', 'CLM_FROM_DT', 'CLM_THRU_DT', 'ICD9_DGNS_CD_1', 'ICD9_DGNS_CD_2', 'ICD9_DGNS_CD_3', 'ICD9_DGNS_CD_4', 'ICD9_DGNS_CD_5', 'ICD9_DGNS_CD_6']
Sample data:
        DESYNPUF_ID           CLM_ID  CLM_FROM_DT  CLM_THRU_DT ICD9_DGNS_CD_1  ICD9_DGNS_CD_2  ICD9_DGNS_CD_3  ICD9_DGNS_CD_4
0  7F1460C68FD409E9  887963386407821     20080722     20080722          51889             NaN             NaN             NaN
1  7F1460C68FD409E9  887953386839798     20080718     20080723           2519          4148.0         72887.0         78060.0
======================================================================
File: sample1_3.csv | Total Shape: (100, 81)
Columns (first 10 of 81): ['DESYNPUF_ID', 'CLM_ID', 'SEGMENT', 'CLM_FROM_DT', 'CLM_THRU_DT', 'PRVDR_NUM', 'CLM_PMT_AMT', 'NCH_PRMRY_PYR_CLM_PD_AMT', 'AT_PHYSN_NPI', 'OP_PHYSN_NPI']
Sample data:
        DESYNPUF_ID           CLM_ID  SEGMENT  CLM_FROM_DT  CLM_THRU_DT PRVDR_NUM  CLM_PMT_AMT  NCH_PRMRY_PYR_CLM_PD_AMT
0  00013D2EFD8E45D1  196661176988405        1   20100312.0   20100313.0    2600GD       4000.0                       0.0
1  00016F745862898F  196201177000368        1   20090412.0   20090418.0    3900MB      26000.0                       0.0
======================================================================
File: sample1_4.csv | Total Shape: (100, 76)
Columns (first 10 of 76): ['DESYNPUF_ID', 'CLM_ID', 'SEGMENT', 'CLM_FROM_DT', 'CLM_THRU_DT', 'PRVDR_NUM', 'CLM_PMT_AMT', 'NCH_PRMRY_PYR_CLM_PD_AMT', 'AT_PHYSN_NPI', 'OP_PHYSN_NPI']
Sample data:
        DESYNPUF_ID           CLM_ID  SEGMENT  CLM_FROM_DT  CLM_THRU_DT PRVDR_NUM  CLM_PMT_AMT  NCH_PRMRY_PYR_CLM_PD_AMT
0  00013D2EFD8E45D1  542192281063886        1   20080904.0   20080904.0    2600RA         50.0                       0.0
1  00016F745862898F  542272281166593        1   20090602.0   20090602.0    3901GS         30.0                       0.0
======================================================================
File: sample1_5.csv | Total Shape: (100, 8)
Columns (first 10 of 8): ['DESYNPUF_ID', 'PDE_ID', 'SRVC_DT', 'PROD_SRVC_ID', 'QTY_DSPNSD_NUM', 'DAYS_SUPLY_NUM', 'PTNT_PAY_AMT', 'TOT_RX_CST_AMT']
Sample data:
        DESYNPUF_ID           PDE_ID   SRVC_DT  PROD_SRVC_ID  QTY_DSPNSD_NUM  DAYS_SUPLY_NUM  PTNT_PAY_AMT  TOT_RX_CST_AMT
0  00013D2EFD8E45D1  233664490397622  20080103     247037252            30.0              20          10.0           120.0
1  00013D2EFD8E45D1  233644490171972  20080105     223039502            10.0              10           0.0             0.0
======================================================================
File: sample1_6.csv | Total Shape: (100, 32)
Columns (first 10 of 32): ['DESYNPUF_ID', 'BENE_BIRTH_DT', 'BENE_DEATH_DT', 'BENE_SEX_IDENT_CD', 'BENE_RACE_CD', 'BENE_ESRD_IND', 'SP_STATE_CODE', 'BENE_COUNTY_CD', 'BENE_HI_CVRAGE_TOT_MONS', 'BENE_SMI_CVRAGE_TOT_MONS']
Sample data:
        DESYNPUF_ID  BENE_BIRTH_DT  BENE_DEATH_DT  BENE_SEX_IDENT_CD  BENE_RACE_CD  BENE_ESRD_IND  SP_STATE_CODE  BENE_COUNTY_CD
0  00013D2EFD8E45D1       19230501            NaN                  1             1              0             26             950
1  00016F745862898F       19430101            NaN                  1             1              0             39             230
======================================================================
File: sample1_7.csv | Total Shape: (100, 32)
Columns (first 10 of 32): ['DESYNPUF_ID', 'BENE_BIRTH_DT', 'BENE_DEATH_DT', 'BENE_SEX_IDENT_CD', 'BENE_RACE_CD', 'BENE_ESRD_IND', 'SP_STATE_CODE', 'BENE_COUNTY_CD', 'BENE_HI_CVRAGE_TOT_MONS', 'BENE_SMI_CVRAGE_TOT_MONS']
Sample data:
        DESYNPUF_ID  BENE_BIRTH_DT  BENE_DEATH_DT  BENE_SEX_IDENT_CD  BENE_RACE_CD BENE_ESRD_IND  SP_STATE_CODE  BENE_COUNTY_CD
0  00013D2EFD8E45D1       19230501            NaN                  1             1             0             26             950
1  00016F745862898F       19430101            NaN                  1             1             Y             39             230


```

```python
# Let's inspect the dates and columns in detail
print("File mapping verification:")
for f in sorted(glob.glob('sample1_*.csv')):
    df = pd.read_csv(f)
    print(f"\n--- {f} ---")
    print(f"Shape: {df.shape}")
    cols = df.columns.tolist()
    if 'CLM_ADMSN_DT' in cols:
        print("Type: INPATIENT CLAIMS (has CLM_ADMSN_DT, NCH_BENE_DSCHRG_DT, CLM_DRG_CD)")
    elif 'PDE_ID' in cols:
        print("Type: PRESCRIPTION DRUG EVENTS (has PDE_ID, SRVC_DT, PROD_SRVC_ID, DAYS_SUPLY_NUM, TOT_RX_CST_AMT)")
    elif 'LINE_NCH_PMT_AMT_1' in cols or len(cols) == 142:
        print("Type: CARRIER CLAIMS (Part B physician/lab claims, has CLM_FROM_DT, HCPCS codes)")
    elif 'NCH_BENE_PTB_DDCTBL_AMT' in cols or ('PRVDR_NUM' in cols and 'CLM_ADMSN_DT' not in cols):
        print("Type: OUTPATIENT CLAIMS (has PRVDR_NUM, CLM_FROM_DT, HCPCS codes)")
    elif 'BENE_BIRTH_DT' in cols:
        # Check year differences in reimbursement or coverage
        print("Type: BENEFICIARY SUMMARY (Demographics & Chronic Conditions)")
        print(f"Sample row 1 IP spend: {df.iloc[0]['MEDREIMB_IP']}, OP: {df.iloc[0]['MEDREIMB_OP']}")


```

```text
File mapping verification:

--- sample1_0.csv ---
Shape: (100, 32)
Type: BENEFICIARY SUMMARY (Demographics & Chronic Conditions)
Sample row 1 IP spend: 0.0, OP: 50.0

--- sample1_1.csv ---
Shape: (100, 142)
Type: CARRIER CLAIMS (Part B physician/lab claims, has CLM_FROM_DT, HCPCS codes)

--- sample1_2.csv ---
Shape: (100, 142)
Type: CARRIER CLAIMS (Part B physician/lab claims, has CLM_FROM_DT, HCPCS codes)

--- sample1_3.csv ---
Shape: (100, 81)
Type: INPATIENT CLAIMS (has CLM_ADMSN_DT, NCH_BENE_DSCHRG_DT, CLM_DRG_CD)

--- sample1_4.csv ---
Shape: (100, 76)
Type: OUTPATIENT CLAIMS (has PRVDR_NUM, CLM_FROM_DT, HCPCS codes)

--- sample1_5.csv ---
Shape: (100, 8)
Type: PRESCRIPTION DRUG EVENTS (has PDE_ID, SRVC_DT, PROD_SRVC_ID, DAYS_SUPLY_NUM, TOT_RX_CST_AMT)

--- sample1_6.csv ---
Shape: (100, 32)
Type: BENEFICIARY SUMMARY (Demographics & Chronic Conditions)
Sample row 1 IP spend: 0.0, OP: 0.0

--- sample1_7.csv ---
Shape: (100, 32)
Type: BENEFICIARY SUMMARY (Demographics & Chronic Conditions)
Sample row 1 IP spend: 4000.0, OP: 0.0


```

```python
# Let's inspect carrier and pde data for patient 00016F745862898F across inpatient stays
inp = pd.read_csv('sample1_3.csv')
pde = pd.read_csv('sample1_5.csv')
car1 = pd.read_csv('sample1_1.csv')
car2 = pd.read_csv('sample1_2.csv')
car = pd.concat([car1, car2], ignore_index=True)
op = pd.read_csv('sample1_4.csv')

p_id = '00016F745862898F'
p_inp = inp[inp['DESYNPUF_ID']==p_id][['DESYNPUF_ID', 'CLM_ID', 'CLM_ADMSN_DT', 'NCH_BENE_DSCHRG_DT', 'CLM_DRG_CD', 'ADMTNG_ICD9_DGNS_CD']]
print("Inpatient stays for patient:")
print(p_inp)

p_pde = pde[pde['DESYNPUF_ID']==p_id][['DESYNPUF_ID', 'SRVC_DT', 'PROD_SRVC_ID', 'DAYS_SUPLY_NUM', 'TOT_RX_CST_AMT']]
print("\nPDE fills for patient:")
print(p_pde)

p_car = car[car['DESYNPUF_ID']==p_id][['DESYNPUF_ID', 'CLM_ID', 'CLM_FROM_DT', 'HCPCS_CD_1', 'LINE_NCH_PMT_AMT_1']].head(10)
print("\nCarrier visits for patient (sample):")
print(p_car)


```

```text
Inpatient stays for patient:
        DESYNPUF_ID           CLM_ID  CLM_ADMSN_DT  NCH_BENE_DSCHRG_DT  CLM_DRG_CD ADMTNG_ICD9_DGNS_CD
1  00016F745862898F  196201177000368      20090412            20090418         201                7866
2  00016F745862898F  196661177015632      20090831            20090902         750                6186
3  00016F745862898F  196091176981058      20090917            20090920         883               29590
4  00016F745862898F  196261176983265      20100626            20100701         983                5849

PDE fills for patient:
Empty DataFrame
Columns: [DESYNPUF_ID, SRVC_DT, PROD_SRVC_ID, DAYS_SUPLY_NUM, TOT_RX_CST_AMT]
Index: []

Carrier visits for patient (sample):
         DESYNPUF_ID           CLM_ID  CLM_FROM_DT HCPCS_CD_1  LINE_NCH_PMT_AMT_1
5   00016F745862898F  887523386668713     20081004      29405                50.0
6   00016F745862898F  887793388522804     20081008      76700                 0.0
7   00016F745862898F  887783385091632     20081009      96372                80.0
8   00016F745862898F  887953385848149     20081020      99231                50.0
9   00016F745862898F  887423388326030     20081209      99284                30.0
10  00016F745862898F  887383388842050     20090105      85025                20.0
11  00016F745862898F  887783384850257     20090113      00120                50.0
12  00016F745862898F  887293389131196     20090117      99213                 0.0
13  00016F745862898F  887523385536820     20090308      99254                10.0
14  00016F745862898F  887683387620011     20090314      99213                50.0


```

```python
# Check carrier visits post discharge for 20090418 and 20090902
p_car_all = car[car['DESYNPUF_ID']==p_id].copy()
p_car_all['CLM_FROM_DT'] = pd.to_datetime(p_car_all['CLM_FROM_DT'].astype(str))
print("Carrier visits in 2009 for patient:")
print(p_car_all[p_car_all['CLM_FROM_DT'].dt.year == 2009][['CLM_ID', 'CLM_FROM_DT', 'HCPCS_CD_1', 'LINE_NCH_PMT_AMT_1', 'ICD9_DGNS_CD_1']])


```

```text
Carrier visits in 2009 for patient:
             CLM_ID CLM_FROM_DT HCPCS_CD_1  LINE_NCH_PMT_AMT_1 ICD9_DGNS_CD_1
10  887383388842050  2009-01-05      85025                20.0           1628
11  887783384850257  2009-01-13      00120                50.0          V5867
12  887293389131196  2009-01-17      99213                 0.0           2723
13  887523385536820  2009-03-08      99254                10.0           7870
14  887683387620011  2009-03-14      99213                50.0          78900
15  887693385935201  2009-03-24      99213                 0.0          28249
16  887433386151111  2009-03-30      99213                70.0           4019
17  887743388182774  2009-04-15      99215                50.0           4011
18  887903389160104  2009-05-11      99222               120.0           V561
19  887433388731696  2009-05-16      99213                50.0           V568
20  887853388412950  2009-06-05      99284                40.0           7224
21  887603386081276  2009-06-21      90862               150.0          29524
22  887443385121084  2009-07-03      99214                50.0           4271
23  887453384924494  2009-07-16      A0427                80.0          78965
24  887713388064954  2009-07-31      80061                 0.0           2788
25  887243387711309  2009-08-11      90862                40.0          29625
26  887023387989281  2009-08-24      72148                70.0          72190
27  887243387365395  2009-10-01      99212                50.0           0020
28  887873386493630  2009-10-05      72131                50.0           7222
29  887253385863058  2009-10-29      99223                 0.0          56081
30  887783386404610  2009-11-11      93010                10.0          42769
31  887813386861087  2009-12-02      99214                 0.0           1991
32  887753386337995  2009-12-06      99213                80.0          V8746


```

These eight sample files provide the necessary multi-table Medicare claims data to construct the **Preventra Post-Discharge Readmission Trend Monitoring** system.

Together, they span **Inpatient baseline stays, Part D pharmacy events, Part B physician/ED visits, Outpatient hospital care, and longitudinal Beneficiary summaries**, providing the static and dynamic signals required by the proposal.

---

### 1. Mapping the 8 Sample Files to Preventra Requirements

| File Name | CMS Data Source | Content & Identifiers | Role in Weekly Trend Monitoring |
| --- | --- | --- | --- |
| **`sample1_3.csv`** | **Inpatient Claims** | `DESYNPUF_ID`, `CLM_ID`, `CLM_ADMSN_DT`, `NCH_BENE_DSCHRG_DT`, `CLM_DRG_CD`, `ICD9_DGNS_CD_1..10`, `ICD9_PRCDR_CD_1..6` | **Index Discharge ($t_0$) & Ground Truth Anchor:**<br>

<br>• Defines the discharge event ($t_0$) initiating the 30–90 day recovery window.

<br>

<br>• Establishes baseline stay acuity (DRG, LOS, surgical codes).<br>

<br>• Subsequent admission timestamp defines the true readmission outcome. |
| **`sample1_0.csv`**<br>

<br>**`sample1_6.csv`**<br>

<br>**`sample1_7.csv`** | **Beneficiary Summaries**<br>

<br>(2008, 2009, 2010) | `DESYNPUF_ID`, `BENE_BIRTH_DT`, `BENE_SEX_IDENT_CD`, `BENE_RACE_CD`, `SP_CHF`, `SP_COPD`, `SP_DIABETES`, `SP_CHRNKIDN`, `BENE_DEATH_DT` | **Baseline Patient Profile & Frailty:**<br>

<br>• Provides fixed demographic and 11 baseline comorbidity flags.

<br>

<br>• Mortality tracking excludes non-informative cases where patient died during the index stay. |
| **`sample1_5.csv`** | **Prescription Drug Events (Part D)** | `DESYNPUF_ID`, `PDE_ID`, `SRVC_DT`, `PROD_SRVC_ID`, `QTY_DSPNSD_NUM`, `DAYS_SUPLY_NUM`, `TOT_RX_CST_AMT` | **Dynamic Post-Discharge Medication Adherence:**<br>

<br>• **Discharge Fills (Week 1):** Captures whether essential discharge prescriptions were filled within 7 days of leaving the hospital.

<br>

<br>• **Refill Gaps & Supply Runouts (Weeks 2–12):** Computes medication possession ratio (MPR) and refill activity across rolling weekly windows.

 |
| **`sample1_1.csv`**<br>

<br>**`sample1_2.csv`** | **Carrier Claims (Part B 1A & 1B)** | `DESYNPUF_ID`, `CLM_ID`, `CLM_FROM_DT`, `HCPCS_CD_1..45`, `LINE_NCH_PMT_AMT_1..45` | **Follow-up Attendance & Interim Destabilization:**<br>

<br>• **PCP/Specialist Follow-up:** Tracks outpatient Evaluation & Management (E&M) codes (HCPCS `99211–99215`) within 7, 14, 21, and 28 days post-discharge.

<br>

<br>• **Interim Emergency Department (ED) Touches:** Detects ED visits (HCPCS `99281–99285`) or ambulance calls (HCPCS `A0427`) that did not result in an immediate inpatient stay.

 |
| **`sample1_4.csv`** | **Outpatient Claims** | `DESYNPUF_ID`, `CLM_ID`, `CLM_FROM_DT`, `PRVDR_NUM`, `CLM_PMT_AMT` | **Post-Discharge Hospital Utilization:**<br>

<br>• Detects outpatient hospital-based observation stays, imaging, and ambulatory lab services post-discharge.

 |

---

### 2. Longitudinal Data Joining & Windowing Strategy

Rather than flattening every hospital stay into a single static row, the data is joined into a **weekly observation panel** for every active patient recovery week $w \in \{1, 2, \dots, W\}$:

```
[Inpatient Index Stay (t0)] ──► [Week 1 Snapshot (t=7d)] ──► [Week 2 Snapshot (t=14d)] ──► ...
          │                                 │                                 │
   Static Baseline:                  Post-Discharge:                   Post-Discharge:
   Demographics + DRGs               • Week 1 Med Fill (PDE)           • Follow-up Visit Kept (Carrier)
   + Chronic Conditions              • No Follow-up Visit (Carrier)    • Cumulative Refill Gap (PDE)

```

```
                 Inpatient Index Stay (t0 = Discharge Date)
                                    │
                                    ├───────────────────────────────┐
                                    │                               │
                       Pre-Discharge Window               Post-Discharge Window
                       (Static Baseline)                  (Dynamic Rolling Weeks)
                                │                                   │
              ┌─────────────────┴─────────────────┐                 │
              ▼                                   ▼                 │
     Beneficiary Summary                 Inpatient Claims           │
     (Age, Sex, Comorbidities)           (DRG, LOS, ICD-9 Dx)       │
                                                                    │
                                    ┌───────────────────────────────┴───────────────────────────────┐
                                    ▼                                                               ▼
                          Carrier Claims (Part B)                                         PDE (Part D Pharmacy)
                 (Weekly Post-Discharge PCP & ED Visits)                        (Weekly Post-Discharge Fills & Refill Gaps)

```

#### Joining Logic:

1. **Primary Entity:** Each index discharge row in `sample1_3.csv` establishes patient $i$ and discharge timestamp $t_0$.
2. **Static Join:** Left join annual demographics and chronic conditions from the stacked beneficiary tables (`sample1_0`, `sample1_6`, `sample1_7`) on `[DESYNPUF_ID, YEAR(t_0)]`.
3. **Weekly Dynamic Slice:** For each recovery week $w \in \{1, 2, 3, 4, \dots\}$ where $t_w = t_0 + 7w$ days:


* Filter Carrier (`sample1_1`, `sample1_2`) for records with $t_0 < \text{CLM\_FROM\_DT} \le t_w$.
* Filter PDE (`sample1_5`) for fills with $t_0 < \text{SRVC\_DT} \le t_w$.
* Filter Outpatient (`sample1_4`) for encounters with $t_0 < \text{CLM\_FROM\_DT} \le t_w$.



---

### 3. Engineering Preventra-Conforming Features

At each weekly scoring cadence $w$, combine fixed discharge features with cumulative post-discharge recovery indicators:

```python
# -------------------------------------------------------------------------
# Dynamic Feature Schema at Week w (e.g., w = 1, 2, 3, 4)
# -------------------------------------------------------------------------
feature_vector_week_w = {
    # 1. Fixed Baseline Features (at Discharge t0)
    "AGE_AT_ADMISSION": age,
    "TOTAL_CHRONIC_CONDITIONS": chronic_count,
    "FRAILTY_SCORE": frailty_score,
    "CLM_DRG_CD": drg_code,
    "LENGTH_OF_STAY": los,
    "IS_ZERO_DEDUCTIBLE": zero_deductible_flag,
    # 2. Post-Discharge Physician Follow-up Attendance (from Carrier/Outpatient)
    "POST_DSCHRG_PCP_VISIT_COUNT": cumulative_pcp_visits_up_to_w,  # HCPCS 99211-99215
    "HAD_PCP_FOLLOWUP_BY_WEEK_W": int(cumulative_pcp_visits_up_to_w > 0),
    # 3. Post-Discharge Acute Destabilization (from Carrier/Outpatient)
    "POST_DSCHRG_INTERIM_ED_VISITS": cumulative_ed_visits_up_to_w,  # HCPCS 99281-99285
    "POST_DSCHRG_AMBULANCE_CALLS": cumulative_ambulance_events,  # HCPCS A0427
    # 4. Post-Discharge Pharmacy Adherence & Refills (from PDE)
    "POST_DSCHRG_TOTAL_RX_FILLS": cumulative_rx_fills_up_to_w,
    "POST_DSCHRG_DAYS_SUPPLY_COVERED": cumulative_days_supply,
    "MEDICATION_REFILL_GAP_DAYS": max(
        0, (7 * w) - cumulative_days_supply
    ),  # Uncovered recovery days
    "POST_DSCHRG_PHARMACY_SPEND": cumulative_rx_cost_up_to_w,
    # 5. Recovery Timeline Anchor
    "DAYS_IN_RECOVERY_WINDOW": 7 * w,
}

```

---

### 4. Trend Detection & Action Triggering Layer

Once weekly risk scores $\hat{S}_w = P(\text{Readmission} \mid \mathbf{x}_w)$ are generated, the trend engine evaluates trajectory direction to drive clinical follow-up:

```
                                  Weekly Risk Score: S(w)
                                             │
                        ┌────────────────────┴────────────────────┐
                        ▼                                         ▼
            Delta: ΔS = S(w) - S(w-1)                3-Week Trajectory Slope
                        │                                         │
       ┌────────────────┴────────────────┐                        │
       ▼                                 ▼                        │
ΔS ≥ +0.15 (or Risk-Band Jump)     ΔS > +0.03 & Slope > 0         ▼
       │                                 │                  Slope < -0.02
       ▼                                 ▼                        │
[ SHARP INCREASE ALERT ]         [ INCREASING ALERT ]             ▼
Escalate immediately; same       Auto-alert care coordinator;     [ DECREASING TREND ]
urgency tier as in-hospital      prioritize outreach call;        Log recovery on track;
high-risk alert[cite: 1].       audit adherence gaps[cite: 1].  reduce check-in cadence[cite: 1].

```

| Trend State

 | Mathematical Condition | Triggered Care-Team Action

 |
| --- | --- | --- |
| **Increasing**<br> | $\Delta S_w = S_w - S_{w-1} > +0.03$ over 2 consecutive weeks, or slope $> 0$.

 | Auto-generate alert to care coordinator; prioritize outreach call; review adherence and missed visits for root cause.

 |
| **Sharp Increase**<br> | $S_w - S_{w-1} \ge +0.15$ (large single-week jump) or risk band jump.

 | Immediate clinical escalation (same urgency as an in-hospital high-risk alert).

 |
| **Decreasing**<br> | $S_w < S_{w-1} - 0.02$ (risk falling week over week).

 | Log positive recovery trajectory; consider reducing check-in frequency as recovery stabilizes.

 |
| **Stable / Flat**<br> | $\vert{}\Delta S_w\vert{} \le 0.02$ (change within normal noise).

 | Continue routine weekly monitoring; no care-team intervention needed.

 |
| **Window Closes**<br> | $w = 12$ ($90\text{ days}$) without escalation.

 | Close out monitoring; archive trend trajectory as successful recovery record.

 |

---

### Conclusion

These 8 files contain all necessary data streams to implement Preventra's proposed system. They support extracting baseline discharge features, tracking weekly post-discharge refill adherence and physician visits, calculating weekly risk updates, and classifying score trajectories into the proposal's action tiers.