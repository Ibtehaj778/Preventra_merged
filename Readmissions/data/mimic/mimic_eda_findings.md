# MIMIC-IV EDA — What the Charts Actually Say

A read-through of [`eda results/mimic-eda-solved.ipynb`](eda%20results/mimic-eda-solved.ipynb) and the
ten chart exports beside it. Every number below is copied from the notebook's stored output on the
**full MIMIC-IV v3.1 `hosp` extract** — not the demo, and not re-derived here.

The notebook answers two questions in one pass:

1. **Phase 1** — is there enough discharge-time signal to train a readmission model?
2. **Phase 2** — does MIMIC contain post-discharge observations on anything like a weekly cadence?

The answers are **yes** and **no**, and the charts below are how each was reached. Several of them
are easy to misread, so each section says what the chart shows *and* what it does not.

---

## 0. How the data was read

`labevents.csv` is **17.1 GB** and `prescriptions.csv` is **3.2 GB**; a Kaggle CPU session has 32 GB
of RAM and pandas needs roughly 3–5× a CSV's disk size once parsed. Both are streamed in 2-million-row
chunks, filtered to the cohort, reduced to per-admission aggregates and discarded. Nothing large is
ever held whole. Results cache to parquet so a second run skips the scans.

| Table | Size (GB) | How it was read |
|---|---:|---|
| `labevents` | 17.139 | streamed — 158.4 M rows in 80 chunks, 266 s |
| `prescriptions` | 3.249 | streamed — 8 chunks, 67 s |
| `omr` | 0.299 | loaded whole (7.75 M rows) |
| `transfers` | 0.191 | loaded whole |
| `diagnoses_icd` | 0.169 | loaded whole |
| `admissions` | 0.088 | loaded whole |
| `drgcodes` | 0.051 | loaded whole |
| `procedures_icd` | 0.032 | loaded whole |
| `services`, `patients`, `d_icd_diagnoses`, `d_labitems` | ≤0.024 | loaded whole |

The lab scan resolves target `itemid`s from the 64 KB `d_labitems` dictionary **first**, so the
18 GB pass filters on a small integer set rather than matching strings — 25 itemids across 12 lab
concepts.

---

## 1. Cohort construction

```
all admissions                 546,028
- died in hospital             -11,801
- hospice / died at discharge  -17,118
- observation stays           -235,639
= eligible index stays         296,760
```

**Order matters here, and the notebook gets it right.** The *next* admission is identified across the
full sequence **before** any rows are dropped. Reversing that would lose a readmission that happened
to follow an excluded stay, quietly deflating the positive rate.

The observation-stay exclusion is the large one — 43% of all admissions. `EU OBSERVATION`,
`OBSERVATION ADMIT`, `AMBULATORY OBSERVATION` and `DIRECT OBSERVATION` are not inpatient stays, so a
return after one is not a readmission in the CMS sense.

### Headline numbers

| | |
|---|---|
| Eligible index stays | **296,760** |
| Distinct patients | **148,669** |
| Admissions per patient | 2.00 |
| 30-day unplanned readmissions | **58,345** |
| **Positive rate** | **19.66%** |
| All-cause including elective returns | 20.63% |
| Patients with more than one stay | **38.9%** |

Two consequences that shaped everything downstream:

- **19.66% is a workable base rate.** Not so rare that the positive class starves, not so common that
  a trivial classifier looks good. It is also nearly double the 11.2% in the UCI diabetes file the
  baseline trained on, which is part of why scores are not comparable across the two.
- **2.00 admissions per patient forces `GroupShuffleSplit`.** With 38.9% of patients contributing more
  than one stay, a row-level split puts the same person in train and test. That is the single most
  important line in the notebook for model validity.

---

## 2. `prior admissions.png` — the strongest single feature

| Prior admissions | n | 30-day rate |
|---|---:|---:|
| 0 | 125,945 | **13.7%** |
| 1 | 58,919 | 16.6% |
| 2 | 30,728 | 20.6% |
| 3–5 | 41,383 | 25.3% |
| 6+ | 39,785 | **36.5%** |

Cleanly monotonic across a 22.8-point spread — the widest of any single feature profiled. A patient
with six or more prior stays is **2.7×** as likely to return as one with none.

**What to be careful about.** This is exactly the feature that makes a row-level split leak. Prior
admissions is computed from the patient's own history, so if stay #3 is in train and stay #4 is in
test, the model has effectively seen the answer. The strength of this gradient is *why* the leak would
be so damaging, not a reason to be pleased with it.

---

## 3. `discharge location.png` — strong signal, one misleading bar

| Discharge destination | n | 30-day rate |
|---|---:|---:|
| PSYCH FACILITY | 2,079 | **51.6%** |
| AGAINST ADVICE | 2,424 | 34.3% |
| MISSING | 501 | 29.5% |
| ACUTE HOSPITAL | 1,824 | 29.4% |
| CHRONIC / LONG TERM ACUTE CARE | 7,183 | 27.9% |
| HOME HEALTH CARE | 74,632 | 24.0% |
| SKILLED NURSING FACILITY | 40,526 | 21.8% |
| ASSISTED LIVING | 505 | 20.2% |
| OTHER FACILITY | 1,236 | 19.9% |
| REHAB | 10,906 | 18.3% |
| HOME | 154,912 | **15.9%** |

The clinical story is coherent: leaving with support (`HOME`, `REHAB`) is safest; leaving to a
higher-acuity setting, or leaving against advice, is not.

**Three things this chart does not say.**

- **`PSYCH FACILITY` at 51.6% is not a 51.6% avoidable-readmission rate.** Psychiatric care involves
  planned, recurrent short admissions. The label counts a return as unplanned unless the *next*
  admission is typed `ELECTIVE`, and psychiatric re-admissions are frequently typed `URGENT` or
  `EW EMER.` even when they are part of an expected pattern. On n=2,079 this is a real but
  over-stated signal.
- **`MISSING` at 29.5% is informative, not noise.** A discharge with no recorded destination sits
  10 points above the cohort. Imputing it to the mode would destroy that. This is a direct argument
  for the model's native missing-value handling.
- **The bar length is the rate, not the volume.** `HOME` is the shortest bar and also 52% of the
  cohort. Most readmissions in absolute numbers come from `HOME` — 154,912 × 15.9% ≈ 24,600, more
  than every facility category combined.

---

## 4. `admission type.png` — the genuinely counterintuitive one

| Admission type | n | 30-day rate |
|---|---:|---:|
| DIRECT EMER. | 21,215 | **30.6%** |
| EW EMER. | 167,888 | 21.0% |
| **ELECTIVE** | 13,019 | **19.6%** |
| **URGENT** | 51,912 | **15.1%** |
| SURGICAL SAME DAY ADMISSION | 42,726 | 14.4% |

**`ELECTIVE` (19.6%) sits above `URGENT` (15.1%).** That reads backwards and is the chart most likely
to be waved away as an error. It is not one. Two things drive it:

- In MIMIC-IV, `URGENT` is largely **inter-facility transfers** accepted on an urgent basis, many of
  them surgical, and they resolve. `ELECTIVE` includes planned admissions for serious chronic disease —
  scheduled chemotherapy, transplant work-up, staged cardiac procedures — where a return within 30
  days is common and often clinically expected.
- The label excludes a return only when the *next* stay is typed `ELECTIVE`. A patient on a planned
  cycle whose next admission is typed anything else is counted as an unplanned readmission.

`DIRECT EMER.` at 30.6% — an emergency admission arranged directly by a physician rather than through
the ED — is the highest-risk type and the one worth surfacing in the product.

**Takeaway:** admission type carries signal but is not an acuity ordering. Treating it as ordinal
(1 = elective … 5 = emergency, as the UCI schema did) would be wrong here. It stays categorical.

---

## 5. `length of stay.png` — a U-shape, not a slope

| LOS band | n | 30-day rate |
|---|---:|---:|
| 14d+ | 21,301 | **28.5%** |
| 7–14d | 45,949 | 24.8% |
| 3–7d | 114,599 | 19.7% |
| **<1d** | 17,703 | **16.2%** |
| **1–3d** | 97,199 | **15.9%** |

Read top to bottom the chart looks monotonic, but the bands are sorted by rate, not by duration. Put
them in order of length and the relationship is **U-shaped**: 16.2% (<1d) → 15.9% (1–3d) → 19.7%
(3–7d) → 24.8% (7–14d) → 28.5% (14d+). The minimum is at 1–3 days, and the very shortest stays are
*riskier* than slightly longer ones.

That inflection is real and clinically meaningful — a sub-24-hour inpatient stay can mean a problem
that was never fully worked up — but it means **length of stay must not be modelled as a monotonic
risk term.** A linear model would flatten this; the gradient-boosted trees pick it up natively, which
is one concrete reason the model class was not a free choice.

---

## 6. `insurance.png` — weak signal, and a rendering fault

| Insurance | n | 30-day rate |
|---|---:|---:|
| Medicare | 135,546 | 21.7% |
| Medicaid | 49,491 | 21.1% |
| Other | 7,635 | 17.0% |
| Private | 100,154 | 16.6% |
| MISSING | 3,503 | 13.2% |
| No charge | 431 | 9.0% |

A 5-point spread between the main categories — the narrowest of the demographic splits, and mostly a
proxy for age and socioeconomic position rather than an independent effect. Medicare's elevation is
largely the ≥65 population.

**Two cautions.** `No charge` at 9.0% rests on **n=431**, barely above the notebook's own `MIN_N=100`
floor; do not read a story into it. And in the exported PNG the matplotlib legend box overlaps the
Medicare bar, so that bar looks truncated — a plotting artifact, not missing data. The value label to
the right (21.7%) is correct.

---

## 7. `APR DRG.png` — the cleanest gradient in the notebook

| APR-DRG severity | n | 30-day rate |
|---|---:|---:|
| 1 — minor | 56,224 | **10.6%** |
| 2 — moderate | 97,738 | 17.0% |
| 3 — major | 86,468 | 24.8% |
| 4 — extreme | 30,256 | **27.4%** |

Monotonic, well-populated at every level, and a 16.8-point spread. This is a single field that already
encodes what a coder concluded about how sick the patient was, and it costs nothing to use.

Coverage is **91.2%** of the cohort — the remaining 8.8% have no APR-type DRG row and are left missing
rather than imputed to the median, which would push them toward "moderate" and understate risk for
whatever systematically lacks APR coding.

Same panel, other numbers worth keeping: **68.2%** of admissions have at least one procedure (median 2,
max 41); **57.9%** arrived via the ED, with median 6.1 ED hours and p90 12.5; and the ED-arrival rate
gap is small — **20.79% vs 18.11%**, only 2.7 points, much weaker than the destination or prior-stay
splits.

---

## 8. `ICD stuff.png` — two panels, two separate findings

### Panel 1 — the coding-version split

**ICD-9 61.8% / ICD-10 38.2%** across 3,628,115 cohort diagnosis rows.

This is the blocker that Phase 6 caught: the baseline's `_CCI_PATTERNS` in `api/main.py` were ICD-9
only. Applied to MIMIC, **every ICD-10-coded admission would have scored Charlson = 0** — not an
error, not a warning, just a comorbidity index of zero for nearly two-fifths of the cohort. The fix
is the dual ICD-9 + ICD-10 Charlson mapping (Quan et al. 2005) now in the training notebook.

The two code spaces also **overlap textually** — the same string can be valid in both and mean
different things — so every join must key on the `(icd_code, icd_version)` pair, never the code alone.
`models/mimic_diagnoses.py` enforces this.

### Panel 2 — diagnoses per admission

Median 11, mean 12.2, max 57. The histogram is **not smooth**: there are pronounced spikes at **9** and
**19** diagnoses.

Those spikes are a **billing artifact, not clinical reality.** Claim forms cap the number of secondary
diagnosis fields, so coders fill to the limit and stop. `n_diagnoses` therefore measures *coding
intensity* — how thoroughly this admission was documented — at least as much as it measures how sick
the patient was. It is still a useful feature, and the model does use it, but it should never be
described to a clinician as "how many conditions this patient has".

Top diagnoses are unremarkable in the reassuring sense — hypertension (73,750), hyperlipidemia
(52,108), esophageal reflux (37,505), diabetes (30,475), CHF (30,278), atrial fibrillation (29,428),
coronary atherosclerosis (29,229). A general adult inpatient population, not a specialty skew.

---

## 9. `Drug class prevelance.png` — prevalence that needs a caveat

| Drug class | % of admissions | Rate if exposed | Rate if not | Difference |
|---|---:|---:|---:|---:|
| Anticoagulant | **76.1%** | 21.45% | 14.00% | **+7.5 pp** |
| Opioid | 64.3% | 20.19% | 18.74% | +1.5 pp |
| Insulin | 33.2% | 23.15% | 17.95% | +5.2 pp |
| Diuretic | 31.1% | 23.10% | 18.13% | +5.0 pp |
| Antipsychotic | 11.7% | 23.24% | 19.20% | +4.0 pp |

**76.1% on an anticoagulant is the number to question.** No inpatient population is three-quarters
therapeutically anticoagulated. The regex matches `heparin`, and essentially every admitted adult
without a bleeding contraindication receives **prophylactic subcutaneous heparin** for clot
prevention. So this flag is closer to "was admitted and not actively bleeding" than to "is on
anticoagulation".

That reframes its +7.5 pp gap, the largest in the table. The comparison group — the 23.9% *not* given
prophylaxis — is enriched for exactly the patients who could not receive it: active bleeding, imminent
procedures, comfort-focused care, very short stays. Some of that gap is the drug flag; some is the
comparison group being unusual. The feature earns its place empirically, but "anticoagulants raise
readmission risk" is not what it shows.

Opioid exposure, by contrast, is high-prevalence and **nearly flat** (+1.5 pp) — a good reminder that
prevalence and signal are unrelated.

---

## 10. `lab coverage.png` — why 44 of 94 features are usually missing

| Lab | % of cohort admissions with ≥1 result |
|---|---:|
| Platelets | 89.1% |
| Hemoglobin | 89.0% |
| WBC | 88.8% |
| Creatinine | 86.1% |
| BUN | 85.0% |
| Potassium | 84.9% |
| Sodium | 84.5% |
| Glucose | 84.3% |
| Bicarbonate | 84.2% |
| INR | 58.3% |
| **Albumin** | **31.4%** |
| **HbA1c** | **9.3%** |

Nine labs sit in a tight 84–89% band — the routine CBC and basic metabolic panel, drawn on nearly
everyone. Then it falls off a cliff.

**HbA1c at 9.3% is the single most consequential number for cross-dataset transfer.** It is ordered
when someone suspects or is managing diabetes, so its presence is a diagnostic decision, not a
measurement schedule. The UCI diabetes dataset has an A1C column for its entire cohort by
construction — every patient there is diabetic. That asymmetry is a large part of why the MIMIC model
scored 0.544 when transferred: the features do not mean the same thing in the two populations.

Coverage is also why a filled manual-entry form still leaves **44 of 94 features missing**, and why
blank-means-unknown had to be handled natively rather than imputed.

---

## 11. `abnormal.png` — two panels, and the one place to be sceptical

### Panel 1 — value distributions, unfiltered

| Lab | n | Mean | Median | Min | Max |
|---|---:|---:|---:|---:|---:|
| Albumin | 93,095 | 3.40 | 3.40 | 0.80 | 6.40 |
| Bicarbonate | 249,929 | 25.67 | 25.62 | 9.25 | 49.50 |
| BUN | 252,376 | 20.41 | 16.00 | 1.00 | **209.06** |
| Creatinine | 255,533 | 1.24 | 0.90 | 0.00 | **29.80** |
| Glucose | 250,288 | 123.56 | 112.82 | 23.00 | **85,189.33** |
| HbA1c | 27,629 | 6.63 | 5.90 | 3.50 | 22.00 |
| Hemoglobin | 264,153 | 10.99 | 10.93 | 3.40 | 23.22 |
| INR | 173,130 | 1.37 | 1.20 | 0.45 | 14.18 |
| Platelets | 264,413 | 234.47 | 219.10 | 5.00 | **2,096.89** |
| Potassium | 251,975 | 4.10 | 4.07 | 2.30 | 10.00 |
| Sodium | 250,821 | 138.47 | 138.75 | 114.50 | 167.88 |
| WBC | 263,463 | 8.91 | 8.22 | 0.10 | **511.02** |

**A glucose of 85,189 mg/dL is not a physiological value.** Nor is a WBC of 511 or a platelet count of
2,097. These are unit errors, decimal slips and mis-mapped `itemid`s that survived because this cell
applies **no outlier bounds** — unlike the `omr` parsing in §13, which does clip to plausible ranges
and drops 6,542 values.

Medians are unaffected (glucose median 112.82 is clinically sensible), so the *distributional* reading
of this panel stands. But any downstream step that uses a **mean, a max, or a standard deviation** of
these labs inherits the contamination. `lab_glucose_max` is one of the 94 model features. Gradient
boosting is robust to this — a split at "glucose > 400" absorbs an 85,000 the same as a 500 — which is
why it did not surface as a modelling failure. It would matter immediately for any linear model,
z-scoring, or a chart with an unclipped axis.

**This is the notebook's one genuine gap:** the lab aggregation should carry the same physiological
bounds the `omr` path already applies.

### Panel 2 — share of admissions with ≥1 abnormal-flagged result

Glucose 84.3% · Hemoglobin 84.2% · INR 64.9% · Albumin 56.4% · WBC 53.9% · BUN 52.5% · HbA1c 49.2% ·
Platelets 36.8% · Bicarbonate 36.5% · Creatinine 34.2% · Potassium 25.4% · Sodium 24.0%

**Every one of these is conditional on the test having been run.** HbA1c reads 49.2% abnormal — but
among the 9.3% of admissions who had one, a group already selected for suspected diabetes. The correct
reading is "half of tested patients were abnormal", not "half the cohort". The two panels must be read
together or the second is actively misleading.

The lab-independent point stands: on the routinely-drawn panel, **more than eight in ten admissions
have at least one out-of-range glucose or hemoglobin**. Abnormality is the norm in inpatients, so
`n_abn` counts are useful as a *degree* measure, not as a yes/no flag.

---

## 12. Missingness across the assembled feature set

| Column | % missing |
|---|---:|
| `days_since_prev` | **42.4%** |
| `edregtime` | 42.1% |
| `marital_status` | 2.7% |
| `insurance` | 1.2% |
| medication aggregates | 0.7% |
| `discharge_location` | 0.2% |
| age, gender, race, LOS, admission type, prior admissions | 0.0% |

The two large ones are **structural, not defects**:

- `days_since_prev` is undefined for a patient's **first** admission. Its 42.4% missing rate is
  essentially the share of stays that are somebody's first — consistent with 61.1% of patients having
  exactly one stay. Filling it with 0 would state "readmitted the same day"; filling with a large
  number would state "last seen years ago". Both are fabrications. It stays missing.
- `edregtime` is missing for the 42.1% who did **not** arrive through the ED, matching the 57.9%
  ED-arrival rate almost exactly.

Everything a clinician would consider core is essentially complete. There is no data-quality reason
to drop any of the discharge-time features.

---

## 13. Part 2 — `omr`, and the question that killed weekly monitoring

`omr` is the only outpatient table in the `hosp` module, so everything Phase 2 could possibly use
comes from here.

**Raw contents:** 7,753,027 rows, 193,501 distinct patients, spanning 2105-01-19 → 2215-04-14 (MIMIC's
date-shifted calendar).

| Measurement type | Rows |
|---|---:|
| Blood Pressure | 2,827,801 |
| Weight (Lbs) | 2,145,353 |
| BMI (kg/m²) | 1,901,496 |
| Height (Inches) | 814,964 |
| BMI / Weight / Height (alt units) | 46,494 |
| Blood Pressure (sitting/standing/lying variants) | 16,640 |
| eGFR | **279** |

**Four measurement types, and that is the whole of it.** Weight, blood pressure, BMI, height. No
outpatient labs — the 279 eGFR rows across 193,501 patients are a rounding error. Whatever a weekly
monitor could watch, it cannot watch kidney function, glucose, or anything else the discharge model
actually relies on.

After parsing and clipping to physiological bounds (6,542 implausible values dropped): **10,589,231
tidy observations** — sbp 2,843,678 (mean 127.6), dbp 2,842,420 (74.0), weight 2,159,470 kg (80.9),
bmi 1,929,401 (29.1), height 814,262 cm (166.4).

### The decisive test

Joining every eligible discharge to that patient's later observations:

- **212,451 of 296,760 discharges (71.6%)** have at least one observation afterwards.
- Days until the **first** post-discharge observation: p10 **3**, p25 **8**, **p50 22**, p75 **96**,
  p90 **552**.

| Window | Weeks possible | Median weeks covered | Mean | **Discharges with ≥2 distinct weeks** |
|---|---:|---:|---:|---:|
| 30 days | 4 | 0 | 0.67 | **16.9%** |
| 90 days | 12 | 1 | 1.58 | 34.8% |
| 180 days | 25 | 1 | 2.58 | 43.3% |

The notebook draws a 25% viability line and prints its own verdict:

> **VERDICT: weekly re-scoring is NOT supportable from MIMIC-IV.**
> `omr` is opportunistic clinic measurement, not scheduled monitoring.

**16.9% against a 25% line.** Inside the 30-day window that matters, the *median* discharge has **zero**
weeks with any observation. Even stretching to 180 days, fewer than half of discharges reach two
distinct observation weeks — and by then the readmission question is long settled.

This is not a sample-size problem. Adding patients adds more of the same opportunistic pattern.
The cadence does not exist in the data.

### The subgroup trap

Even the 71.6% who *do* have later observations are not a usable population:

| | With observations | Without |
|---|---:|---:|
| n | 212,451 | 84,309 |
| **30-day readmission rate** | **22.0%** | **13.8%** |
| Mean age | 57.4 | 58.1 |
| Mean LOS | 5.76 | 6.03 |

Patients who return to clinic readmit at **22.0% vs 13.8%** — a 8.2-point gap on nearly identical age
and length of stay. Having a follow-up observation is itself a marker of being in the system, sicker,
and under active management. A Phase 2 model trained on this subgroup would be trained on a
self-selected population and would not generalise to the patients who most need monitoring: the ones
who never come back to clinic.

Observation counts are also wildly skewed — median 28 per discharge, p90 **229**, max **3,062** —
a handful of intensively-tracked patients dominating any naive average.

---

## 14. What the EDA settled

**Phase 1 — go.** The label constructs cleanly at a 19.66% base rate over 296,760 stays. The features
with the widest rate spreads — prior admissions (13.7 → 36.5), discharge destination (15.9 → 51.6),
APR-DRG severity (10.6 → 27.4), length of stay (15.9 → 28.5) — are the ones the clinical literature
predicts, which is the reassurance you want before training anything.

**Phase 2 — no go from MIMIC.** Four measurement types, opportunistically recorded, 16.9% two-week
coverage in the 30-day window, and a self-selected observed subgroup. `scripts/simulate_weekly_monitoring.py`
exists because of this section, and it is labelled `source="simulated"` for the same reason.

**Four constraints the EDA imposed on the model, all of which shaped the code that followed:**

1. `GroupShuffleSplit` on `subject_id` — 38.9% of patients have multiple stays.
2. Dual ICD-9 + ICD-10 Charlson mapping — 61.8/38.2 split, or ~38% score zero.
3. Native missing-value handling, not imputation — HbA1c at 9.3% coverage, `days_since_prev` missing
   by construction for 42.4%.
4. A model class that handles non-monotonic effects — length of stay is U-shaped and admission type
   is not ordinal.

---

## Appendix A — a discrepancy worth recording

`donesofar.md` Phase 6 reports the Phase 2 finding as **"median 127 days to the first post-discharge
reading; only 1.6% of discharges have readings in even two distinct weeks of the 30-day window."**

This notebook, on the full extract, gives **median 22 days** and **16.9%**.

Both used the same denominator — all eligible discharges, with non-observed discharges filled to zero
weeks — so the definitions match. The gap is almost certainly **demo versus full extract**:
`scripts/mimic_feasibility.py` documents itself as working "against the open demo or the full hosp
module", and the demo's ~100-patient `omr` slice is far sparser than the real table.

**The verdict is unchanged either way** — 16.9% is still well below the notebook's own 25% viability
line, and the median discharge still has zero observation weeks inside 30 days. But the figures
traceable to a stored run in this repository are the ones in §13, and those are the ones to quote.

---

## Appendix B — chart index

| File | Section | Read it for |
|---|---|---|
| `prior admissions.png` | §2 | The widest single-feature spread, and the leakage it implies |
| `discharge location.png` | §3 | Destination signal; note the psych-facility caveat |
| `admission type.png` | §4 | Why ELECTIVE > URGENT is not a bug |
| `length of stay.png` | §5 | The U-shape hidden by rate-sorted bars |
| `insurance.png` | §6 | Weakest split; legend overlaps the Medicare bar |
| `APR DRG.png` | §7 | Cleanest gradient; also ED and procedure coverage |
| `ICD stuff.png` | §8 | ICD-9/10 split, and the billing spikes at 9 and 19 |
| `Drug class prevelance.png` | §9 | Why 76% "anticoagulant" is prophylaxis |
| `lab coverage.png` | §10 | HbA1c at 9.3% and what it cost transfer |
| `abnormal.png` | §11 | Unfiltered maxima, and rates conditional on testing |

Charts are exported from `eda results/mimic-eda-solved.ipynb`; several include the surrounding notebook
output, which is why the printed tables above them are quoted in each section rather than re-derived.
