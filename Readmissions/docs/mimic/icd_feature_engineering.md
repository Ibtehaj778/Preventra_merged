# Can ICD codes become useful features?

**The question.** Right now the model turns a patient's whole diagnosis list into two numbers.
Can we map the codes into features that improve training *and* make the explanations better —
both at discharge and during weekly monitoring, where the explanations are currently generic?

**The answer.** Yes, on both counts, and the first step costs almost nothing because the work is
already being done and thrown away. But not by turning each code into a feature — that fails for
reasons the data makes very clear.

---

## 1. Why one feature per code does not work

| | |
|---|---:|
| Distinct codes in MIMIC | 28,562 |
| Used on exactly one admission | 6,160 (21.6%) |
| Used on ten or fewer | 16,157 (56.6%) |
| Used on 1% or more of admissions | **207** |

A column with one positive example teaches a model nothing; it either ignores it or memorises
that patient. Adding 28,562 columns to 296,760 training rows would produce a matrix that is
99.96% zeros.

Two further problems make it worse:

- **The same condition appears twice.** MIMIC spans the ICD-9 → ICD-10 switch, and **1,332
  diagnosis titles appear under both editions**. High blood pressure is `4019` in older records
  and `I10` in newer ones. As separate columns, the model sees two unrelated conditions and
  splits the evidence between them.
- **One illness is scattered across many codes.** Heart failure occupies **23 ICD-10 codes**
  plus a dozen ICD-9 equivalents. Individually most are rare; together they describe 6.7% of all
  admissions.

So the codes must be **grouped** before they can be features. The rest of this document is about
choosing groupings that a model can learn from and a clinician can read.

---

## 2. Five levels of features, cheapest first

### Level 0 — already done. The Charlson flags are in the model.

**An earlier version of this document was wrong here, and the correction matters.**

It claimed the Phase-1 pipeline computed the 17 Charlson condition flags and then discarded
them, keeping only the summed score. It does not. All 17 are columns in
`phase1_matrix.parquet` **and all 17 are in the model's 94-feature list**:

```
myocardial_infarction   congestive_heart_failure   peripheral_vascular   cerebrovascular
dementia                chronic_pulmonary          rheumatic             peptic_ulcer
mild_liver              diabetes_uncomplicated     diabetes_complicated  hemiplegia
renal_disease           malignancy                 severe_liver          metastatic_cancer
hiv_aids
```

The error came from checking the feature list for names containing "diag", "icd", "charlson" or
"comorb" — none of which match `congestive_heart_failure`. **19 of the 94 features are
diagnosis-derived**, not 2.

What follows from the correction:

- The model can already distinguish a heart failure patient from a kidney patient from a cancer
  patient. It cannot distinguish **sepsis** from a **hip fracture**, because neither is a
  Charlson condition — that specific example survives, but the general claim does not.
- The cerebrovascular and dementia sign problem is real for the *summed score* but not for the
  model, which has both flags separately and can learn their true direction.
- The driver cards can already attribute to a named condition. If they are showing
  "Comorbidity burden (Charlson): 5" instead, that is a presentation choice in
  `models/mimic_drivers.py`, not a missing feature.

The remaining levels are unaffected: none of the chapter, shape, or combination features exist
in the model today.

### Level 1 — one flag per ICD chapter

Twenty binary features, one per body-system family. Coarse, but every one has enormous support —
the smallest meaningful chapter still covers 2.6% of admissions, and the largest covers 72.7%.

This is what finally lets the model distinguish a sepsis admission from a hip fracture with the
same diagnosis count.

### Level 2 — the shape of the diagnosis list

Not *which* conditions, but how the list is put together. All cheap to compute, and each
describes something the two current features cannot:

| Feature | What it captures | Why it might matter |
|---|---|---|
| `n_chapters` | how many body systems are involved | mean 6.1, range 1–17. A 12-diagnosis patient confined to one system is a different problem from one spread across ten |
| `n_categories` | distinct 3-character stems | separates "ten variants of one thing" from "ten different things" |
| `n_status_codes` | Z/V codes — history, social factors, long-term treatments | 72.7% of admissions have at least one. *Long-term use of anticoagulants* is not a disease but is highly predictive |
| `n_symptom_codes` | R-codes: chest pain, ascites — findings without a diagnosis | a list heavy in these suggests the stay ended without a settled explanation |
| `n_complication_codes` | T80–T88 / 996–999: something went wrong during **this** stay | device infections, procedural mishaps. Known at discharge, so legitimate to use |
| `principal_chapter` | the chapter of the `seq_num = 1` code | the coder's judgement about *why the patient was there*, currently discarded entirely |

### Level 3 — combinations that are clinically real

Some pairs are more dangerous together than apart. A model with separate flags has to discover
that from data; naming it directly is cheap and makes the driver card immediately readable:

| Feature | Conditions | Why |
|---|---|---|
| `combo_cardiorenal` | heart failure + kidney disease | each treatment worsens the other; a recognised syndrome |
| `combo_af_heart_failure` | atrial fibrillation + heart failure | 4,951 admissions carry both. **Atrial fibrillation is not a Charlson condition at all**, so the model cannot currently see it |
| `combo_diabetes_renal` | diabetes + kidney disease | dose adjustment and monitoring both change |
| `combo_cardiopulmonary` | heart failure + COPD | breathlessness has two possible causes, so home readings are ambiguous |
| `dx_sepsis` | sepsis on this admission | also absent from Charlson; a strong driver of early return |

### Level 4 — published groupings, if more breadth is wanted

Two standard options, both with published ICD-9 and ICD-10 crosswalks:

- **Elixhauser (31 conditions).** Designed for exactly this purpose and broader than Charlson —
  it includes hypertension, arrhythmia, obesity, depression, alcohol and drug use, none of which
  Charlson covers. The natural next step after Level 0.
- **AHRQ CCSR (~530 categories).** Collapses every ICD-10-CM code into a clinically meaningful
  category. The right tool if breadth is the goal, at the cost of a large mapping file and
  ICD-10-only coverage (its predecessor CCS handles ICD-9).

Both need a mapping table downloaded from AHRQ. Neither is needed to start.

### Level 5 — detail inside the code string

The characters after the third position encode acuity, stage and laterality:

- **Acute vs chronic**: `I50.22` chronic systolic HF, `I50.23` acute-on-chronic. A patient
  discharged after an *acute* decompensation is at very different risk from one with stable
  chronic disease.
- **Stage**: `N18.1` through `N18.6` are CKD stages 1 to 5. Currently all collapse to one
  "renal disease" flag.
- **Specificity**: whether the code is an "unspecified" variant. A list full of unspecified
  codes is a signal about documentation quality, which itself correlates with care fragmentation.

Worth doing after Levels 0–3 prove themselves, since it multiplies feature count for
subtler gains.

---

## 3. THE RESULT: it was tested, and it does not work

**Run on full MIMIC-IV — 296,760 admissions, 148,669 patients, a 59,835-row test fold split by
patient. Baseline 94 features against the same model with 21 ICD features added.**

| Metric | Baseline | Enriched | Difference | Bootstrap 95% CI | Verdict |
|---|---:|---:|---:|---|---|
| AUC-ROC | 0.7229 | 0.7257 | **+0.0027** | [+0.0010, +0.0042] | significant |
| AUC-PR | 0.3921 | 0.3922 | **+0.0001** | [-0.0026, +0.0025] | **not significant** |
| Brier | 0.1404 | 0.1402 | -0.0002 | — | negligible |
| Calibration slope | 1.010 | 1.009 | -0.001 | — | both near perfect |

And the number a care team actually feels — how many readmissions land among the patients they
have capacity to work:

| Budget | Baseline catches | Enriched catches | Difference | 95% CI |
|---|---:|---:|---:|---|
| Top 500 by risk | **341** | 336 | -5 | [-22, +11] |
| Top 1,000 by risk | **648** | 635 | -13 | [-32, +16] |

**The AUC-ROC gain is real and irrelevant.** It is statistically significant and operationally
invisible: AUC-PR is flat, and at a fixed intervention budget the enriched model catches *fewer*
readmissions, though not significantly so.

That combination is explicable rather than surprising. AUC-ROC is dominated by the mass of
negatives, so the new features improved separation at the *low-risk* end. AUC-PR and the top-N
catch rate are dominated by the high-risk end — the only end the worklist uses — and it did not
move.

### Which features the model actually used

The 21 new features carry **6.5% of total SHAP attribution**, so the model does reach for them.
Some rank above most of the original 94:

| Rank of 115 | Feature |
|---:|---|
| 22 | `chap_blood` — anaemia and coagulation disorders, 30.7% of admissions, and **not a Charlson condition** |
| 24 | `n_symptom_codes` — how much of the list is symptoms rather than settled diagnoses |
| 32 | `chap_neoplasm` |
| 38 | `chap_genitourinary` |
| 42 | `chap_nervous` |
| 52 | `n_categories` |
| 59 | `has_complication` |

### What was refuted

**`principal_chapter` ranks 110 of 115, with a mean absolute SHAP of 0.00003 — effectively
unused.** This document called it "the strongest new signal" on the strength of a 3x univariate
spread across its chapters, 0.53x for obstetric to 1.69x for a Z-code principal. That spread is
real, and it is fully explained by features the model already has: admission type, discharge
disposition, age and the labs. Univariate lift said "informative"; the model said "I already knew
that".

The four hand-built combinations rank 92-106, and `dx_sepsis` ranks 81 despite a 1.29x
univariate lift. The caveat stated earlier — that a gradient-boosted tree can synthesise
interactions from the component flags — held.

### Recommendation: do not ship the enriched model

Beyond the flat result, deploying it carries a cost the metrics do not show. The application
stores **one ICD code plus three secondary diagnosis titles**. It cannot compute `n_chapters`,
`chap_blood` or `n_symptom_codes` for a patient without every code of the admission — so shipping
this model would first require storing all codes at load time, and would hand the manual-entry
path features it has no way to fill. That is real work for +0.0027 AUC-ROC that never reaches the
worklist.

The experiment was worth running. It converted "these features should help" into "they do not",
which is what it was for.

### What would be worth trying instead

- **Elixhauser's 31 conditions.** `chap_blood` ranking 22nd is the interesting result here: the
  most useful new feature was a body system Charlson does not cover at all. Elixhauser adds
  arrhythmia, hypertension, obesity, depression, alcohol and drug use, and coagulopathy — none of
  them present today. A more promising direction than chapter flags.
- **Nothing on the weekly side changes.** The clinical grouping in Phase 23 is untouched by this
  result: it never claimed to improve the discharge model, and it changes what a card *says* and
  what the programme *collects*, which no AUC measures.

---

## 4. The pre-training screen: does any of it carry signal?

Rather than assert it, measure it. [`notebooks/mimic/mimic_icd_feature_engineering.ipynb`](../notebooks/mimic/mimic_icd_feature_engineering.ipynb)
builds every feature above on full MIMIC-IV and reports, for each one:

- **prevalence** — how many admissions have it
- **readmission rate** among those admissions
- **lift** — that rate divided by the cohort base rate

Lift near 1.0 means the feature carries nothing on its own. Prevalence below ~0.5% means it is
too rare to learn from whatever its lift. The notebook labels each feature `useful`, `too rare`,
or `no signal alone`, so the retrain starts from evidence rather than from a wish list.

It also exports `icd_engineered_features.parquet`, keyed on `hadm_id` — designed to join
straight onto `phase1_matrix.parquet`.

**Univariate lift is a screen, not proof.** A feature can have lift 1.0 and still matter in
combination; another may have high lift but be redundant with something the model already sees
through `charlson_score`. The screen's real value is identifying what is *not* worth adding.

### The honest experiment

Adding features is not the same as improving a model. The comparison that settles it:

1. Retrain on the identical `GroupShuffleSplit` by `subject_id`, so no patient spans the split.
2. Compare **AUC-PR** (not AUC-ROC — the outcome is imbalanced) and **calibration**, since the
   whole ROI layer depends on calibrated probabilities.
3. Check whether the SHAP explanations became more specific, which is a goal in its own right
   even if AUC moves very little.

A plausible outcome is a small AUC gain and a large explainability gain. That would still be
worth shipping — but it should be reported as what it is, not dressed up.

---

## 5. What this changes on screen

Today a driver card can say:

```
Number of diagnoses recorded: 14
  more coded diagnoses indicate greater clinical complexity
Comorbidity burden (Charlson): 5
  higher scores mean more chronic conditions and higher risk
```

Both are true and neither is actionable. With Level 0–3 features, the same patient's SHAP
attribution can say:

```
Heart failure with chronic kidney disease
  each condition's treatment worsens the other, and this pairing accounts for
  a large part of this patient's risk
Atrial fibrillation
  raises stroke risk and complicates the medication plan
Complication coded during this stay
  something went wrong in hospital that has not yet resolved
```

Same model family, same SHAP method — the difference is entirely in what the features are
allowed to represent. **The explanation cannot be more specific than the features permit**,
which is the core reason to do this work even if the AUC barely moves.

---

## 6. The weekly monitoring half

The second part of the question: weekly explanations are generic, and some diseases need more
care than others. Both are true, and both are fixable.

### What happens now

Searching `models/monitoring_rules.py` for any mention of diagnosis, ICD or Charlson returns
nothing. Every patient gets the same rule:

```python
def _rule_weight(kg):
    if kg >= 2.0:
        return 7.0, "a gain of more than 2 kg in a week indicates fluid retention…"
```

**+7 points for a 2 kg gain, whether the patient has heart failure or a new knee.** That is
wrong in both directions: two kilos in a week is *the* warning sign in heart failure and close
to meaningless after orthopaedic surgery.

### What it should be

Derive a **clinical group** from the patient's codes, and let the group choose both the weights
and the wording. The proposed groups, ordered so the condition that most determines the
monitoring plan wins when a patient qualifies for several:

| Group | Signals that matter most | What changes |
|---|---|---|
| **Heart failure** | daily weight, breathlessness, diuretic adherence | weight ≥2 kg becomes the dominant driver, roughly +10; SpO₂ thresholds tightened |
| **Renal** | weight, blood pressure, potassium-affecting medicines | both weight and BP weighted up; dialysis attendance replaces the generic follow-up rule |
| **Respiratory / COPD** | SpO₂ against the patient's **own** baseline, inhaler adherence, sputum change | absolute SpO₂ thresholds are wrong here — 91% may be this patient's normal; weight becomes nearly irrelevant |
| **Post-surgical / injury** | temperature, wound appearance, pain trajectory, mobility | weight drops to near zero; fever and wound signals dominate; the follow-up appointment matters more because it is when the wound is inspected |
| **Sepsis / infection** | temperature, heart rate, completing the antibiotic course | antibiotic completion becomes its own rule; a partially completed course is a specific, actionable risk |
| **Diabetes** | glucose readings, hypoglycaemic episodes, insulin adherence | glucose enters the rule set at all, which it currently does not |
| **Oncology** | temperature (neutropenic fever), weight **loss**, chemotherapy schedule | weight loss becomes a risk signal, the opposite direction from heart failure |
| **Neuro / stroke** | falls, swallowing difficulty, anticoagulant adherence | falls become a monitored signal; anticoagulant adherence weighted heavily |
| **Mental health** | appointment attendance, medication adherence, isolation | vitals matter little; contact and attendance are almost the whole signal |
| **General** | current rule set unchanged | the safe default |

The notebook measures how many admissions fall into each group and their readmission rate, so
the groups can be validated as *worth having* before any of this is built.

### Two things this changes beyond the score

**The explanation becomes specific.** Instead of:

> Weight change since discharge: +2.1 kg — *a gain of more than 2 kg in a week indicates fluid
> retention and is an early sign of decompensation*

a heart-failure patient sees:

> Weight change since discharge: +2.1 kg — *in heart failure this is the single most reliable
> early warning, and it usually responds to a diuretic review rather than a hospital admission.
> Two kilos of fluid is roughly two litres the heart is having to move*

and a post-surgical patient sees:

> Weight change since discharge: +2.1 kg — *after surgery this is usually appetite returning
> rather than fluid, and on its own it is not a concern. The wound and temperature are the
> signals that matter this week*

**It changes what you ask the patient for.** A COPD patient should be logging SpO₂ daily and can
skip weight; a post-op patient should be sending a wound photograph and a temperature, neither
of which the current form collects. The weekly logging form becomes group-aware, which is a
larger practical win than the score adjustment.

### One caveat, stated plainly

These weights would be **clinically-reasoned defaults, not learned values** — exactly like the
current ones. MIMIC contains no post-discharge vitals, so there is nothing to fit them against.
The right posture is to write them down explicitly, attribute them, and treat them as a starting
hypothesis a clinician can argue with. That is what `models/monitoring_rules.py` already does;
this makes the rules conditional without pretending they became empirical.

---

## 7. What can be built now, and what is blocked

| Piece | Buildable today? | What it needs |
|---|---|---|
| ~~Unpack 17 Charlson flags~~ | **Already done** | All 17 are model features already — see Level 0 |
| `principal_chapter` | **Yes, locally** | `phase1_diagnoses.parquet` holds the principal code and version for 296,433 admissions, keyed on `hadm_id`. No raw MIMIC needed |
| Chapter flags across all codes, list-shape, `dx_sepsis`, complications | Needs raw MIMIC | These need every code of the admission, not just the principal. `notebooks/mimic/mimic_icd_training.ipynb` builds them on Kaggle and joins onto the uploaded matrix |
| Elixhauser / CCSR | Same, plus a download | AHRQ mapping files |
| Store all diagnosis codes when loading | **Yes, today** | Raise `N_SECONDARY` in `models/mimic_diagnoses.py` and keep `(code, version)` for secondaries. Unblocks everything downstream and costs a re-run of the loader |
| Show secondaries on clinical screens | **Yes, today** | The API already returns them; only the worklist and detail panel need to render them |
| Disease-conditional weekly rules | **Yes, today** | Mongo holds `primary_icd_code` for every patient. Grouping on the principal code alone is coarser than grouping on the full list, so this improves further once the row above is done |
| Group-aware weekly logging form | **Yes, today** | Follows the rules change |

The dependency to notice: **everything at discharge time is blocked behind one re-run of the
Phase-1 notebook**, because the training matrix keeps no codes. Everything on the weekly side is
buildable immediately.

---

## 8. Risks worth naming before starting

- **Complication codes are close to the outcome.** T80–T88 records that something went wrong
  during the stay. That is genuinely known at discharge, so it is not leakage — but it will be a
  strong feature for a reason that is partly circular, and should be reported as such.
- **ICD version is a calendar proxy.** Feeding it in lets the model learn era-specific
  readmission rates rather than clinical ones. Leave it out.
- **Z-codes encode care pathways, not physiology.** *Awaiting organ transplant* predicts
  readmission strongly, but because of how those patients are managed. Useful, and worth
  flagging when it drives a score, since acting on it is not the same as acting on a disease.
- **More features on the same 296,760 rows.** Fine for a gradient-boosted model, but calibration
  must be re-checked — the entire ROI layer assumes the probability means what it says.
- **Group assignment must be visible.** If a patient is monitored as "heart failure", the screen
  should say so and say which code produced it. A silent grouping that changes someone's score
  is exactly the kind of hidden logic this project has otherwise avoided.

---

## 9. Suggested order

1. ~~**Make the weekly rules diagnosis-conditional.**~~ **Done** — Phase 23. Eleven clinical
   groups, group-specific weights, wording and collection.
2. ~~**Train and compare.**~~ **Done** — section 3. The enriched model is not worth shipping.
3. **Show the secondary diagnoses on clinical screens.** No model work, the data is already in
   the response. Unaffected by the training result.
4. **Store all codes at load time.** Still worth doing — not for the discharge model, which does
   not benefit, but because the weekly grouping currently defaults 32% of patients to "general"
   for want of codes on the secondaries.
5. **Elixhauser's 31 conditions**, if anything. `chap_blood` was the most-used new feature and
   Charlson has no blood chapter at all, which is the one clue in the results pointing at a
   direction that might work.
