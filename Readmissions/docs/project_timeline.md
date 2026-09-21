# Preventra — project timeline

What was built, in the order it happened, and what each stage produced. Every figure below is
taken from the artefacts in this repository: notebook outputs, MLflow run records, model cards,
or a re-run of the original code where nothing was saved.

---

## At a glance

| Stage | Data | Outcome |
|---|---|---|
| **0** Starting point | UCI Diabetes 130-US Hospitals, 101,766 encounters | Decision tree, AUC-ROC **0.7063** on the production track |
| **1** CMS extraction and analysis | CMS DE-SynPUF, **1,332,755 encounters × 58 features** | Gradient model, **ROC-AUC 0.6893** — below the diabetes baseline, and on synthetic data |
| **2** MIMIC discovery and acquisition | MIMIC-IV `hosp` — 545,497 admissions, 223,291 patients | Real clinical measurements: labs, medications, both ICD editions |
| **3** MIMIC model, EDA, ICD analysis | 296,760 index stays, 148,669 patients | Calibrated gradient boosting, AUC-ROC **0.7229**, AUC-PR 0.3921, Brier 0.1404 |
| **4** Weekly monitoring | Discharge model + a rule layer over augmented weekly observations | 30-day post-discharge re-scoring, 20,000 weekly records across 4,000 patients |
| **5** Refining the reasoning | — | Auditable ROI, source attribution, disease-specific monitoring, and one experiment that returned a negative result |

---

## Stage 0 — the baseline everything else was measured against

Before the CMS work there was a readmission model on the **UCI Diabetes 130-US Hospitals**
dataset. It matters here only because it is the yardstick the CMS notebooks explicitly compare
themselves to — `notebooks/cms/phase1_readmission_model.ipynb` keeps the same Charlson weight table
"so scores stay comparable to the existing diabetes-data baseline".

**Four training tracks** were run and validated, each with its own report in `docs/`. The exit
gate was AUC-ROC ≥ 0.65 on a temporal test split — earliest 80% of encounters to train, most
recent 20% to test:

| Track | AUC-ROC | Precision | Recall | Gate |
|---|---:|---:|---:|---|
| Decision tree, plain | 0.6463 | 0.349 | 0.111 | **failed** |
| Decision tree, balanced | 0.6893 | 0.406 | 0.995 | passed |
| **Decision tree, balanced + importance** | **0.7063** | **0.745** | 0.188 | passed — *shipped* |
| XGBoost | 0.6702 | 0.348 | 0.126 | passed |

The **balanced + importance** track is the one that went to production, and 0.7063 is the number
`docs/deliverables/Preventra_Baseline_vs_CMS_MIMIC.pptx` reports as the baseline. Its threshold
sits high, at a predicted probability of 0.6341, which buys precision of 0.745 at the cost of
finding fewer than one readmission in five.

MLflow (`mlruns/`, runs dated **2026-03-30** and **2026-03-31**) holds the untuned and tuned
decision-tree runs at 0.5100–0.6463. `data/diabetic/model_card.json` (trained **2026-04-22**) publishes a
rounded 0.70 AUC with precision 0.72 and recall 0.76 — the recall figure matches no validation
report, so the reports in `docs/` are what this document cites.

---

## Stage 1 — CMS data extraction, exploration and analysis

**The data.** CMS DE-SynPUF — the *Data Entrepreneurs' Synthetic Public Use Files*, published by
the Centers for Medicare & Medicaid Services. Twenty sample files were pulled, cleaned, linked
and enriched into a single modelling table.

**What was built.** A discharge-time readmission model on the full merged build:

| | |
|---|---:|
| Encounters | **1,332,755** |
| Features | **58** |
| Readmitted within 30 days | 133,477 — **10.02%** |
| Validation | 5-fold, **grouped by patient** |

The feature set was substantial: demographics and ESRD status, Medicare coverage months and
annual reimbursement, 11 chronic-condition flags, length of stay, DRG, claim payment and
deductible, ten ICD-9 diagnosis columns and six procedure columns, and eight prior-utilisation
lookbacks covering inpatient stays, outpatient visits, **Carrier claims and Part D pharmacy
fills**.

### The result

| | |
|---|---:|
| **ROC-AUC** | **0.6893** |
| Validation | 5-fold, grouped by patient |

Grouping the folds by patient means the score holds up on people the model has never seen, which
is the right way to validate it. The figure itself sits **below the 0.7063 diabetes baseline**
and below the 0.7229 MIMIC reached later.

> **An earlier version of this document reported 0.8593 for this run**, together with a
> fold-by-fold table, PR-AUC 0.3627 and a Brier score of 0.0740. That figure was superseded and
> **0.6893 is the correct one**. The other metrics came from the same superseded report and are
> not carried forward here — the leakage check noted at the end of this stage is the most likely
> explanation for the higher number, and it is worth completing before any of them are quoted
> again.

> A smaller 200-row extract, `data/cms/finalmerged.csv`, also exists in the repository with 47
> of these columns. It was an early local prototype used to develop the pipeline before the full
> build, and its metrics — AUC 0.63 on a test fold containing a single readmission — describe
> that prototype, not this model.

### So why move to MIMIC?

**The score alone would have been reason enough** — 0.6893 is below the diabetes baseline this
project already had. But it was not the deciding factor: even a strong score on this data could
not have shipped. The reasons the metrics cannot show are worth stating in order of weight.

**1. DE-SynPUF is synthetic, so the score cannot be trusted onto real patients.** The files are
generated from real Medicare claims through a process that protects privacy by preserving the
distribution of each variable while deliberately weakening the relationships *between* variables.
CMS publishes them for developing and testing software, not for drawing conclusions about real
beneficiaries. A model trained on them can learn structure created by the synthesis rather than
by medicine — and there is no way, from inside the data, to tell which it has learned. **A score
on synthetic data is not a claim that can be made about a real patient**, and a model trained on
it cannot be deployed.

**2. There are no clinical measurements in it at all.** Of the 58 columns, **zero are laboratory
results and zero are vital signs**. Everything is administrative: what was billed, what was paid,
how many claims, how many coverage months. For comparison, **48 of MIMIC's 94 features are
laboratory values**, and the single strongest feature in the trained model is the last white cell
count before discharge.

**3. That makes the explanations unusable for the product.** The dashboard gives a care
coordinator three named reasons per patient. From claims data those reasons are things like
*prior outpatient payment sum* — in the early prototype that one feature held 54% of the model's
importance. It is predictive and it is useless: a coordinator cannot act on a payment total. From
MIMIC the same slot reads *"albumin 2.6 g/dL — below the normal range, indicating malnutrition
and poor physiological reserve"*, which points at something a person can do something about.

**4. ICD-9 only.** All ten diagnosis columns are ICD-9; there is no ICD-10 anywhere in the file.
The disease infrastructure this project now runs on — chapter mapping, the Charlson crosswalk and
eleven clinical monitoring groups — is built across both editions, because MIMIC contains both.
On CMS it would have been frozen in a code set the United States stopped using in 2015.

**5. The population is Medicare.** People aged 65 and over, plus those under 65 qualifying
through disability. The product is for all-cause adult inpatients, and MIMIC's cohort is 24%
under 40 — a group DE-SynPUF barely contains.

**6. Claims arrive too late for the weekly product.** A claim is settled weeks or months after
the care it describes. Stage 4's monitoring layer needs to know what happened *this week*. Claims
structurally cannot supply that, whatever their predictive quality.

**7. The two labels are not the same question.** CMS readmission runs at 10.02%, MIMIC at 19.63%
— close to double. Comparing 0.6893 against 0.7229 compares two models answering measurably
different questions on differently-shaped populations, so the gap should not be read as a clean
quality difference in either direction.

> **Worth confirming in the CMS pipeline.** The merged file carries both `READMITTED_30D` and
> `DAYS_TO_NEXT_ADMISSION`, and the second determines the first. It must be excluded from the
> feature set; if it ever reached the model, the resulting AUC would be an artefact rather than a
> measurement. This is the most likely explanation for the 0.8593 previously reported here, and a
> one-line check against the training code would settle it.

**The summary.** CMS gave a model that scores well but cannot be believed, cannot be explained to
a clinician, and cannot be deployed. MIMIC gives a lower score that is measured on real people,
real laboratory values and real diagnoses — a number the team can stand behind, on data a product
can actually be built on.

---

## Stage 2 — MIMIC data discovery and acquisition

**MIMIC-IV**, the critical-care and hospital database from the Beth Israel Deaconess Medical
Center, `hosp` module. Credentialed access.

| | CMS DE-SynPUF | MIMIC-IV |
|---|---:|---:|
| Encounters | 1,332,755 | 545,497 |
| Nature | **synthetic** | **real, de-identified** |
| Laboratory results | none | 48 features from `labevents` |
| Vital signs | none | available |
| Medications | prior fill counts only | full `prescriptions` at discharge |
| Diagnosis coding | ICD-9 only, 10 columns | ICD-9 **and** ICD-10, unlimited per stay |
| Population | Medicare — 65+ and disabled | all adult inpatients, 24% under 40 |
| Timeliness | claims settle weeks to months later | recorded during the stay |

The tables used: `admissions`, `patients`, `diagnoses_icd`, `d_icd_diagnoses`, `labevents`,
`prescriptions`, `omr`, `drgcodes`, `procedures_icd`, `services` and `transfers`. Samples of each
are kept under `data/mimic/`.

MIMIC is smaller in encounters and it scores lower. What it has instead is the thing that decides
whether a clinical product can exist: **measurements taken from real patients**. Laboratory
values, medication orders and complete diagnosis coding in both ICD editions — the three things
CMS could not supply, and the three the model came to rely on most.

---

## Stage 3 — Model training on MIMIC, plus two exploratory analyses

### 3a. The discharge model

**Where it lives:** `data/mimic/phase1_discharge_risk_mimic.ipynb`, with the trained
bundle and metadata in `data/mimic/model/results/`.

| | |
|---|---|
| Cohort | 296,760 index stays, 148,669 patients |
| Excluded | in-hospital death, hospice discharge, observation stays |
| Label | 30-day unplanned readmission — elective returns excluded |
| Prevalence | 19.63% |
| Features | 94 |
| Model | `HistGradientBoostingClassifier` with isotonic calibration |
| Split | `GroupShuffleSplit` by `subject_id` — no patient appears in two folds |

**Measured on a 59,835-admission test fold** (`model_card_phase1.json`, trained 2026-09-01):

| Metric | Value |
|---|---:|
| AUC-ROC | **0.7229** |
| AUC-PR | **0.3921** |
| Brier score | 0.1404 |
| Precision at the operating threshold | 0.3421 |
| Recall at the operating threshold | 0.6008 |
| Operating threshold | 0.2243 |

**0.7229 is the best figure the project has produced** — above the 0.7063 diabetes baseline and
above the 0.6893 CMS run. But the gain over the baseline is 0.017, which is small, and leading
with it would miss the point of the whole migration.

What changed is what the number is *made of*. It is measured on real patients, on **59,835
admissions containing 11,743 real readmissions**, split so no person appears in two folds, and
isotonically calibrated so a score of 30% can be read as a real 30% likelihood — which is what
later allowed a cost model to be built on top of it. The diabetes baseline was never calibrated,
so its scores could rank patients but could not be multiplied by anything.

What actually changed, beyond the 0.017 of AUC:

| | Baseline — UCI decision tree | Current — MIMIC gradient boosting |
|---|---|---|
| Population | diabetic inpatients, single encounter | all-cause adult inpatient, longitudinal |
| Features | 34 | 94 |
| Split | by row | **by patient** — no patient in two folds |
| Calibration | none | isotonic, ratio 1.01 |
| AUC-PR / Brier | not reported | 0.392 / 0.140 |
| Explainability | decision-path walker | SHAP, 94 features, clinician-facing labels |

The calibration line is the one that mattered most downstream. A score of 40% now means a 40%
chance, which is what later allowed a cost model to be built on top of it. The baseline was never
calibrated, so its scores could rank patients but could not be multiplied by anything.

A transfer test was also run and recorded in `data/mimic/transfer_test_results.json`: applied as-is to
the UCI Diabetes cohort the model scores AUC-ROC **0.5439** — barely better than chance, because
55 of its 94 features do not exist in that data. Restricted to only the features UCI shares, it
scores 0.6622 on MIMIC itself. The deck additionally reports that **retraining** the same
pipeline elsewhere reaches 0.670, which is the argument that the pipeline ports even though the
model does not; that retrain is quoted from the deck rather than from an artefact in this
repository. All of it is documented rather than buried — the model is specific to the data it was
trained on.

### 3b. Exploratory analysis of MIMIC

**Where it lives:** `data/mimic/mimic_eda_phase1_phase2.ipynb`, ten chart exports, and a
written interpretation in `data/mimic/mimic_eda_findings.md`.

The findings document explains every chart, including what each one does *not* support — the
psychiatric-facility transfer artefact, unfiltered laboratory maxima, the counter-intuitive
finding that elective admissions readmit more often than urgent ones, and the U-shaped
relationship between length of stay and readmission.

### 3c. Exploratory analysis of the ICD codes

**Where it lives:** `notebooks/mimic/solved-mimic-icd-analysis.ipynb`, with
`docs/mimic/mimic_disease_landscape.md` and `docs/mimic/mimic_cohort_icd_index.md` as the write-ups.

| | |
|---|---:|
| Distinct ICD codes | 28,562 |
| Distinct 3-character categories | 2,622 |
| Chapters present | 20 |
| ICD-9 / ICD-10 split | 45.7% / 54.3% |
| Diagnoses per admission | median 10, mean 11.7, maximum 57 |
| Admissions with a single diagnosis | 2.6% |
| Admissions spanning 2 or more chapters | **96.1%** |
| Codes used on exactly one admission | 6,160 (21.6%) |

The finding that shaped everything afterwards: patients do not have one disease. The median
admission carries ten diagnoses spread across six body systems, and 250 codes — under 1% of them
— account for half of every diagnosis ever recorded.

---

## Stage 4 — Weekly monitoring of readmission risk

A discharge score is a single number on the day someone leaves. The monitoring layer re-scores
them every seven days across the 30-day window, so a patient who deteriorates at home is visible
before they return.

**The architecture is deliberately split:**

- **Week 0** is the trained model alone — the real calibrated model over all 94 discharge
  features, explained with real SHAP attribution.
- **Weeks 1 to 4 are part model, part rules.** Each weekly score is the model's calibrated
  discharge probability, passed in unchanged as the anchor, plus a bounded rule adjustment for
  that week, plus a carry term so an unresolved problem keeps compounding instead of resetting
  every Monday. In `models/monitoring_rules.py` that is one line:
  `score = baseline + normalised + carry`.

So the trained model still sets the *level* a patient sits at every week; the rules only supply
the *movement* around it. The split exists because the model was trained on discharge-time
features and holds no vitals, adherence or pharmacy feature — it cannot react to what happens at
home, having nothing to react with. The rule layer covers exactly that gap and nothing else: a
transparent clinical guardrail wrapped around a calibrated statistical baseline, which is the
standard shape for a monitoring programme that does not yet have post-discharge outcome data of
its own.

**What is monitored** — what a real programme actually records, rather than a repeat lab panel:

| Signal | Range of effect |
|---|---:|
| Weight change since discharge | −1.0 … +7.0 |
| Medication adherence | −1.5 … +8.0 |
| Pharmacy refill collected | −0.8 … +5.0 |
| Follow-up appointment attended | −2.0 … +4.5 |
| Systolic blood pressure | −0.5 … +4.0 |
| Resting heart rate | 0 … +3.5 |
| Oxygen saturation | −0.5 … +5.0 |

The weights are deliberately asymmetric — the worst week adds about 27 points while the best week
removes about 6. Deterioration is strong evidence of trouble; perfect adherence is only weak
evidence of safety, since a patient can take every pill and still decompensate.

**Data provenance.** MIMIC ends at the hospital door: it contains no post-discharge measurements
of any kind. The weekly observations are therefore **augmented** — generated to exercise the
monitoring layer, with trajectories drawn from the model's own calibrated discharge probability
so that the cohort reproduces the real event rate and puts deterioration where the model expects
it. Every document carries `source` and the interface labels it. The document shape and the API
do not change when a real telemetry feed replaces it.

20,000 weekly records now exist across 4,000 patients.

---

## Stage 5 — Refining the reasoning

The final stage was less about new capability and more about making every number on screen
defensible.

**Return on investment became auditable.** The figures had been produced entirely by a language
model, which invented lump-sum costs and did the arithmetic itself. They moved to
`api/roi_model.py` as ten named line items — five for a readmission episode totalling $15,500,
five for delivering the intervention totalling $350 — with an explicit 25% intervention
effectiveness factor that the earlier formula silently omitted. That factor alone is the
difference between a 32× and an 8× return for the same patient.

**And it learned to say no.** The break-even risk falls straight out of the line items at
**9.0%**, and below it the arithmetic returns a loss. Of the 2,000-patient cohort at the time,
**867 patients** were being shown "expected savings" that the same model scores as money lost.
They now get "no intervention case — routine monitoring" instead.

**Every number says where it came from.** Each weekly signal is attributed to a named feed — a
home device hub, a medication app, a named pharmacy, a clinic scheduling system, or the patient's
own check-in. A pharmacy dispensing record and a self-reported adherence figure are different
kinds of claim and a coordinator should weigh them differently. A week with no contact shows
"carried forward" rather than naming feeds that never reported.

**Monitoring became condition-aware.** Eleven clinical groups were derived from each patient's
ICD codes, using the same Charlson crosswalk the model itself is built on, and validated across
534,227 MIMIC admissions — readmission rates span 0.53× to 1.46× across them. Each group changes
the weights, the wording, and in two cases the rule itself: weight *loss* is the risk signal in
cancer, and oxygen saturation is judged against the 88–92% target range in chronic lung disease
rather than against a population threshold.

Then the panel itself became condition-specific. A discharge baseline record — dry weight, usual
saturation, usual walking distance, pain at discharge — gave every relative reading a personal
reference point instead of a population one. Score normalisation equalised each group's range,
because a group with ten signals would otherwise out-score a group with seven for having more
boxes to tick, and the worklist sorts by score. And four groups gained their own readings: pillows
needed to sleep, sputum change, wound appearance, antibiotic course completion — every threshold
taken from published criteria.

**One experiment returned a negative result, and it was reported as one.** The question was
whether ICD codes could be engineered into features that improve the discharge model. Twenty-one
new features were built and trained on the same split with the same hyperparameters:

| Metric | Baseline | With ICD features | Difference |
|---|---:|---:|---:|
| AUC-ROC | 0.7229 | 0.7257 | +0.0027 |
| AUC-PR | 0.3921 | 0.3922 | +0.0001 |
| Readmissions in the top 500 by risk | **341** | 336 | −5 |

The AUC gain is statistically significant and operationally invisible. At a fixed intervention
budget the enriched model catches slightly *fewer* readmissions. The model was not adopted, and
the finding is recorded — including that the feature predicted to be strongest,
`principal_chapter`, ranked 110th of 115 and was effectively unused.

---

## Where the evidence for each figure lives

| Claim | Source |
|---|---|
| Diabetes baseline metrics | `docs/diabetic/model_validation_report_*.md`, `mlruns/` |
| Baseline-vs-current comparison | `docs/deliverables/Preventra_Baseline_vs_CMS_MIMIC.pptx` |
| CMS cohort size and composition | `data/cms/finalmerged.csv`, `phase1_readmission_model.ipynb` |
| CMS model metrics | re-run of `phase1_readmission_model.ipynb` |
| MIMIC model metrics | `data/mimic/model/results/model_card_phase1.json` |
| Transfer test | `data/mimic/transfer_test_results.json` |
| MIMIC EDA | `data/mimic/mimic_eda_findings.md` |
| ICD analysis | `notebooks/mimic/solved-mimic-icd-analysis.ipynb`, `docs/mimic/mimic_disease_landscape.md` |
| Weekly monitoring rules | `models/monitoring_rules.py`, `models/icd_groups.py` |
| ROI model | `api/roi_model.py` |
| ICD feature experiment | `notebooks/solved-mimic-icd-training.ipynb`, `docs/mimic/icd_feature_engineering.md` |
| Full change history | `donesofar.md` |
