# GLP-1 Adherence — Data Collection, Training Pipeline, and Data Dictionary

This document captures everything done to go from raw public-health data sources
to the trained Gradient Boosting model that predicts GLP-1 therapy adherence,
plus the downstream segmentation, survival, and cost-effectiveness layers built
on top of the model. It is intended as the single read-once-and-understand
reference for planning the next phase of work.

---

## 1. Project Goal

Predict whether a patient is likely to remain adherent to a GLP-1 receptor
agonist (e.g. semaglutide, tirzepatide, liraglutide, dulaglutide) over a
~180-day window, and produce per-patient, per-segment, and population-level
insights that a payer / health system can act on (risk triage, intervention
ROI, cost-effectiveness vs. comparators).

Target variable: `is_adherent` (binary, 1 = adherent, 0 = dropout).

---

## 2. Data Sources

All raw data is public. Each source contributes a different signal layer that
the fusion pipeline later combines into one patient-level training table.

| Source | Role | Script | Key Output |
|---|---|---|---|
| **NHANES** (2017–2018 + 2021–2023 cycles) | Patient demographics + clinical baseline (BMI, HbA1c, BP, cholesterol, diabetes Dx) | [Data_Collection/NHANES/nhanes.py](../Data_Collection/NHANES/nhanes.py) | `nhanes_clinical_baseline.csv` |
| **MEPS** (H248A prescribed meds + H251 consolidated) | Real out-of-pocket cost + insurance coverage by demographics | [Data_Collection/MEPS/meps.py](../Data_Collection/MEPS/meps.py) | `meps_glp1_cost_analysis.csv` |
| **FAERS** (FDA openFDA event API) | Real-world adverse event frequency per GLP-1 generic | [Data_Collection/FAERS/fares.py](../Data_Collection/FAERS/fares.py) | `faers_glp1_side_effects.csv` |
| **ClinicalTrials.gov** API v2 (SUSTAIN, STEP, SURMOUNT families) | Trial-grade AE rates, baselines, outcomes | [Data_Collection/ClinicalTrials/clinical_trials.py](../Data_Collection/ClinicalTrials/clinical_trials.py) | `trial_metadata.csv`, `trial_outcomes.csv`, `trial_adverse_events.csv`, `trial_baselines.csv` |
| **CMS Medicare Part D** (Prescribers by Provider & Drug, 2023) | Prescriber-level refill continuity → system reliability signal | [Data_Collection/Medicare Part D Prescribers - by Provider and Drug/glp1_cms_processor.py](../Data_Collection/Medicare%20Part%20D%20Prescribers%20-%20by%20Provider%20and%20Drug/glp1_cms_processor.py) | `glp1_cms_clean_v2.csv`, `summary_by_drug.csv`, `low_refill_prescribers.csv`, etc. |

### 2.1 NHANES details
- Two cycles combined because 2021–2023 alone yielded only ~3.4k eligible
  candidates (target was ≥5k for stable ML).
- Files used per cycle: `DEMO_*.XPT`, `BMX_*.XPT`, `GHB_*.XPT`,
  `DIQ_*.XPT`, `BPX_*.XPT`, `TCHOL_*.XPT`.
- A `cycle` column is added to prevent `SEQN` collisions across cycles.
- Drop rule is intentionally relaxed: keep a row if **either** BMI or HbA1c
  is present (drop only if both missing).

### 2.2 MEPS details
- MEPS stores **generic** drug names (SEMAGLUTIDE, TIRZEPATIDE…), not brand
  names. The script filters on generics using `str.contains` and adds a clean
  `molecule` column so fusion lookups don’t silently return 0 rows. This was
  the most painful early bug.
- Cost columns: prefers `RX*23X` (X-suffix), falls back to `RX*23`. Produces
  `out_of_pocket`, `insurance_paid`, `total_drug_cost`, plus
  `patient_pay_ratio` and `high_cost_burden` (>$50 OOP).

### 2.3 FAERS details
- Pulls top reactions per generic via the openFDA `count` query. Output is
  a tall table of `(drug, side_effect, frequency)` used downstream to compute
  a normalized `real_world_risk` per molecule.

### 2.4 ClinicalTrials details
- Pulls all SUSTAIN-1..10, STEP-1..5, SURMOUNT-1..4 (NCT IDs hardcoded).
- Extracts: study metadata, outcome measurements per arm, serious + other
  AEs per arm, baseline characteristics per arm.
- A trial is mapped to a molecule by series prefix (STEP/SUSTAIN →
  semaglutide, SURMOUNT → tirzepatide, AWARD → dulaglutide, LEAD →
  liraglutide).

### 2.5 CMS Medicare Part D details
- Source CSV: `MUP_DPR_RY25_P04_V10_DY23_NPIBN.csv` (one row per
  prescriber × drug).
- Two non-obvious quirks handled in the script:
  1. **CMS bottom-codes** 30-day fills at 1.0, so a fixed `<0.8` refill
     threshold flags nothing. Replaced with a **per-drug 25th percentile**
     threshold (`Low_Refill_Flag`).
  2. **Beneficiary counts <11 are suppressed** for privacy. These rows are
     kept for cost/volume signal but excluded from per-beneficiary averages
     via a `Benes_Suppressed` flag.
- Engineered features: `Refill_Continuity_Ratio`, `Avg_Cost_Per_Bene`,
  `Avg_Days_On_Therapy`, `Low_Refill_Flag`.
- Outputs include `summary_by_drug.csv` (used in fusion Layer 3) and
  `low_refill_prescribers.csv` (provider-risk lookup).

---

## 3. Fusion Pipeline (raw sources → ML-ready table)

The fusion pipeline is intentionally split into stacked layers so each signal
type can be debugged independently. All scripts live in [Fusion/](../Fusion/).

```
NHANES + MEPS                   →  Layer 1  →  FUSION_LAYER_1.csv
+ FAERS + ClinicalTrials        →  Layer 2  →  FUSION_LAYER_2.csv
+ CMS Medicare Part D           →  Layer 3  →  FUSION_LAYER_3.csv
+ behavioral simulation         →  final.py →  FINAL_GLP1_MODEL_DATA.csv
```

### 3.1 Layer 1 — Patient baseline + cost
File: [Fusion/layer_1.py](../Fusion/layer_1.py)

- **Eligibility filter (3 pathways, OR-combined):**
  1. BMI ≥ 30 (obesity indication)
  2. BMI ≥ 27 AND HbA1c ≥ 5.7 (overweight + pre-diabetic)
  3. `DIQ010 == 1` (confirmed diabetes diagnosis, regardless of BMI/HbA1c)
- Adds `gender_female`, `age_bin` (8 bins).
- Randomly assigns a `molecule` per patient from {SEMAGLUTIDE, TIRZEPATIDE,
  DULAGLUTIDE, LIRAGLUTIDE} (seeded). This is a known limitation — see §7.
- Builds a 3-tier OOP cost lookup:
  - Tier 1: (`age_bin`, `gender`, `molecule`) mean OOP from MEPS
  - Tier 2: molecule-level mean OOP from MEPS
  - Tier 3: hardcoded industry fallback ($80–$200)
  Records the tier used in `cost_lookup_tier`.
- Computes `income_cost_pressure = avg_oop_cost / (INDFMPIR + 0.1)`, with
  missing PIR imputed by (age_bin, gender) median, then clipped at the
  99th percentile.

### 3.2 Layer 2 — Biological friction
File: [Fusion/layer_2.py](../Fusion/layer_2.py)

- FAERS: sums event frequency per drug → `real_world_risk` (max-normalized).
- ClinicalTrials: filters AEs to GI terms (Nausea/Vomiting/Diarrhea/GI),
  computes `ae_rate = num_events / num_at_risk`, aggregates to molecule level
  via series-prefix mapping to avoid fan-out on merge.
- `bio_friction = (real_world_risk + ae_rate) / 2`, median-imputed for nulls.

### 3.3 Layer 3 — System reliability + drug generation
File: [Fusion/layer_3.py](../Fusion/layer_3.py)

- Loads CMS `summary_by_drug.csv` and `low_refill_prescribers.csv`.
- Brand→molecule mapping covers all brands actually present in CMS output
  (Ozempic, Wegovy, Rybelsus, Mounjaro, Zepbound, Trulicity, Victoza variants,
  Saxenda, Soliqua, Xultophy, Bydureon Bcise, Byetta).
- Computes per-molecule:
  - `drug_refill_avg` (mean refill continuity from CMS)
  - `provider_risk_score` (mean Low_Refill_Flag rate)
- `system_refill_score = drug_refill_avg - 0.2 * provider_risk_score`, with
  ±5% seeded uniform noise applied per patient (for downstream variance).
- Adds `drug_generation` (1=liraglutide, 2=dulaglutide/semaglutide,
  3=tirzepatide) and `is_newer_drug = (drug_generation >= 2)`.

### 3.4 Final — Behavioral simulation
File: [Fusion/final.py](../Fusion/final.py)

The `is_adherent` label is **simulated** from a transparent behavioral
equation, then noise is added. This is deliberate: there is no public,
patient-level adherence outcome dataset for GLP-1s, so we constructed a
realistic surrogate label whose drivers match published evidence.

```
base_prob = 0.65
p_adherent =
    base_prob
  - 0.40 * income_cost_pressure_norm   # financial pressure
  - 0.30 * bio_friction_norm           # side-effect friction
  - 0.05 * is_newer_drug               # PA / access friction
  + 0.10 * system_refill_score_norm    # provider/system support
  + 0.15 * motivation                  # 0.5*BMI_norm + 0.5*HbA1c_norm
  + 0.05 * comorbidity_score_norm      # disease-severity motivation
  + N(0, 0.10)                         # human noise
is_adherent = (final_prob > 0.5)
```

Output: `FINAL_GLP1_MODEL_DATA.csv` (16 columns, ~6.5k rows pre-cleanup).

---

## 4. Data Dictionary — `GLP1_CLEANED.csv` (model training input)

This is the dataset that goes into the model after the cleanup notebook
([Processing/cleanup.ipynb](../Processing/cleanup.ipynb)) has run. Final shape:
**7,566 rows × 15 columns** (after underage drop, null imputation, BMI
clipping, dead-column removal, and minority upsampling).

| Column | Type | Source layer | Description | Range / values observed |
|---|---|---|---|---|
| `RIDAGEYR` | float | NHANES (Layer 1) | Patient age in years | 18 – 80 (under-18 rows removed in cleanup) |
| `gender_female` | binary | NHANES (Layer 1) | 1 if female, else 0 | {0, 1} |
| `BMXBMI` | float | NHANES (Layer 1) | Body Mass Index | clipped 18.5 – 70.0 |
| `LBXGH` | float | NHANES (Layer 1) | HbA1c (%) | 3.9 – 17.1, median 5.8 |
| `assigned_molecule` | string | Layer 1 (random, seeded) | GLP-1 generic randomly assigned to each patient | {SEMAGLUTIDE, TIRZEPATIDE, DULAGLUTIDE, LIRAGLUTIDE} ~25% each |
| `drug_generation` | int | Layer 3 | 1=liraglutide (2010), 2=dulaglutide/semaglutide (2014/2017), 3=tirzepatide (2022) | {1, 2, 3} |
| `is_newer_drug` | binary | Layer 3 | 1 if `drug_generation >= 2` | {0, 1} |
| `avg_oop_cost` | float (USD) | Layer 1 (MEPS lookup, 3-tier) | Estimated out-of-pocket cost per fill for the assigned molecule | 2.17 – 424.19, median ≈ 49 |
| `income_cost_pressure` | float | Layer 1 | `avg_oop_cost / (INDFMPIR + 0.1)`, 99th-pct clipped | 0.43 – 366.7 |
| `bio_friction` | float [0–1] | Layer 2 | Average of FAERS real-world risk + trial GI AE rate, median-imputed | 0.237 – 0.566 (per-molecule constant ± noise) |
| `system_refill_score` | float | Layer 3 | CMS drug-level refill avg minus 0.2 × provider risk, ±5% per-row noise | 0.92 – 1.34 |
| `comorbidity_score` | int | NHANES (Layer 1) | Count of {hypertension, dyslipidemia, dysglycemia} | {0, 1, 2} *(hypertension column ended up all zeros — see §7)* |
| `has_dyslipidemia` | binary | NHANES (Layer 1) | Total cholesterol ≥ 200 | {0, 1} |
| `has_dysglycemia` | binary | NHANES (Layer 1) | HbA1c ≥ 5.7 | {0, 1} |
| `is_adherent` | **binary (TARGET)** | Simulated (final.py) | 1 = adherent, 0 = dropout | post-upsample ~47% / 53% |

> **Dropped during cleanup:** `has_hypertension` (zero variance — `BPXOSY1`
> threshold was never met after the merge, leaving the column all 0s).

### Cleanup steps applied (Processing/cleanup.ipynb)
1. Schema validation against the 16 expected columns.
2. Null imputation: `BMXBMI` (40 nulls) and `LBXGH` (383 nulls) filled with
   column median.
3. Drop rows with `RIDAGEYR < 18` (373 rows).
4. Drop zero-variance columns → `has_hypertension` removed.
5. Clip `BMXBMI` to [18.5, 70.0].
6. Upsample the minority `is_adherent==1` class to a 47/53 split (matching
   real-world benchmarks), final shape 7,566 × 15.

---

## 5. Model Training Pipeline

File: [Model/model.ipynb](../Model/model.ipynb)

### 5.1 Preprocessing
- `assigned_molecule` one-hot encoded into `mol_DULAGLUTIDE`,
  `mol_LIRAGLUTIDE`, `mol_SEMAGLUTIDE`, `mol_TIRZEPATIDE`.
- 17 features total (everything except `is_adherent`).
- 80/20 train/test split, stratified on `is_adherent`.
- `StandardScaler` fit on training set only, applied to the 7 continuous
  features: `RIDAGEYR`, `BMXBMI`, `LBXGH`, `avg_oop_cost`,
  `income_cost_pressure`, `bio_friction`, `system_refill_score`. Binary and
  one-hot columns are left as-is.

### 5.2 Models trained

| Model | Hyperparameters | Accuracy | Precision | Recall | F1 | AUC-ROC |
|---|---|---|---|---|---|---|
| **Gradient Boosting v1** (primary) | n_est=200, lr=0.05, depth=4, subsample=0.8 | 0.7985 | 0.8776 | 0.6643 | 0.7562 | 0.8906 |
| Logistic Regression (baseline) | C=1.0, max_iter=1000 | 0.7635 | 0.8352 | 0.6194 | 0.7113 | 0.8386 |
| **Gradient Boosting v2** (final) | v1 + `max_features='sqrt'` to prevent single-feature dominance | similar AUC, more balanced importances | | | | |

### 5.3 Why v2 over v1
A permutation-importance check showed `system_refill_score` dominating every
tree split in v1 (suspected near-leakage given how cleanly it partitions the
target). Re-training with `max_features='sqrt'` forces each split to consider
only a random feature subset, distributing importance across cost / friction
/ clinical signals without sacrificing AUC.

### 5.4 Threshold tuning
Used `precision_recall_curve` to pick the decision threshold that maximizes
F1 while keeping precision **and** recall ≥ 0.75 on the adherent class.
Chosen threshold is persisted with the model in `final_gb_model.pkl`.

### 5.5 Persisted artifact
```python
final_gb_model.pkl = {
    'model':      GradientBoostingClassifier (v2),
    'threshold':  BEST_THRESHOLD,
    'features':   [17 feature names, ordered],
    'scaler':     fitted StandardScaler,
    'scale_cols': [7 continuous cols],
}
```

---

## 6. Downstream Layers (built on top of the model)

These are all inside [Model/model.ipynb](../Model/model.ipynb), keep them in
mind as part of the “work done” when planning next steps — they consume the
trained model and produce dashboard-ready CSVs.

### 6.1 SHAP explainability
- `shap.TreeExplainer` on v2, computed for the full test set.
- Outputs: global summary plot, mean-abs bar plot, waterfall for highest-risk
  patient, plus `shap_patient_drivers.csv` (top-3 plain-language drivers per
  patient, with direction) and `shap_values_test.npy` (raw).
- `FEATURE_LABELS` dict maps internal feature names → physician-readable
  phrases (e.g. `system_refill_score` → "Provider & pharmacy refill
  reliability").

### 6.2 K-Means segmentation (k=4)
- Clustering features (12, no target, no one-hot): age, BMI, HbA1c, avg_oop_cost,
  income_cost_pressure, bio_friction, system_refill_score, comorbidity_score,
  drug_generation, is_newer_drug, has_dyslipidemia, has_dysglycemia.
- StandardScaler fit on the full cleaned df before clustering.
- k chosen at 4 (elbow + clinical interpretability; silhouette was flat
  across k=2..8, max delta 0.04).
- Manually corrected labels:
  - Cluster 0 — Low Urgency Dropout Risk
  - Cluster 1 — Financial Barrier Dropout Risk
  - Cluster 2 — Low Friction Strong Adherer
  - Cluster 3 — Moderate Risk Moderate Adherer
- Outputs: `GLP1_SEGMENTED.csv`, `segment_profiles.csv`,
  `cluster_heatmap.png`, `cluster_pca.png`.

### 6.3 Kaplan-Meier survival
- We don’t have true longitudinal timestamps. `time_to_dropout` is
  synthesized from an **exponential distribution parameterized per cluster**
  by that cluster’s adherence rate (`lambda = -log(adherence) / 180`).
  Adherent patients are right-censored at day 180.
- Important fix already applied: pass features through the trained scaler
  before scoring the full dataset, otherwise raw values fall outside every
  learned tree split and all dropout probabilities collapse to ~0.97.
- KM curves, log-rank test, and 30/60/90/180-day checkpoint dropout rates
  computed per cluster. Outputs: `survival_checkpoints.csv`,
  `kaplan_meier_segments.png`, `GLP1_FINAL_WITH_SURVIVAL.csv`.

### 6.4 Cost-effectiveness engine (CEA / ICER / budget impact)
- Per-molecule trial benchmarks hardcoded from STEP / SUSTAIN / SURMOUNT
  (weight loss %, HbA1c reduction, annual drug cost).
- Comparators: insulin glargine, SGLT2 inhibitor.
- Computes per cluster: avg annual cost, effective weight loss / HbA1c
  reduction (prorated by `time_to_dropout` for dropouts), cost per %
  body-weight lost, cost per HbA1c point, wasted spend per patient.
- ICER vs each comparator, per cluster.
- Budget impact: assumes a 15% relative dropout reduction at $500/patient
  intervention cost, reports net savings per cluster.
- Outputs: `cost_effectiveness.csv`, `icer_by_segment.csv`,
  `budget_impact.csv`.

---

## 7. Known Limitations & Caveats

These should anchor any planning discussion about the next phase.

1. **Target is simulated.** `is_adherent` comes from a transparent behavioral
   equation in `final.py`, not from a real adherence outcome dataset. AUC
   ~0.89 partly reflects how well the model recovers the very equation that
   generated the label. Useful for end-to-end pipeline + dashboard
   demonstration, **not** as a clinical performance claim.
2. **Molecule assignment is random.** Patients are assigned a GLP-1 generic
   uniformly at random, not based on payer/clinical fit. Any "molecule-level"
   finding (ICER differences, segment-by-drug breakdowns) is a function of
   the random assignment + per-molecule benchmark constants, not real
   prescribing behavior.
3. **`system_refill_score` is coarse.** It’s a per-molecule constant with
   ±5% per-patient noise, derived from CMS prescriber-level data — it
   doesn’t actually vary by *this patient’s* provider. It dominated v1
   importances; v2 mitigates this with `max_features='sqrt'`.
4. **`bio_friction` has very low variance.** Effectively a per-molecule
   constant (FAERS + trial AE rates), so it cannot distinguish *patients*
   on the same drug. Min/max in the cleaned data is 0.237–0.566 but
   essentially clustered at four discrete molecule values.
5. **`has_hypertension` was dead.** All zero post-merge, dropped in cleanup.
   `comorbidity_score` therefore tops out at 2, not the documented 3.
6. **MEPS demographics ≠ NHANES patients.** Layer 1 looks up cost from MEPS
   by (age_bin, gender, molecule). The MEPS patient is not the same person
   as the NHANES patient — this is an aggregate cost imputation, not a
   record linkage.
7. **`time_to_dropout` is synthetic.** Exponential per-cluster draw, not
   measured. KM curves are illustrative of the modeled hazard, not real
   patient timelines.
8. **CMS data is 2023.** Drug list and refill behavior may shift
   year-over-year; re-pull with the next release.
9. **Class balance is upsampled, not weighted.** Adherent class was
   resampled (replace=True) to hit 47%. Acceptable for getting a balanced
   training signal but inflates effective N for the minority class —
   metrics are slightly optimistic vs. class-weighted training.
10. **No cross-validation in the notebook.** A single 80/20 stratified split
    + holdout eval. Fine for a prototype, not for reporting.

---

## 8. Pipeline Output Files (quick reference)

| File | Produced by | Purpose |
|---|---|---|
| `nhanes_clinical_baseline.csv` | Data_Collection/NHANES/nhanes.py | Patient clinical baseline (both cycles combined) |
| `meps_glp1_cost_analysis.csv` | Data_Collection/MEPS/meps.py | GLP-1 OOP cost by demographics |
| `faers_glp1_side_effects.csv` | Data_Collection/FAERS/fares.py | Top reactions per generic |
| `trial_metadata.csv`, `trial_outcomes.csv`, `trial_adverse_events.csv`, `trial_baselines.csv` | Data_Collection/ClinicalTrials/clinical_trials.py | SUSTAIN / STEP / SURMOUNT trial data |
| `glp1_cms_clean_v2.csv`, `summary_by_drug.csv`, `summary_by_state_and_drug.csv`, `summary_by_specialty.csv`, `low_refill_prescribers.csv` | Data_Collection/Medicare Part D…/glp1_cms_processor.py | CMS prescriber-level GLP-1 data |
| `FUSION_LAYER_1.csv` | Fusion/layer_1.py | NHANES + MEPS, eligibility-filtered |
| `FUSION_LAYER_2.csv` | Fusion/layer_2.py | + bio_friction |
| `FUSION_LAYER_3.csv` | Fusion/layer_3.py | + system_refill_score, drug_generation |
| `FINAL_GLP1_MODEL_DATA.csv` | Fusion/final.py | + simulated `is_adherent` (16 cols) |
| `GLP1_CLEANED.csv` | Processing/cleanup.ipynb | ML-ready (15 cols, 7,566 rows) |
| `final_gb_model.pkl` | Model/model.ipynb | Trained GB v2 + scaler + threshold + feature order |
| `shap_patient_drivers.csv`, `shap_values_test.npy` | Model/model.ipynb (SHAP) | Per-patient drivers + raw SHAP |
| `GLP1_SEGMENTED.csv`, `segment_profiles.csv` | Model/model.ipynb (K-Means) | Cluster labels + profiles |
| `GLP1_FINAL_WITH_SURVIVAL.csv`, `survival_checkpoints.csv` | Model/model.ipynb (KM) | Survival times + checkpoint dropouts |
| `cost_effectiveness.csv`, `icer_by_segment.csv`, `budget_impact.csv` | Model/model.ipynb (CEA) | Economic outputs per segment |

---

## 9. Reproduction Order

If starting from scratch on a clean machine (Mongo migration aside):

1. Download raw CMS, MEPS, NHANES XPT/XLSX files into their respective
   `Data_Collection/<source>/` folders (paths are hardcoded; see each script).
2. Run, in any order: `nhanes.py`, `meps.py`, `fares.py`,
   `clinical_trials.py`, `glp1_cms_processor.py`.
3. Run fusion in order: `layer_1.py` → `layer_2.py` → `layer_3.py` →
   `final.py`.
4. Run `Processing/cleanup.ipynb` end-to-end → produces `GLP1_CLEANED.csv`.
5. Run `Model/model.ipynb` end-to-end → produces the trained model and all
   downstream segmentation / survival / CEA artifacts.

> Note: as of commit `51dba85` the project migrated CSV-based storage to
> MongoDB Atlas. Some of the file paths above may now be Mongo collections;
> check current `Backend/` and `Fusion/` scripts before re-running.

---

## 10. Consequence Model Layer (Phases 1–2)

The consequence model sits on top of the trained adherence model and answers
the payer-relevant question: *what does dropout cost the system, and what
happens to the patient's metabolic state if they drop?* All parameters are
sourced from [evidence/parameter_registry.csv](evidence/parameter_registry.csv);
audit trail and scope decisions are in [evidence/cea_audit.md](evidence/cea_audit.md)
and [evidence/markov_scope_decision.md](evidence/markov_scope_decision.md).

### 10.1 Downstream Cost Model (Phase 1)

- Per-patient 6-state Markov chain (Controlled / Uncontrolled T2D / CKD /
  ESRD / CV-event-as-stream / Death) parameterized by registry values.
- Annual cycle, 5-year primary horizon, 10-year sensitivity, 3% discount rate.
- Outputs: per-patient `progression_cost.csv` (7,566 rows) with expected
  downstream cost at 5 and 10 years plus primary cost driver.
- Code: [Model/consequence/downstream_cost.py](../Model/consequence/downstream_cost.py),
  [Model/consequence/markov.py](../Model/consequence/markov.py).
- API: `GET /api/consequence/downstream-cost`.

### 10.2a Payer ROI Synthesizer (Phase 3)

- Per-cluster ROI at 1, 3, and 5-year horizons using registry-sourced Markov
  projections (dropout-side and on-therapy-side), model-derived adherence
  probabilities, per-molecule net-of-rebate GLP-1 costs.
- Formula (audit-compliant — see [evidence/cea_audit.md](evidence/cea_audit.md)):
  `expected_downstream = (1−α)·C_dropout + α·C_adherent`;
  `gross_benefit = C_dropout − expected_downstream`;
  `drug_cost = α·D·annuity(t,r) + (1−α)·D·t_drop/365`;
  `net_benefit = gross_benefit − drug_cost − intervention_cost`;
  `ROI = net_benefit / drug_cost`.
- Break-even adherence: minimum α at which annual drug cost equals per-patient
  avoided cost. Returns None when the on-therapy projection is not strictly
  cheaper (program cannot break even at any adherence).
- Intervention cost threshold: `gross_benefit − drug_cost` at 5 years — the
  max spend per patient that keeps ROI ≥ 0.
- Time-to-positive ROI: linearly interpolated year at which the ROI crosses
  zero, computed on a 1..5-year series.
- Outputs:
  - `payer_roi.csv` (per-cluster, 4 rows) — all horizons in wide format.
  - `payer_roi_yearly.csv` (per-cluster × year, 20 rows) — long format for
    the dashboard's time-to-positive line chart.
- Code: [Model/consequence/payer_roi.py](../Model/consequence/payer_roi.py),
  [Model/consequence/roi.py](../Model/consequence/roi.py).
- API: `GET /api/consequence/payer-roi?intervention_cost=<usd>` — ROI is
  recomputed server-side from the caller-supplied intervention cost so the
  dashboard slider works without persisting new documents to Mongo.

### 10.2 Metabolic Rebound Risk Engine (Phase 2)

- Per-patient 12-month HbA1c and BMI trajectory post-dropout, parameterized
  by per-molecule trial efficacy + registry rebound rate (0.10 HbA1c %/month)
  + plateau (66% of the on-therapy gain is regained).
- Per-patient probabilities: new-onset T2D within 12 months (`p_new_t2d_12mo`)
  for pre-DM patients; uncontrolled T2D within 12 months (`p_uncontrolled_12mo`)
  for T2D patients.
- Sensitivity analysis: every patient re-projected at three dropout-timing
  scenarios (early=day 30, median=cluster-empirical, late=day 150).
- Outputs:
  - `rebound_risk.csv` (per-patient, 7,566 rows)
  - `rebound_trajectory.csv` (per-cluster × scenario × month, 60 rows)
  - `rebound_sensitivity.csv` (per-cluster × scenario summary, 12 rows)
- Code: [Model/consequence/rebound_risk.py](../Model/consequence/rebound_risk.py),
  [Model/consequence/rebound.py](../Model/consequence/rebound.py).
- API: `GET /api/consequence/rebound-risk`.

### 10.3 Hardcoded parameters

All hardcoded clinical / economic constants for the consequence model live in
[evidence/parameter_registry.csv](evidence/parameter_registry.csv). Each row
carries source, URL, year, and notes. Two rows are flagged
**"ASSUMED, NOT SOURCED"** and must not propagate into the Phase 3 ROI
synthesizer without being either sourced or made user-configurable:
`intervention_program_cost_per_patient_usd` and
`dropout_reduction_relative_assumed`.

### 10.4 Known limitations (Consequence Model)

In addition to the §7 limitations on the underlying training data:

11. **Rebound trajectory sourced from European trial populations.** The
    per-molecule on-therapy reductions (SUSTAIN/STEP/SURPASS/SURMOUNT) and
    the 12-month rebound plateau (STEP-1 extension) come from RCTs that
    enrolled predominantly European cohorts in controlled clinical settings.
    The NHANES-seeded patient population here is US, more demographically
    heterogeneous, and operating outside trial conditions. **Rebound
    magnitudes are directionally correct but are not calibrated to this
    specific population.** Any per-patient rebound number must be presented
    as a model-derived projection, not a measurement.
12. **Linear-to-plateau rebound shape.** Biological rebound is closer to a
    monoexponential approach to plateau. The v1 model uses linear-then-flat
    for parameter parsimony; a v2 upgrade gated behind a config flag could
    swap in an exponential half-life formulation.
13. **HbA1c clinical floor at 5.0.** Trial-grade GLP-1 reductions were
    measured in T2D cohorts (mean baseline HbA1c ≈ 8); applying full
    reductions to NHANES patients with normal/pre-DM baselines would
    overshoot biology. The model caps reduction so that on-therapy HbA1c
    cannot drop below 5.0 (lower limit of normal). This is a pragmatic
    correction documented inline in `rebound.py`.
14. **No patient-level random effects on rebound.** Two patients on the
    same molecule with the same baseline get an identical projection. v2
    could add per-patient variability (±0.3 SD on attained reduction).
15. **Markov transition probabilities are population-level averages.**
    Within S1 (Uncontrolled T2D), the S1→S2 rate (0.026/yr) does not
    distinguish HbA1c 7.0 from HbA1c 9.5 — the registry has stratum-level
    transitions available for a v2 refinement.
16. **Long-horizon (10-year) projections are illustrative.** Uncertainty
    compounds significantly beyond the 5-year horizon. Lead with 5-year
    figures; surface 10-year as sensitivity only.
17. **Dialysis cost is Medicare fee-for-service by default.** Commercial
    insurance ESRD cost is ~3.3x higher (HCCI 2022); the script accepts
    `payer_type="commercial"` to swap the cost weight but it is not yet
    exposed via the API.
18. **CV event recurrence not modeled.** First CV event applies acute
    + follow-up cost; subsequent CV events within the same 5-year window
    are not modeled.
19. **GLP-1 net-of-rebate assumption.** Payer ROI uses net drug cost =
    WAC × (1 − 0.35) as the default. The 0.35 rebate fraction is
    industry-typical (SSR Health, IQVIA, CRS R47487) but is a rough midpoint
    of a 30–40% observed range and is flagged in the registry as
    ASSUMED-NOT-SOURCED. Set `glp1_payer_net_rebate_fraction = 0` for a
    WAC-based upper-bound sensitivity.
20. **QALY / quality-of-life benefits not modeled.** ROI is computed on
    pure cost avoidance. GLP-1s are typically cost-effective at
    ~$50,000/QALY thresholds when QoL gains are included; a pure cost-avoidance
    5-year ROI is expected to be negative for most patients, and this is
    consistent with published health-economic assessments. The dashboard should
    frame ROI as "budget impact" not "value" for this reason.
21. **On-therapy Markov modifiers are RCT-derived.** `on_therapy_cv_rr` = 0.74
    (SUSTAIN-6/LEADER), `on_therapy_renal_rr` = 0.64 (FLOW), and
    `on_therapy_glycemic_rr` = 0.15 (SUSTAIN-6/LEADER/STEP-5 HbA1c stability).
    All are population-average relative risks — they don't distinguish
    responders from non-responders within a cluster.
22. **Adherence assumed constant across the horizon.** ROI uses the
    baseline adherence rate as the α term for the full 5-year projection.
    In reality adherence decays year-over-year (persistence curves). A v2
    model would apply a year-specific α(t) derived from the KM survival layer.
23. **No mortality reduction credited to on-therapy patients.** SUSTAIN-6
    showed HR 0.63 for CV death and LEADER HR 0.78 for all-cause death, but
    v1 uses the same baseline mortality (0.012/yr) for both cohorts. This is
    slightly conservative for the on-therapy ROI (adherent patients live longer
    → slightly more downstream cost accrual, marginal effect).
