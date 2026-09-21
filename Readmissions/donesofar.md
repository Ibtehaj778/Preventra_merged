# Preventra — Progress Log

Running record of work on this repository. Newest phase last.

---

## Phase 1 — AI Insights: ROI + counterfactual

- **`api/gemini_insights.py`** (new): Gemini calls with structured JSON schemas for
  (a) an ROI estimate (readmission cost avoided vs. intervention cost, net ROI, ratio)
  and (b) a counterfactual explanation of what would lower the patient's risk.
- **`POST /api/ai-insights`**: on-demand, button-triggered rather than auto-fired, to control LLM cost and latency.
- **`AiInsightsPanel.jsx`**: mounted at the end of every verdict view — `PatientDetail`,
  `ManualEntry`, `UpdatePatient`, and the dashboard's `PatientDetailPanel`.
- Iterations: removed "(Simulated… mock mode)" text; converted prose to bullet points;
  banned dashes in the Gemini system instructions; built **`BulletList.jsx`** after
  `list-disc list-inside` produced an inconsistent marker gap.

## Phase 2 — Weekly trend monitoring

- **`GET /api/patients/{id}/trend`**: builds a series from `risk_registry` and classifies each
  patient as `stable` / `deteriorating` / `improving` / `action_required` (sharp jump reuses the
  existing 15-point alert threshold) / `insufficient_data`.
- **`POST /api/week-narrative`**: per-week Gemini explanation of why that week's score moved.
- **`WeeklyTrendPanel.jsx`** + **`TrendStatusBadge.jsx`**: status banner, trend chart, per-week
  driver cards, each with an "Explain this week" button.
- New route **`/patients/:id/trend`**; a compact version sits in the dashboard slide-over.

## Phase 3 — Dashboard: current vs. discharge risk

The worklist was showing the stale discharge-time score, so a patient who had deteriorated to
98% could rank below one who had recovered to 40%.

- `_classify_trend_status()` and `_weekly_series_by_patient()` in `main.py` — one shared
  classifier so the dashboard, detail panel and trend page cannot disagree.
- Worklist now shows **current score** primary, discharge score as a sub-line, a **delta column**,
  a **trend badge**, sortable trend filters, and a clickable "Needs Attention" tile.
- Fixed along the way: mock/detail score mismatch; empty Score History chart in mock mode
  (missing `history` field); redundant `98% / at discharge 98%` when no weekly history exists.

## Phase 4 — UI polish

- Found that `animate-in` / `slide-in-from-*` classes throughout the app were **no-ops** —
  the `tailwindcss-animate` plugin was never installed. Replaced the dashboard slide-over's
  open/close with real `transition-transform` / `translate-x`, including deferred unmount so
  the close animation actually plays.

---

## Phase 5 — Dataset research and the DE-SynPUF finding

Triggered by: "we need a well-trained model, and for that a good dataset."

**Headline: CMS DE-SynPUF cannot train a clinically valid model.** CMS's own Data User's Guide
states its disclosure treatment destroys correlations between variables and that the file lacks
research utility for inference. A supervised model only learns `P(readmit | features)`; if those
relationships were synthesised away, the model trains, reports an AUC, and is meaningless.

Two live defects found in the then-current production model while checking artefacts:

| Issue | Detail |
|---|---|
| Model card overstates precision | `model_card.json` advertised `precision: 0.72`; actual positive-class precision was **0.49** (6,212 FP vs 6,077 TP). Served to clinicians via `/api/model/metrics`. |
| Risk scores inflated ~3.5× | Trained on a rebalanced set (~39.6% positives) but the true `<30`-day rate in `diabetic_data.csv` is **11.2%**. Median leaf probability 0.395. This also corrupts the ROI panel, which treats `risk_score` as a probability. |

Calibration note: a 2025 meta-analysis puts the pooled readmission AUC at **0.71**, so ~0.70 was
already at the literature norm. Better data buys real correlations, honest calibration and
longitudinal signal — not a higher AUC.

Deliverable: dataset evaluation matrix (MIMIC-IV, All of Us, CMS LDS/RIF via ResDAC, Synthea)
published as an artifact, plus **`scripts/mimic_feasibility.py`**.

## Phase 6 — MIMIC-IV feasibility, measured

Run against the MIMIC-IV demo, then the full extract.

- **Phase 1 (discharge risk): GO.** Label constructs cleanly; 9.4% 30-day rate on the demo.
- **Phase 2 (weekly monitoring): NO GO from MIMIC.** `omr` is the only outpatient table and holds
  just Weight, BP, BMI, Height — recorded opportunistically. Median **127 days** to the first
  post-discharge reading; only **1.6%** of discharges have readings in even two distinct weeks of
  the 30-day window. Not a sample-size problem; the cadence does not exist.
  *(Superseded — those are demo-scale figures. The full-extract EDA in Phase 12 gives median
  **22 days** and **16.9%** two-week coverage, still well below the 25% viability line. Same
  verdict, different magnitude; quote the Phase 12 numbers.)*
- **New blocker found:** diagnoses are ~50/50 ICD-9/ICD-10 (**61.8 / 38.2** on the full extract),
  but `_CCI_PATTERNS` in `api/main.py` were ICD-9 only, so ICD-10 rows silently scored **CCI = 0**
  for 38% of the cohort.

## Phase 7 — Kaggle training notebooks

Two notebooks written to `data/mimic/`, designed around the real constraint: `labevents.csv`
is **18.4 GB** and a Kaggle CPU session has **32 GB RAM**.

- `phase1_discharge_risk_mimic.ipynb`, `phase2_postdischarge_trend_mimic.ipynb`
- Tables over ~500 MB are **streamed in chunks**, filtered to the cohort, reduced to per-admission
  aggregates and discarded. `emar` (8.7 GB), `poe` (5.1 GB) and `pharmacy` (4 GB) are never touched.
- Correctness guards: **`GroupShuffleSplit` on `subject_id`** (patients average ~2 admissions; a row
  split leaks the same person across folds), a three-way train/calibrate/test split, and a
  `calib_ratio` metric that surfaces exactly the 3.5× inflation bug.
- Dual **ICD-9 + ICD-10 Charlson** mapping (Quan et al. 2005) fixes the silent `CCI = 0`.
- Four bugs were found by *executing* the cells, not compiling them: variable shadowing
  (`for name, pat in …` clobbered the `patients` DataFrame), `pd.concat([])` on empty chunk
  results, `object` vs `int64` join keys, and duplicate `subject_id` producing `_x`/`_y` suffixes.

## Phase 8 — Trained results and the transfer test

Trained on full MIMIC-IV: 296,760 index stays, 148,669 patients, 19.66% readmission rate.

| Evaluation | AUC-ROC | AUC-PR | Lift | Calib. ratio |
|---|---|---|---|---|
| MIMIC test fold, all 94 features | **0.723** | **0.392** | 2.00× | **1.01** |
| MIMIC test fold, UCI features only | 0.662 | 0.300 | 1.53× | 0.80 |
| UCI Diabetes, transferred as-is | **0.544** | 0.125 | 1.10× | 1.09 |
| UCI Diabetes, after recalibration | 0.545 | 0.125 | 1.10× | 1.00 |
| **Control: retrained on same 39 features** | **0.670** | 0.217 | 1.90× | — |

- On MIMIC the model is credible **and calibrated** (ratio 1.01) — the logistic baseline in the
  same run scored 2.37, a live reproduction of the `class_weight="balanced"` bug in production.
- **It does not transfer.** Decomposition: missing features cost only **−0.061**; domain and label
  shift cost **−0.118**. Recalibration does not help, so this is broken *discrimination*.
- The control (retraining on the same 39 mapped features → 0.670) proves the mapping is sound and
  the failure is genuine.
- **Conclusion: the pipeline is the transferable asset, not the weights.**

Script: **`scripts/test_mimic_model_on_diabetes.py`** (full feature mapping documented inline).

## Phase 9 — Full switch to MIMIC

Decision: full replacement, with Manual Entry rebuilt around enterable MIMIC features.

**The blocker.** The MIMIC model is `HistGradientBoostingClassifier` inside
`CalibratedClassifierCV` — it has no `.tree_` and no `.decision_path`, so the existing
interpretability engine (`models/driver_extractor.py`, `_extract_top3_drivers`) **cannot run on it
at all**.

- **`models/mimic_drivers.py`** (new) — SHAP-based per-patient drivers against the inner HGB, plus
  clinician-facing labels for all 94 features, emitted in the `"Label: value (explanation)"` format
  the dashboard already parses.
- **`api/mimic_scoring.py`** (new) — 94-feature builder, banding, scoring, driver extraction.
- **`api/main.py`** — **−292 lines**: removed the UCI model loader, `_CCI_PATTERNS`,
  `_build_feature_vector`, `_LABEL_MAP_INFER`, `_extract_top3_drivers`, `_get_risk_band`.
- **`GET /api/manual-entry/schema`** (new) — field list and valid category values, so the form can
  be driven from the model rather than hardcoded.
- **`scripts/load_mimic_to_mongo.py`** (new) — ETL into the existing dashboard schema.

Verified, not assumed:

- The model pickles under scikit-learn 1.6.1 (Kaggle) and the venv runs 1.7.2. A minimal
  `_RemainderColsList` shim makes it load, and predictions are **bitwise identical** to a genuine
  1.6.1 environment across 3,000 rows — so no venv downgrade.
- SHAP on HGB is **approximate**: ~8% additivity error against the model margin, top-3 driver
  agreement 2.45/3 versus interventional SHAP. Drivers are indicative, not exact Shapley values.
  Documented in the module. Still a large improvement on "cannot compute at all".
- Two bugs caught by testing: the NaN guard used `isinstance(x, float)`, which **misses numpy
  scalar NaNs**; and the driver parser split on the *first* `" ("`, truncating any label containing
  brackets. Both fixed, in `mimic_scoring` and in `main.py`'s row parser.

`ManualPatientInput` is now all-optional by design — HGB learned a split direction for missing
values during training, so a blank field scores as genuinely unknown rather than as zero.

### Loaded to MongoDB

2,000 patients / 3,869 admissions. **Derived data only** — score, band, three driver strings, a
rebuilt date. No labs, ICD codes, notes or real MIMIC timestamps leave the machine; the 94
engineered features stay local in the parquet.

Dates are reconstructed from `n_prior_adm` + `days_since_prev` + `los_days`, anchored so each
patient's last discharge lands today. Within-patient intervals — the clinically meaningful part —
are exact; only the absolute epoch moves. This also fixes MIMIC's 2110–2201 de-identification
shift, which would otherwise look broken in the UI.

The original 47-patient batch (`2026-04-22`) is still in the database but no longer displayed,
because `get_latest_batch_date()` returns the newer batch.

## Phase 11 — Manual Entry rebuilt on the MIMIC contract

The last piece of the UCI model still in the product. `PatientFormFields.jsx` was collecting
`A1Cresult` / `max_glu_serum` / `insulin` / `diabetesMed` and posting them to an API that had
stopped understanding those fields in Phase 9, so every submitted field was silently dropped and
every manual score came from an empty feature vector.

- **`PatientFormFields.jsx`** rewritten around the 94-feature contract: 5 categoricals, 11 numerics,
  8 flags, 17 Charlson checkboxes and 10 labs, grouped into six sections. Labels are taken from
  `models/mimic_drivers.py`'s label map so a driver card and the field that produced it read the same.
- **`MimicPatientForm`** is now one shared component rendered by both `ManualEntry.jsx` and
  `UpdatePatient.jsx`, so the two pages cannot drift the way the inlined UCI copies did.
- **`GET /api/manual-entry/schema` is now actually called.** Category values come from the model's own
  feature spec, with the built-in lists kept only as a fallback, so a retrain updates the form without
  a code change.

Three things the rebuild had to get right:

| Problem | Fix |
|---|---|
| `NumberField` did `Number(e.target.value)`, so a cleared box sent **0** | Blank now sends `null`, which `exclude_none=True` turns into NaN. Measured: an all-blank form scores **6.9%** as unknown and **18.6%** with blanks coerced to zero — 11.7 points and a band flip, from typing nothing. |
| A two-way Yes/No toggle cannot say "not known" | `TriStateField` — Yes / No / Unknown, defaulting to Unknown. |
| `disch_home` / `disch_snf` / `disch_ama` are three independent flags | Collected as one **Discharge destination** select and expanded on submit, so "home = yes AND skilled nursing = yes" is unrepresentable. |

`charlson_score` is shown live in the section header as the ticked weights add up, but is still derived
server-side and never posted — the preview mirrors `CHARLSON_WEIGHTS`, it does not replace it.

**`UpdatePatient` now warns when there is nothing to edit.** Batch-loaded patients carry
`raw_inputs = {}`, so the form opens blank while the stored score came from the full 94-feature vector.
Recalculating from that blank form scores a different, largely-unknown patient; the page says so
instead of presenting the two numbers as a like-for-like before/after.

Verified end to end against the running app: schema fetched (200), a 19-field high-acuity profile
scored **44.9% / High** with three coherent SHAP drivers, Charlson derived as 5 from three ticked
boxes, and `npm run build` clean. No `A1Cresult` / `max_glu_serum` / `diabetesMed` reference remains
anywhere in `frontend/src`.

## Phase 12 — EDA documented

The EDA notebook (`data/mimic/eda/mimic-eda-solved.ipynb`) and its ten chart exports
had no written companion, so the numbers behind the Phase 6 and Phase 8 decisions lived only in
notebook output. **`data/mimic/mimic_eda_findings.md`** now explains every chart against the
stored full-extract run, including what each one does *not* say.

What the write-up settles or corrects:

- **The full-extract Phase 2 figures.** Median **22 days** to first post-discharge observation
  (p10 3, p25 8, p75 96, p90 552), and **16.9%** of discharges with two distinct observation weeks
  inside 30 days — against the notebook's own 25% viability line. Phase 6 above quotes demo-scale
  numbers.
- **The observed subgroup is not representative.** The 71.6% of discharges with any later observation
  readmit at **22.0%** versus **13.8%** for those without, on near-identical age and length of stay.
  A Phase 2 model trained there would miss the patients who never come back to clinic.
- **The ICD split is 61.8 / 38.2**, not 50/50.

Four charts that mislead on a quick read, now written up with the reason each one is not an error:

| Chart | Trap |
|---|---|
| `admission type.png` | ELECTIVE (19.6%) outranks URGENT (15.1%). URGENT is largely inter-facility surgical transfers that resolve; ELECTIVE includes planned admissions for serious chronic disease. Admission type is **not** an acuity ordering, so it cannot be encoded as one. |
| `length of stay.png` | Bars are sorted by rate, hiding a **U-shape**: 16.2% (<1d), 15.9% (1–3d), 19.7%, 24.8%, 28.5%. The shortest stays are riskier than 1–3 days. A monotonic risk term would flatten it. |
| `Drug class prevelance.png` | 76.1% "anticoagulant" is prophylactic heparin, not therapeutic anticoagulation. Its +7.5 pp gap partly reflects an unusual comparison group — patients who could not receive prophylaxis. |
| `abnormal.png` | Abnormal rates are conditional on the test being ordered. HbA1c reads 49.2% abnormal among the **9.3%** who had one. |

**One real gap found while writing it up.** The lab aggregation applies **no physiological bounds**,
unlike the `omr` path which clips and drops 6,542 implausible values. A glucose max of
**85,189 mg/dL**, a WBC of 511 and a platelet count of 2,097 survive into the cached features and
therefore into `lab_*_max`. Gradient boosting absorbs them — a split at "glucose > 400" treats 85,000
identically — which is why this never surfaced as a modelling failure. It would break any linear
model, z-scoring, or unclipped chart immediately.

The deck gained four EDA slides and its Phase 2 figures were corrected to match.

## Phase 13 — Weekly monitoring rebuilt on what a programme actually records

Two problems with the weekly cards, both surfaced by reading the UI closely.

**1. A label that contradicted its own card.** Every week showed
`Days since previous discharge: 2 days` sitting directly under a `7 days later`
header. Two different quantities were competing for the same words: the card
header's interval between scoring points, and the model feature `days_since_prev`,
which is the gap between the patient's *previous* discharge and the *start of this
admission*. The value was correct and correctly constant; the wording read as
"it has been 2 days since you were discharged".

- Relabelled to **`Gap before this admission`**, with `_gap_explain` reworded to
  drop every phrase that counts forward from a discharge.
- Driver strings are persisted verbatim, so a label-map change does not reach
  existing rows. **`scripts/relabel_gap_driver.py`** rewrites them in place —
  label and explanation only, no score, value or ordering touched. 4,038
  documents across `weekly_monitoring`, `patient_worklist` and `risk_registry`.
- The manual-entry field was renamed to match, keeping form and driver aligned.

**2. The weekly cards were showing discharge-time features.** Charlson flags,
prior admissions and the admission gap are properties of the index stay: they
cannot move, so a four-week monitoring view repeated the same three unchanging
drivers. A monitoring view should show what is being monitored.

`scripts/simulate_weekly_monitoring.py` was rewritten around what a real
post-discharge programme records — **vitals** (weight, blood pressure, heart rate,
oxygen saturation), **medication adherence** as proportion of days covered,
**pharmacy refill** collection, and **follow-up attendance**.

| | |
|---|---|
| Week 0 | The real calibrated model over 94 features, explained with real SHAP attribution. Unchanged. |
| Weeks 1–n | That discharge baseline, adjusted by the week's monitored signals through explicit bounded rules, plus a carry term so an unresolved problem compounds instead of resetting each week. |

**This is deliberately not the gradient-boosted model scoring vitals.** The model
contains no vitals, adherence or pharmacy feature and cannot score them. The
weekly layer is a transparent clinical guardrail over a calibrated ML baseline —
the standard shape for a programme with no post-discharge outcome data of its own
yet. Every rule and weight sits in `SIGNAL_RULES` where a clinician can argue with
it, and each document records `scored_by` as `model` or `monitoring_rules`.

Weights are **asymmetric** — the worst week adds ~27 points, the best removes ~6.
Deterioration is strong evidence of trouble; perfect adherence is weak evidence of
safety. This mirrors a property already measured on the real model: perturbing its
lab inputs across their deteriorating range moved scores **+10.2** points on
average, while normalising them moved only **−1.8**.

Regenerated for 2,000 patients × 5 weeks. Cohort behaviour:

| Week | Deteriorating | Recovering |
|---|---:|---:|
| 0 | 23.1% | 14.1% |
| 2 | 37.3% | 10.3% |
| 4 | **52.2%** | **9.6%** |

Recovering patients decline and then plateau rather than falling to zero, because
the fixed discharge features set a floor good behaviour cannot go below.

A worked trajectory (`MIMIC-10076342`, 34.1% → 72.1%): adherence 57% → 41%, weight
+1.4 → +4.2 kg, oxygen saturation 92% → 88%, heart rate 81 → 120, then a missed
refill and a missed follow-up. Textbook decompensation, and every card says which
signal moved the score.

**Also fixed along the way**

- `api/db_utils.get_mongo_client` had no retry or timeout configuration. Atlas
  here intermittently fails the TLS handshake on one replica-set node, which
  pymongo surfaces as `AutoReconnect` — it took down a migration mid-run and
  returned 500s from the live trend endpoint. Explicit `serverSelectionTimeoutMS`,
  `connectTimeoutMS`, `socketTimeoutMS`, `retryReads` and `retryWrites` now let
  the driver route around it. Both scripts also retry with backoff and write in
  batches rather than per document.
- `No lab draw` / `weeks had a lab draw` in `WeeklyTrendPanel.jsx` and the API's
  `interval_label` were left over from the lab-panel version. Now `No contact` and
  `no readings recorded`.

## Phase 14 — AI Insights panel restored

The ROI panel was returning "AI insights are temporarily unavailable" for every patient. Three
separate faults, none of them the Gemini key, which was valid throughout.

**1. `API_KEY` in `.env` held the Gemini key.** Line 4 had been set to the same 53-character value
as `GEMINI_API_KEY`, while `frontend/.env` sends a different 32-character secret. Any freshly
started backend therefore rejected every browser request with `Invalid or missing API key`. The
running server only appeared to work because it had loaded the older value at startup and still
held it in memory. Reset to the value the frontend already sends; `.env` backed up first, and
`.env.bak.*` added to `.gitignore` so a backup containing the Gemini key cannot be committed.

**2. The running backend was a stale process.** Started hours earlier in an environment where
`sklearn` was not importable, so `/api/patients/predict` returned `Scoring unavailable`. Restarting
it under `.venv/bin/python` fixed scoring and picked up the corrected `.env`.

**3. The real cause of the panel error: Gemini 504.** With the first two fixed the call still
failed, and the backend log gave the actual reason the endpoint had been swallowing into a generic
503:

    [ai-insights] Gemini call failed: 504 DEADLINE_EXCEEDED

`_HTTP_OPTIONS` in `api/gemini_insights.py` was set to a 20-second timeout with
`attempts=1`. Gemini returns a transient deadline error often enough that a single attempt failed
the whole panel while the key, payload and model were all fine. Now **45 seconds with 3 attempts**.
The panel is button-triggered and shows an "Estimating..." state, so a slow call is visible rather
than silent, and the bound still prevents a hung spinner.

Verified in the browser: the panel renders Readmission Cost $15,500, Intervention Cost $350,
Expected Savings $5,286, Net ROI $4,936 at 15.1x, with rationale and counterfactual bullets.

**Worth noting about that ROI figure.** The formula in the Gemini system instruction is
`expected_cost_avoided = (risk_score / 100) * readmission_cost`, which assumes the intervention
prevents *all* of the readmission risk. Real post-discharge care coordination reduces risk by
roughly 20-30% relative, so the displayed ratio is overstated by about 3-5x. The fix is an
effectiveness term; separately, Gemini currently performs the arithmetic itself and nothing
validates that the five returned figures are mutually consistent. Both are listed below.

## Phase 15 — ROI on the weekly monitoring view

The ROI panel ran on four surfaces, all of them scoring the *index admission*. The trend page had
none, which left the most decision-relevant view without a business case.

- **`PatientTrend.jsx`** now mounts `AiInsightsPanel` below the trend, driven by the **latest**
  point in the series rather than the discharge score, with a line above it stating which is which
  ("intervening now, at this patient's latest score of 72.1% rather than the 34.1% recorded at
  discharge").
- **`WeeklyTrendPanel`** gained an optional `onLoaded` callback so the page can reuse the series it
  already fetched instead of issuing a second identical request. The callback is held in a ref, so
  a parent re-rendering with a new function identity cannot retrigger the fetch.
- The panel is **not** rendered inside `WeeklyTrendPanel`, so the dashboard slide-over - which
  mounts the compact trend panel and its own `AiInsightsPanel` - still shows exactly one.

**Why this surface is the better one for ROI.** On the discharge view the counterfactual reasons
over fixed features, and advice like "address the metastatic cancer" is not actionable. On the
weekly view the drivers are the monitored signals, so the same call returns things a care
coordinator can actually do. Verified output for `MIMIC-10076342` at 72.1%:

> Addressing the missed pharmacy refill through immediate medication delivery and counseling would
> close the treatment gap and reduce overall risk.
>
> Providing timely outpatient follow up for the rapid weight gain and low oxygen saturation could
> stabilize the patient and prevent an acute decompensation event.

**Two caveats carried in the UI rather than hidden.** A weekly score is the calibrated discharge
probability adjusted by the monitoring rules, not a calibrated probability in its own right, so the
page labels the weekly figure as directional. And because the ROI formula still lacks an
effectiveness term, a higher weekly risk inflates the ratio further - this patient shows **31.9x**
against the ~15x seen at discharge. Both are open items below.

## Phase 16 — ROI made auditable

The ROI panel was unauditable. Gemini invented a lump-sum readmission cost and a lump-sum
intervention cost, did the arithmetic itself, and returned five numbers with no breakdown. Two
runs on the same patient could disagree, nothing checked the five figures were even consistent
with each other, and no one could see what had been counted.

**`api/roi_model.py`** (new) replaces all of it with named line items and deterministic arithmetic.

| Cost of one readmission episode | Basis | |
|---|---|---:|
| Emergency department presentation and triage | 1 ED visit before admission | $1,250 |
| Inpatient bed-days | 5.2 days at $2,150 per day | $11,180 |
| Laboratory and diagnostic imaging | per episode | $1,120 |
| Pharmacy and procedures | per episode | $1,450 |
| Discharge planning for the return stay | per episode | $500 |
| **Total** | | **$15,500** |

| Cost of delivering the intervention | Basis | |
|---|---|---:|
| Care coordinator time | 3.5 h at $48/h loaded | $168 |
| Pharmacist medication reconciliation | 0.75 h at $76/h loaded | $57 |
| Remote monitoring device and data plan | 30 days amortised | $65 |
| Appointment scheduling and transport support | per enrolled patient | $40 |
| Platform licence per monitored patient | per patient per month | $20 |
| **Total** | | **$350** |

**The effectiveness term is now in.** The old formula multiplied risk by the full episode cost,
which assumes the intervention prevents every readmission it touches. It now multiplies by an
explicit 25% relative reduction, the conservative end of what transitional-care meta-analyses
report. For a patient at 72.1%:

    Exposure                0.721 x $15,500                 = $11,176
    Avoidable share         $11,176 x 25%                   =  $2,794
    Less intervention cost  $2,794 - $350                   =  $2,444   ratio 7.98x

The same patient previously showed **31.9x**. 8x is the number that survives a finance review.

**Gemini no longer prices anything.** `_INSIGHTS_SCHEMA` was cut to `roi_rationale` and
`counterfactual_explanation`; the computed breakdown is passed into the prompt with an instruction
to use the figures verbatim and never state a monetary value not present in the input. The endpoint
computes ROI first, then merges the narrative over it, so the money is fixed before the model is
called and is identical on every run.

**The UI shows the audit trail.** A "Show how this was calculated" disclosure under the four
headline boxes renders both cost tables line by line, the three calculation steps with their
formulas, and the assumptions — including that the line items are published-average defaults
meant to be replaced with the organisation's own finance figures.

## Phase 17 — Sign-in, roles, and the patient portal

The API had no notion of identity: one shared `X-API-Key`, every route public to
anyone holding it, and `MyHealth.jsx` reading the patient to display from `?id=` in
the URL. Two roles now exist, and each sees only what it should.

**Authentication — standard library only.** Neither PyJWT, python-jose, passlib nor
bcrypt is installed, and each carries version-coupling breakage that lands on whoever
deploys. `api/auth.py` uses PBKDF2-HMAC-SHA256 at 600,000 iterations with a 16-byte
per-user salt for passwords, and `<base64url payload>.<hmac-sha256>` tokens signed with
`AUTH_SECRET` — structurally a JWT minus the algorithm-negotiation header, which is the
part of JWT that produces CVEs. Verified with `hmac.compare_digest`; 12-hour expiry.

**Access control is deny-by-default, in one place.** A single middleware in `api/main.py`
requires a valid token on every `/api/` route and permits a patient token only under
`/api/me/`. A route added later is hospital-only until someone deliberately allows it —
the failure direction we want. Measured:

| Request | Result |
|---|---|
| No token → `/api/patients` | 401 |
| Wrong password → `/api/auth/login` | 401 |
| Hospital token → `/api/patients` | 200 |
| **Patient token → `/api/patients`** | **403** |
| **Patient token → `/api/analytics/top-drivers`** | **403** |
| Patient token → `/api/me/summary` | 200 |

**No id is ever supplied by a patient.** `/api/me/summary`, `/api/me/trend` and
`/api/me/weekly-log` resolve the patient from the signed token, so there is no parameter
to tamper with and no IDOR to get wrong. This replaces the `?id=` read that `ROADMAP.md`
flagged as letting anyone view any patient by editing the URL.

**The patient portal** (`MyHealth.jsx`, rebuilt) shows what they were treated for — primary
diagnosis with ICD code, secondary conditions, discharge date — their current risk against
their discharge risk with the change between, what is driving the score now, and a weekly
check-in form. Blank fields are omitted from the payload rather than sent as zero, so an
unmeasured reading is never scored as a measured one.

**Patient-logged observations move the real score.** The rule set moved out of the
simulator into **`models/monitoring_rules.py`**, shared by both callers, so a patient's
own reading scores exactly as a simulated one does. Baseline is always the calibrated
discharge score, never last week's, so a bad week cannot permanently ratchet the number.
Measured on a live account:

    bad week   fluid +2.6 kg, 45% doses, missed refill, missed follow-up, SpO2 90
               29.2% -> 63.6%  (+34.4)
    good week  weight -1.2 kg, 98% doses, refill collected, follow-up attended
               63.6% -> 41.1%  (-22.5)

**Accounts are provisioned, not self-registered.** `scripts/seed_users.py` creates hospital
and patient accounts, generating passwords that are printed once and stored only as hashes.
A patient account grants access to a real medical record, so it should be issued against a
verified patient_id rather than claimed by whoever types one into a signup form first.

Frontend: `AuthProvider` restores a session by asking the server who the token belongs to
rather than trusting a cached role; the route tree, sidebar, chatbot and alerts bell are all
role-gated; a patient typing `/patients/<someone-else>` is redirected to their own page.

## Phase 18 — Registration, and users moved to SQLite

**Accounts now live in SQLite**, at `data/runtime/users.db`, behind `api/user_store.py`. Deliberately
not the clinical MongoDB: sign-in should not fail because a patient worklist is unreachable —
which it repeatedly was during this work — and credentials have a different backup policy and
blast radius from patient records. The table carries username, email, password hash, role,
optional `patient_id`, display name, created/updated and last-login timestamps, with a
`CHECK` constraint on role and unique indexes on username and email. WAL journalling, one
connection per operation, since FastAPI runs sync handlers in a threadpool.

The four seeded Mongo accounts were migrated across with their hashes intact, so existing
passwords still work. `data/runtime/users.db*` is gitignored — it holds password hashes.

**`POST /api/auth/register` is self-service but a role cannot be claimed.** Open registration
where the caller names their own role would let any visitor tick "hospital" and read all 2,000
patient records.

| Role | What it must prove |
|---|---|
| hospital | `HOSPITAL_REGISTRATION_CODE`, distributed out of band, compared with `hmac.compare_digest` so it cannot be found a character at a time |
| patient | a `patient_id` that exists **and** that record's discharge date |

The patient check is knowledge-based verification against the discharge record. It is adequate
for a stay the patient was physically present for; it is not the invite token issued at
discharge that a live deployment should use, and that gap is in the open items rather than
left implied. A failed match returns one message whether the record is absent or the date is
wrong — distinguishing them would turn the endpoint into an oracle for valid patient IDs.

Every guard measured against the running API:

| Attempt | Result |
|---|---|
| hospital, no staff code | 403 |
| hospital, wrong staff code | 403 |
| patient claiming a record with no proof | 403 |
| patient with the wrong discharge date | 403 |
| password under 8 characters | 422 |
| malformed email | 422 |
| duplicate username | 409 |
| second account for a record that already has one | 409 |
| hospital with the correct code | 201 |
| patient with the correct ID and date | 201 |

**One real bug fixed on the way.** The patient branch is the only part of registration that
touches Mongo, and Atlas's intermittent TLS drop was surfacing as a bare 500 — which reads to
a user as "your details were wrong" rather than "try again". That lookup now retries and
degrades to a 503 with a message that says which it is.

Frontend: `Register.jsx` with a role selector that swaps between the staff-code field and the
patient ID plus discharge date; `Login.jsx` and it toggle without a route change; registration
returns a token so a new user lands straight in their portal. Verified in the browser —
registering against an unclaimed record signed in as "Mary Wilson" and rendered her own page,
while an attempt against an already-claimed record was refused.

`scripts/seed_users.py` now writes to SQLite and remains how an administrator issues accounts
directly: bulk patients for a pilot, a first staff login before a code is circulated, or a
password reset.

---

## Phase 19 — Sign-in disabled behind a flag

Sign-in is off by default. `auth_enabled()` in `api/auth.py` reads `AUTH_ENABLED`, and with it
false the access middleware short-circuits and `current_user` returns a stand-in care-team user,
so every `/api/` route answers without a token. The frontend mirrors it through
`frontend/src/auth/config.js` and `VITE_AUTH_ENABLED`: `AuthProvider` seeds the same stand-in
user, skips session restore, and the login screen never renders.

Nothing was deleted. Login, registration, the patient portal, the role middleware and the SQLite
accounts in `data/runtime/users.db` are intact and bypassed; setting both flags to true restores them.
Both sides must agree — enabling only the frontend produces a login screen the API ignores,
enabling only the backend produces 401s with no way in. The backend prints which mode it is in
at startup.

With the flag off, anyone who can reach the API has full clinical access. It is a local
development convenience and unsafe on anything reachable from outside the machine.

---

## Phase 20 — ROI only where there is a case for it, and named data sources

**Two changes, both about not asserting more than the data supports.**

### An improving patient does not need an ROI pitch

The trend page previously ran the ROI panel on every patient's latest score, including patients
whose risk was low and falling. The arithmetic still runs there, and it returns a NEGATIVE net
benefit — the coordinator hours cost more than the readmission they would be expected to avert —
but the panel presented "Expected Savings" in green regardless, which reads as an argument for
spending money the model itself says is lost.

The break-even point falls straight out of the existing line items:

```
intervention_cost / (readmission_cost x effectiveness)
        $350      / ($15,500 x 0.25)                    = 9.0% readmission risk
```

`roi_model.roi_case` returns a verdict rather than only figures, and it reads trajectory as well
as level, because 55% and falling calls for a different action from 55% and climbing:

| Situation | Verdict | Leads with |
|---|---|---|
| Below 9.0%, risk falling | step monitoring down | the verdict |
| Below 9.0%, otherwise | routine monitoring only | the verdict |
| Below 9.0%, risk rising | below break-even, but the trend is upward - re-assess next week | the verdict |
| Above 9.0%, risk falling | continue current plan, do not escalate | the figures |
| Above 9.0%, risk rising | intervene now | the figures |
| Above 9.0%, stable | intervention is cost-effective | the figures |

`BREAK_EVEN_RISK_PCT` is derived from the line items, not typed in, so editing any cost moves it
automatically. The verdict ships with `/api/patients/{id}/trend`, so the page decides what to show
before it asks Gemini for anything, and Gemini is now instructed that the decision is already
made — for a patient with no case it must say so rather than sell the intervention. A negative
net figure is no longer painted in the colour of a return.

Verified end to end: MIMIC-10019992 at 4.1% renders "No intervention case — routine monitoring"
with the arithmetic behind a disclosure; MIMIC-10013569 at 55.5% renders the figures as before.
Across the 2,000-patient cohort every verdict occurs, and the distribution is the point of the
change — 867 patients were previously being shown a savings figure that the same arithmetic
scores as a loss:

| Verdict | Patients |
|---|---|
| routine monitoring, no case | 867 |
| intervention is cost-effective | 638 |
| intervene now, risk rising | 414 |
| step monitoring down | 40 |
| continue, do not escalate | 32 |
| below break-even but trending up | 9 |

### Every weekly number now says where it came from

A monitoring week is not one feed. `models/monitoring_rules.SIGNAL_FEEDS` attributes each signal
to a named upstream system — a home device hub for vitals, a medication app for adherence, a
retail pharmacy for refills, a clinic scheduling system for follow-up attendance — and the weekly
cards show it under each driver plus a "data received from" footer.

This matters beyond decoration: a pharmacy dispensing record is an external fact while an
adherence percentage typed into an app is the patient's own account of one, and a coordinator
should weigh them differently. Gemini receives the attribution too, and now writes lines like
"Medication adherence reported through the MedMinder app sits at fifty percent, and Bay Street
Pharmacy dispensing records confirm a missed pharmacy refill."

**The feed names are fictional.** No integration exists. They are assigned deterministically from
the patient id, so one patient keeps the same pharmacy and the same device hub across every week,
and the attribution is derived at read time rather than stored — no migration was needed and
documents written before this change get the same answer.

Three cases are attributed honestly rather than uniformly:

- week 0 is not a monitoring week at all, so it is attributed to the model reading the discharge
  record;
- a week with no contact shows "Carried forward" instead of naming feeds that never reported;
- anything a patient submits through the portal is attributed to the portal, because a weight
  they typed did not come off a connected scale.

### More than one way to say the same finding

Each rule fired one fixed sentence per bucket, so four consecutive cards repeated it verbatim and
a reader learned to skip them. Every branch now carries two or three interchangeable phrasings and
`score_week` takes a `variant`, derived from patient and week so a card never rewords itself on
refresh. **Points are variant-independent** — the 10,000 regenerated documents carry identical
scores to the run before, only the prose differs.

Also corrected while in here: the weekly Gemini instruction still described weeks as driven by
"an outpatient lab panel" and told the model to chase a blood draw for a carried-forward week,
left over from before Phase 13 replaced labs with vitals and adherence. And the ROI instruction
had no gender rule, so narratives were calling patients "her"; it now matches the others.

---

## Phase 21 — Disease landscape documented, and a Kaggle notebook for the full data

Two deliverables answering what the diagnoses in this project actually are.

`docs/mimic/mimic_disease_landscape.md` covers what an ICD code does and does not tell you, the
chapter/block/category/code hierarchy with heart failure drilled through all four levels, worked
single- and multi-diagnosis patients, the chapter table with unique code counts, and — the part
that matters for the roadmap — an honest account of how little of this Preventra currently uses:

- **2 of 94 model features are diagnosis-derived** (`n_diagnoses`, `charlson_score`). No
  individual code is a feature, so sepsis and a hip fracture with the same count and Charlson
  score are indistinguishable to the model. Defensible given 685 of 1,062 codes appear once, but
  it is a choice with a ceiling attached.
- **`N_SECONDARY = 3`** means roughly 8 diagnoses per patient are counted and discarded, and the
  three kept have no codes, so they cannot be placed in the hierarchy.
- **The patient portal is the only surface showing comorbidities.** Every clinical view renders
  the principal diagnosis and stops, even though the API already returns the secondaries.
- **The weekly rules are diagnosis-blind** — 2 kg adds +7 points whether the patient has heart
  failure or a new knee.

Also measured: Charlson band against discharge score (0.55 correlation, 10.7% mean at Charlson 0
rising to 32.3% at 8+), with the note that the week-4 column inherits that relationship through
the simulator rather than demonstrating anything.

`notebooks/mimic/mimic_icd_analysis.ipynb` computes the same analysis on full MIMIC-IV, where the raw
`diagnoses_icd` table exists. It finds its inputs by searching `/kaggle/input` recursively for
csv/csv.gz/parquet, so no path editing is needed, and reports whether it is reading the full
dataset, the demo, or a sample. The final cell prints a summary block designed to be pasted back
into the documentation to replace the 2,000-patient figures. All 18 code cells were smoke-tested
locally against the 100-row sample file.

`docs/mimic/mimic_cohort_icd_index.md` and `.csv` list all 1,062 principal codes in the loaded cohort,
grouped by chapter.

### Rewritten against the full dataset

The notebook came back run on all of MIMIC-IV — 6,364,488 diagnosis rows, 545,497 admissions,
223,291 patients — and several figures moved enough to matter:

| | 2,000-patient cohort | Full MIMIC-IV |
|---|---|---|
| Distinct ICD codes | 1,062 principal | **28,562** |
| Diagnoses per admission | median 11 | **median 10, mean 11.7, max 57** |
| Single-diagnosis stays | 1.2% | **2.6%** |
| Admissions spanning 2+ chapters | 76.8% (partial resolution) | **96.1%**, mean 6.1 chapters |
| Codes used exactly once | 685 of 1,062 | **6,160 of 28,562** |

`docs/mimic/mimic_disease_landscape.md` was rewritten around those numbers and pitched at a
non-specialist reader. Findings the full data added:

- **The largest chapter is not a disease chapter.** "Factors influencing health status" — Z
  codes for smoking history, long-term anticoagulants, long-term insulin — touches 72.7% of
  admissions. With symptom and external-cause codes, **~28% of all diagnosis rows are not
  diseases**.
- **Coding detail is inversely related to prevalence.** Hypertension has 17 codes and 139,717
  uses; strokes have 319 codes and 27,324. Injury has 7,486 codes; endocrine has 807 for twice
  the admissions.
- **250 codes — under 1% of them — cover half of every diagnosis row ever recorded.**
- The median admission (10 diagnoses) spans **10 different chapters**, and the worked example is
  a compelling one: an anaemic, unsteady, blind, osteoporotic patient with a history of falls
  whose principal diagnosis is "iron deficiency anaemia".

---

## Phase 22 — ICD feature engineering: the answer, with evidence

Can each ICD code be mapped into features that help training and explainability, at discharge
and weekly? `docs/mimic/icd_feature_engineering.md` answers it. **Not one feature per code** — 21.6%
of codes appear on exactly one admission and only 207 clear 1% support, and the ICD-9/ICD-10
split would divide each condition across two columns. Grouped features, in five levels.

**The finding that matters.** The Phase-1 notebook already computes all 17 Charlson condition
flags with the Quan et al. (2005) crosswalk, applies the severity hierarchy, and then does:

```python
cci["charlson_score"] = sum(cci[c] * w for c, (w, _, _) in CHARLSON.items())
```

Only the sum reaches the model. **The 17 flags are computed and discarded on every run.** Adding
them is a one-line change to the feature list — no new data, no new mapping, no new dependency —
and it turns "Comorbidity burden: 5" into "Chronic kidney disease", which is the difference
between a number and an action.

Also proposed: 20 chapter flags; list-shape features (`n_chapters`, `n_status_codes`,
`n_complication_codes`, `principal_chapter` — the coder's judgement about why the patient was
there, currently discarded); and named combinations for pairings Charlson cannot see at all,
notably **atrial fibrillation**, which is not a Charlson condition despite 4,951 admissions
carrying it alongside heart failure.

`notebooks/mimic/mimic_icd_feature_engineering.ipynb` builds every proposed feature on full MIMIC and
scores each one by prevalence, readmission rate and lift, labelling it `useful`, `too rare` or
`no signal alone`, then exports a `hadm_id`-keyed parquet designed to join onto
`phase1_matrix.parquet`. All 13 code cells smoke-tested locally. The point is to start the
retrain from evidence rather than a wish list — and the doc is explicit that univariate lift is
a screen, not proof, and that the honest test is AUC-PR plus calibration on the same
`GroupShuffleSplit`.

**The weekly half.** Ten clinical groups derived from the codes, each with different weights,
different wording, and — the larger practical win — a different set of signals worth collecting.
A 2 kg weekly gain becomes ~+10 in heart failure and near-zero post-surgically; SpO₂ is scored
against the patient's own baseline in COPD rather than against 92%; weight *loss* becomes the
risk direction in oncology. Stated plainly in the doc: these are clinically-reasoned defaults,
not learned values, because MIMIC has no post-discharge vitals to fit them against.

Dependency worth noting: **everything at discharge time is blocked behind one re-run of the
Phase-1 notebook**, since the training matrix keeps no codes. Everything on the weekly side is
buildable today, because Mongo already holds `primary_icd_code` for every patient.

---

## Phase 23 — Disease-specific weekly monitoring

The weekly rules applied one rule set to everybody: a 2 kg gain added +7 points whether the
patient had heart failure or a new knee. That is wrong in both directions — two kilos in a week
is *the* warning sign in heart failure and close to meaningless after orthopaedic surgery.

**`models/icd_groups.py`** turns a patient's diagnoses into one of eleven clinical groups, using
the same Quan et al. Charlson crosswalk the model's `charlson_score` is built from, plus
chapter-level patterns for sepsis, injury and mental health — none of which are Charlson
conditions. The groups are not invented: each was measured across 534,227 MIMIC-IV admissions
against a 19.02% base rate, spanning 0.53× (general) to 1.46× (oncology).

Resolution is deliberate. The **highest-priority group found anywhere wins** — principal code,
principal title, or any secondary title — with the principal code only breaking ties. The
alternative, "principal code always wins", would monitor a patient admitted with pneumonia and
severe heart failure as a lung patient, and their weight would stop being the signal that
matters.

**`models/monitoring_rules.py`** gained group profiles. A profile changes three things:

| | |
|---|---|
| `weights` | scale the points — 0.15 says the signal is nearly meaningless here, 1.6 says it is what will bring them back |
| `rules` | replace a rule outright where the DIRECTION of risk differs |
| `phrasing` | override the wording for one (signal, branch) pair |

Every rule now returns a branch key alongside its points, which is what makes targeted phrasing
overrides possible without duplicating the whole rule set per group.

Two rules are replaced outright rather than reweighted:

- **Oncology weight.** Loss is the risk, not gain. Cachexia and poor intake predict
  deterioration; a gain is usually steroid fluid or appetite returning. The heart-failure rule
  would have scored recovery as decline.
- **Respiratory SpO₂.** 88–92% is the *target* range in COPD, so the general thresholds flag a
  patient's normal state every week. Measured: 90% now scores **0.00** for a lung patient and
  87% scores +4.50, where the generic rule gave +3.00 for both.

The same +2.2 kg reading, across four groups:

| Group | Points | What the card says |
|---|---:|---|
| Heart failure | **+11.20** | "the single most reliable early warning… roughly two litres of fluid" |
| Sepsis | +2.80 | "not the signal to watch after sepsis" |
| Mental health | +1.40 | "more often an effect of the medication than a warning" |
| Surgical | **+1.05** | "usually appetite returning rather than fluid" — drops out of the top three entirely |

`general` is byte-identical to the pre-change behaviour (verified: same observation set, 58.5 /
+18.5 before and after), so the default path did not move.

**Group-aware collection.** `signal_plan()` drives the weekly logging form: a lung patient is
asked for oxygen saturation first and told weight carries little weight for them; a mental-health
patient is asked for attendance, adherence and refills, with all four vitals collapsed under
"other readings, if you have them". Asking everybody for the same seven readings every week
trains people to stop filling any of them in.

**Nothing is applied silently.** The trend panel shows *Monitored as: Heart failure*, what the
group was decided on, and marks a title-only match as approximate — because the loader keeps no
codes for secondary diagnoses. Gemini receives the group too, and now writes *"the weight gain is
expected as appetite returns after surgery and should not be treated as fluid retention"* for a
post-operative patient given the same numbers that produce a fluid-overload warning for a
heart-failure one.

**Group distribution across the 2,000-patient cohort**, and the honest limitation:

| | App cohort | Full MIMIC |
|---|---:|---:|
| general | 32.0% | 16.7% |
| surgical_injury | 11.2% | 8.4% |
| heart_failure | 9.8% | 15.1% |
| oncology | 9.4% | 8.4% |
| mental_health | 6.3% | 13.7% |

The app assigns "general" twice as often as the notebook does, because it can see one code plus
three secondary *titles* rather than all ten codes. 567 patients were grouped on an exact code
match, 793 on a title keyword, and 640 defaulted. Raising `N_SECONDARY` and keeping codes for
secondaries would close most of that gap — it is the same blocker as the discharge-time work.

The weights remain **clinically-reasoned defaults, not learned values**, exactly like the base
rules: MIMIC has no post-discharge vitals to fit them against. They are written down with their
reasoning so a clinician can argue with them.

10,000 weekly documents regenerated. Scores changed by design; the drivers, wording and ordering
now differ by condition.

---

## Phase 24 — Correction: the Charlson flags were never missing

Phase 22 claimed the Phase-1 pipeline computed the 17 Charlson condition flags and discarded
them, keeping only the summed score, and called adding them "the finding that matters most".

**That was wrong.** All 17 are columns in `phase1_matrix.parquet` and all 17 are in the model's
94-feature list. The error came from checking the feature names for "diag", "icd", "charlson" or
"comorb" — none of which match `congestive_heart_failure`. **19 of the 94 features are
diagnosis-derived, not 2.**

What survives the correction:

- The model already distinguishes heart failure from kidney disease from cancer. It cannot see
  **sepsis, atrial fibrillation, fractures or mental health conditions** — none are Charlson
  conditions — so that specific example still holds while the general claim does not.
- The cerebrovascular and dementia sign problem is real for the summed *score* but not for the
  model, which has both flags separately and can learn their true direction.
- Everything else proposed — principal chapter, chapter flags, list shape, combinations — is
  genuinely absent.

`docs/mimic/icd_feature_engineering.md` and `docs/mimic/mimic_disease_landscape.md` were corrected in place
rather than quietly edited: both now state what the earlier version claimed and why it was wrong.

Second discovery in the same pass: **`phase1_diagnoses.parquet` exists locally** — 296,433
admissions of principal code, version, title, three secondary titles and the true diagnosis
count. Adding patients with real diagnoses needs no raw MIMIC download.

---

## Phase 25 — 4,000 patients, and a worklist that loads in under a second

### The cohort doubled

`scripts/load_mimic_to_mongo.py --limit 4000 --preserve-existing`. The new flag reads the
patient ids already in `patient_worklist` and tops up from the remainder, because
`.sample(4000)` is not a superset of `.sample(2000)` — a fresh draw would have orphaned every
patient account in `data/runtime/users.db` whose `patient_id` fell out.

4,000 patients, 7,902 admissions, 20,000 weekly monitoring documents. The loader also resolves
each patient's clinical group at load time and writes it on the row, so the dashboard can filter
by condition with an indexed equality match rather than classifying 4,000 rows per request.

### The worklist was 27 seconds. It is now under one.

The old endpoint read every worklist row with no projection, aggregated the entire
`weekly_monitoring` collection and the risk registry, normalised the lot in Python, and only
then sliced out the requested page. The cost grew with the **cohort**, not the page size — so
doubling the data would have doubled the wait.

Three changes:

1. **`scripts/refresh_worklist_summary.py`** denormalises the trend summary onto the row —
   `current_score`, `current_band`, `trend_delta`, `monitoring_status`, `weeks_tracked`, the
   precomputed `primary_driver_label`, and `status_rank`/`band_rank` so trend and band sort
   correctly in MongoDB. It is correct to cache because these change only when the loader or the
   simulator runs. Ten indexes built alongside.
2. **The endpoint filters, sorts and pages in MongoDB**, with a `patient_id` tiebreak so paging
   is stable — without it two rows with equal scores swap between pages and a patient is shown
   twice or not at all. `driver_2` and `driver_3` left the payload; nothing rendered them.
3. **A 60-second cache** on the batch date and on filter counts. Every Atlas round trip from
   this machine costs about 0.7s, and a page request was making three.

| Request | Before | After |
|---|---:|---:|
| Dashboard page (25 rows of 4,000) | 27.1s | **0.15–0.7s** |
| Filtered by condition | — | 0.5s |
| Page 40, sorted by diagnosis | — | 0.3s |
| Diagnosis search | — | 0.7s |

Profiling found the remaining limit is bandwidth, not query time: 4,000 full rows are 2.7 MB and
this link moves about 110 KB/s from Atlas, so a full export still takes ~26s. `count` alone is
2s of pure round trip. That is why the answer was "send one page", not "send it faster" — and
why CSV export now issues its own request behind a *Preparing…* state instead of serialising
whatever is on screen.

### Filter by condition

A dropdown on the worklist, populated from `GET /api/patient-groups` so it only ever offers
groups that would return rows, with counts:

    General recovery 1266 · Surgery or injury 431 · Heart failure 414 · Cancer 382
    Chronic lung disease 321 · Heart disease 282 · Mental health 250 · Diabetes 230
    Stroke 179 · Kidney disease 132 · Sepsis 113

It lives in the URL (`?group=heart_failure`), so a filtered worklist is shareable. Search now
matches the diagnosis text and ICD code as well as the patient id — a coordinator looking for
"pneumonia" should not have to know an id.

One thing the first version got wrong on screen: filtering to heart failure showed patients whose
*admitting* diagnosis was something else, because the group can come from a secondary diagnosis.
Correct behaviour, confusing display. The table now shows the monitoring group under the
diagnosis, so the filter explains itself.

---

## Phase 26 — Training notebook for the ICD features

`notebooks/mimic/mimic_icd_training.ipynb` trains the current model and an ICD-enriched model on the
**same split with the same hyperparameters** and compares them.

It reproduces Phase 1 exactly rather than approximating it: `GroupShuffleSplit` on `subject_id`
at 20%, then 20% of the remainder for calibration; `HistGradientBoostingClassifier(max_iter=400,
learning_rate=0.06, max_leaf_nodes=31, min_samples_leaf=40, l2_regularization=1.0)` with native
categorical support; isotonic `CalibratedClassifierCV` on the held-out fold. Both models get
identical rows, so any difference is the features and nothing else.

Features added — and the ones deliberately not added, on the evidence:

| Added | Rejected | Why rejected |
|---|---|---|
| `principal_chapter` | `dx_atrial_fibrillation` | 1.08× alone, and AF+heart-failure scored *below* heart failure by itself |
| 10 selective chapter flags | circulatory, health-status, endocrine, musculoskeletal flags | all ~1.05×; a flag on two thirds of admissions separates nothing |
| `n_chapters`, `n_categories`, `n_status_codes` | 17 Charlson flags | already in the model — see Phase 24 |
| `has_complication` as a binary | | the count version collapsed to one quantile bin and never got a verdict |
| `dx_sepsis`, 4 combinations | | |

It reports AUC-ROC, AUC-PR, Brier and calibration slope, with **Brier and calibration weighted
as heavily as discrimination** — the ROI layer multiplies by the predicted probability, so a
model that ranks better while being over-confident is worse for this application. It also gives
an operational view (readmissions caught in the top 500 and top 1,000 by risk), SHAP attribution
showing whether the model actually reaches for the new features, and a printed verdict that
states plainly when AUC-PR did not improve or calibration got worse.

Exports `phase1_model_icd.joblib` in the same `{model, features, categoricals, threshold}` shape
the application already loads, the enriched matrix, and a JSON summary to paste back.

Smoke-tested locally: all 13 code cells ran on a 20,000-row subsample. The numbers there are
meaningless — only the 100-row sample diagnoses file is on this machine, so the chapter and shape
features were empty — but every code path executed, including the verdict logic, which correctly
reported "the model barely uses the new features".

**Upload two inputs on Kaggle**: a MIMIC-IV dataset, and `phase1_matrix.parquet` from
`data/mimic/model/results/`.

---

## Phase 27 — The training result: the ICD features do not improve the model

The notebook came back run on full MIMIC-IV. 296,760 admissions, 148,669 patients, a 59,835-row
test fold split by patient, baseline 94 features against the same model with 21 ICD features.

| Metric | Baseline | Enriched | Difference | Bootstrap 95% CI |
|---|---:|---:|---:|---|
| AUC-ROC | 0.7229 | 0.7257 | **+0.0027** | [+0.0010, +0.0042] significant |
| AUC-PR | 0.3921 | 0.3922 | **+0.0001** | [-0.0026, +0.0025] **not significant** |
| Brier | 0.1404 | 0.1402 | -0.0002 | negligible |
| Calibration slope | 1.010 | 1.009 | -0.001 | both near perfect |

| Budget | Baseline | Enriched | Difference | 95% CI |
|---|---:|---:|---:|---|
| Readmissions in the top 500 by risk | **341** | 336 | -5 | [-22, +11] |
| Readmissions in the top 1,000 | **648** | 635 | -13 | [-32, +16] |

The bootstrap was run locally against both saved bundles on the reproduced test fold; the
reproduction matched the notebook to four decimals (0.7229 / 0.7257), so the split and models are
faithful.

**The AUC-ROC gain is real and irrelevant.** Statistically significant, operationally invisible.
AUC-ROC is dominated by the mass of negatives, so the new features improved separation at the
low-risk end; AUC-PR and the top-N catch rate are dominated by the high-risk end, which is the
only end the worklist uses, and neither moved.

**What the model used.** The 21 features carry 6.5% of SHAP attribution, so they are not ignored.
`chap_blood` ranks 22 of 115 — above most of the original 94 — followed by `n_symptom_codes` 24,
`chap_neoplasm` 32, `chap_genitourinary` 38, `chap_nervous` 42. The most useful new feature was a
body system **Charlson does not cover at all**, which is the one clue pointing anywhere: it
argues for Elixhauser's 31 conditions rather than for chapter flags.

**What was refuted — mine.** I called `principal_chapter` "the strongest new signal" on a 3x
univariate spread. It ranks **110 of 115**, mean absolute SHAP 0.00003: effectively unused. The
spread was real and entirely explained by features already present — admission type, discharge
disposition, age, labs. Univariate lift said "informative"; the model said "I already knew that".
The four hand-built combinations rank 92-106 and `dx_sepsis` ranks 81 despite a 1.29x lift,
confirming the stated caveat that a boosted tree derives interactions from the component flags.

**Recommendation: do not ship it.** Beyond the flat result, deploying would first require storing
every diagnosis code at load time, because the app holds one code plus three secondary titles and
cannot compute `n_chapters` or `chap_blood` without the rest — and it would hand manual entry 21
features it has no way to fill. Real work for a gain that never reaches the worklist.

Nothing on the weekly side is affected. The Phase 23 grouping never claimed to improve the
discharge model; it changes what a card says and what the programme collects, which no AUC
measures.

Artefacts kept at `data/mimic/model/results of icd training/`.

---

## Phase 28 — Disease-specific monitoring: baselines, normalisation, four panels

Phase 23 changed the weights and the wording of seven signals. It never changed **what gets
measured** — a heart failure patient and a post-operative patient were still asked for the same
seven things, of which three (adherence, refills, follow-up) are universal by nature and two
(blood pressure, resting pulse) are weakly informative for most groups.

Three pieces, in the order they had to be built.

### 1. The discharge baseline

`models/discharge_baseline.py`. Disease-specific monitoring is mostly comparison against the
patient, not against a population: "two kilos above dry weight" is a warning, "84 kg" is not.

Before this there was **no per-patient clinical reference at all**. An unsupplied signal fell
back to a population value — SpO₂ 97%, systolic 125 — so every threshold was a population
threshold with a disease label attached. That is exactly the failure the COPD saturation rule was
written to avoid, and it would have recurred for every new signal.

Six fields, each consumed by an actual rule: dry weight, usual SpO₂, usual systolic, usual
pulse, usual walking distance, pain at discharge. `relative_observations()` converts absolute
readings against them — current weight becomes weight change, metres walked becomes percent of
usual — so the rules stay pure functions of one value and the comparison lives in one place.

Values are **simulated**, derived deterministically from the patient id and conditioned on the
group, so a lung patient's baseline saturation sits at ~91% where it belongs. They carry
`source: "simulated"` and the UI says so. In a live deployment this record is filled in by
whoever discharges the patient; the shape and the API do not change when that happens.

### 2. Score normalisation

Extra signals mean extra points to accumulate. Measured before the fix, the worst attainable week:

| Group | Signals | Worst attainable |
|---|---:|---:|
| general | 7 | +37.0 |
| respiratory | 10 | +53.2 |
| sepsis | 10 | +58.1 |
| **heart failure** | 10 | **+60.9** |

The worklist sorts by score. Heart failure would have drifted to the top of every list for having
**65% more boxes to tick**, which looks like a clinical finding and is arithmetic. Each group's
extremes are now scaled onto the general group's range — every group's worst attainable week is
+37.00 and best is −6.30, verified. Points still **sum** within a group, because three problems
really are worse than one and averaging would hide that; only the range is equalised. General is
the reference, so an ungrouped patient's score is unchanged.

### 3. Four condition panels

Ten new signals across four groups — heart failure, chronic lung disease, surgical recovery,
sepsis — covering 1,279 of 4,000 patients. Every threshold is published, not invented:

| Signal | Threshold, and where it comes from |
|---|---|
| Pillows to sleep | orthopnoea is on the standard heart-failure zone chart given to patients at discharge |
| Ankle swelling | visible fluid retention, read alongside the weight |
| Walking distance | against the patient's **own** usual distance, from the baseline record |
| Rescue inhaler uses | more than twice weekly is the accepted marker of poor control |
| Sputum change | Anthonisen criteria — increased volume *and* purulence define an exacerbation |
| Temperature | 38.0 °C, the neutropenic-fever and post-operative assessment threshold |
| Wound | clean / red / discharge / opening |
| Pain trend | should fall after surgery; rising pain is a symptom, not a tolerance problem |
| Antibiotic course | an unfinished course after sepsis is the highest-priority item on the card |
| New confusion | part of every sepsis screening tool, and often the first thing a family notices |

**Capped at +6.0**, below medication adherence at +8.0. Adherence and follow-up attendance have
the strongest evidence base of anything in the panel, and a first pass at disease-specific
monitoring should not outrank them.

The cards changed as intended — each group now leads with a condition-specific finding:

    heart failure   Pillows needed to sleep: 2
    lung disease    Sputum change: both — two of the three Anthonisen criteria
    surgical        Wound: discharge — the most common reason a post-surgical patient returns
    sepsis          Antibiotic course: stopped early

The weekly form asks only what the patient's group is scored on, condition-specific questions
first, in plain language — "furthest you walked", "pillows to sleep", "your wound" — and shows
the baseline behind a disclosure so a patient can see what their readings are compared against.

**Not done, deliberately:** the other six groups keep the plain seven until these four are shown
to work, and `general` is untouched. No signal was added without a published threshold.

Still clinically-reasoned defaults rather than learned values, for the same reason as before:
MIMIC has no post-discharge data to fit any of it against. The weights, the thresholds and the
baselines are all written down with their reasoning so a clinician can argue with them.

---

## Phase 29 — Two documents written for people outside the project

- **`docs/project_timeline.md`** (new): every stage in order — the UCI baseline, the CMS
  build, MIMIC acquisition, the discharge model, weekly monitoring, and the refinement
  work — with each figure traced to the artefact it came from rather than recalled.
- **`docs/mimic/icd_codes_explained.md`** (new): a plain-English account of how illness is recorded,
  arranged data-first because the numbers are what people ask for. Who the patients are, how
  many conditions each carries, then what an ICD code actually is and how to read one.
- Both were figure-checked against the repository before delivery. That pass caught the claim
  that the deck reported a 0.6463 baseline (it reports 0.7063 — 0.6463 is the track that
  *failed* the gate) and the description of the 200-row `finalmerged.csv` as the CMS build.

## Phase 30 — ICD grouping: "history of" is not a diagnosis

Prompted by a heart-failure filter returning a patient admitted for toxic liver disease. That
one turned out correct — the patient has documented heart failure as a secondary — but auditing
all 4,000 to prove it surfaced two real defects in `models/icd_groups.py`.

- **64 patients were grouped on a resolved condition.** Substring matching cannot tell
  *"Personal history of malignant neoplasm of breast"* from active cancer. 57 patients were on a
  cancer monitoring plan for a cured one, 6 on a stroke plan from a past TIA, 1 on a mental-health
  plan from *"Personal history of suicidal behavior"*.
- **11 were grouped on an explicit negative** — *"Hypertensive heart and chronic kidney disease
  **without** heart failure"*, *"Age-related osteoporosis **without current** pathological
  fracture"*.
- Fixed with a clause-scoped negation guard plus a whole-title guard for `Z85`/`V10`-style history
  codes. Scoped so it cannot over-fire: *"Diabetes mellitus without mention of complication"* is
  still diabetes, because the negation follows the condition rather than preceding it.
- **75 patients reclassified.** Largest moves: oncology → general 38, neuro_stroke → general 7,
  surgical_injury → general 6, oncology → cardiac_other 6.
- Weekly narratives are written in group-specific language, so a label change alone would have
  left 75 patients with stale reasoning. The simulator was re-run in full; per-patient seeds mean
  the other 3,925 reproduce byte-identically. Verified afterwards: **0 of 20,000 weekly documents
  disagree with the worklist**.
- Audit result on the group that started it: of 413 heart-failure members, **0 have no documented
  heart failure and 0 heart-failure patients are missed**.

## Phase 31 — One plan, many conditions

`clinical_group` is the single plan a patient is monitored under — the highest-priority condition
wins, because a patient can only be on one plan. Filtering on it hid people.

- **`models/icd_groups.classify_all`** (new) returns *every* group a patient's diagnoses support,
  best evidence first. `classify_all[0]` is the same pick `classify()` makes — verified across all
  4,000.
- **`scripts/backfill_group_membership.py`** (new) writes `clinical_groups` and `group_matches`
  onto each worklist row and builds the multikey index the filter runs on.
- **21.8% of the cohort carries two or more conditions.** Membership filtering recovers them:
  heart disease 288 → **547**, surgery/injury 430 → **664**, mental health 254 → **374**,
  stroke 175 → **269**. Heart failure gains nothing, being top priority already.
- **`ConditionFilter.jsx`** (new): multi-select with counts, chips, and an any/all toggle.
  Selections live in the URL, so a filtered worklist is shareable. Heart failure **or** diabetes
  returns 691; **and** returns **24** — an intersection previously unreachable.
- `/api/patients` accepts `group=a,b,c` with `match=any|all`, `$in` or `$all` against the multikey
  index. 691 docs examined, 0.3–0.6s — no slower than the single-group filter.
- **Every diagnosis now renders**, not only the admitting one, each tagged with the condition it
  evidences. Text search reaches secondary diagnoses too: "atrial fibrillation" returns 170
  patients, none findable before.
- **`DiagnosisList.jsx`** (new) puts the same list in the patient detail drawer, unfolded — the
  worklist is a table and has to abbreviate; the drawer is where someone decides what to do.

## Phase 32 — A client deck, built from the repository

- **`scripts/build_client_deck.py`** (new) generates `docs/deliverables/Preventra_CMS_to_MIMIC.pptx`
  — four 16:9 slides: the diabetes baseline, CMS and why it was left, MIMIC and the model, and the
  cohort's disease burden.
- Kept in code rather than hand-made so a corrected number is changed once and the deck rebuilt,
  instead of being retyped into a shape and drifting from the documents behind it. Every figure was
  grep-verified against `project_timeline.md` and `icd_codes_explained.md`.
- Each build was rendered to PNG through LibreOffice and inspected. That caught headlines colliding
  with the paragraph beneath them, drop shadows inherited from the theme's `effectRef` despite an
  empty `effectLst`, and a comparison column measured against the grid rather than its card.
- It also caught a content error: *"Hypertensive kidney disease + chronic kidney disease"* had been
  shortened to *"Hypertensive + kidney disease"* to fit a column, which changed what the pair
  claimed — while the note beneath pointed at it as a recognised clinical combination.
- Fonts are restricted to Georgia / Calibri / Consolas. The web version uses Newsreader and IBM
  Plex; those would fall back silently on a client machine.

## Phase 33 — Three corrections

- **The CMS score was wrong.** `0.8593` was superseded by **`0.6893`**, which inverts the story:
  CMS now sits *below* the 0.7063 diabetes baseline rather than above everything. `project_timeline.md`
  Stage 1 and Stage 3 were rewritten — *"why move to MIMIC, when the CMS numbers were better?"*
  no longer holds. The fold table, PR-AUC 0.3627 and Brier 0.0740 came from the same superseded
  report and were removed rather than left beside a corrected AUC; both facts are recorded in the
  document so nobody re-derives them from an earlier draft. The `DAYS_TO_NEXT_ADMISSION` leakage
  note in that stage is now stated as the leading explanation for the higher figure.
- **`DriverCard.jsx` was rendering lab values as percentages.** `formatValue` multiplied any value
  containing a decimal point by 100 and appended `%`, so albumin 2.9 g/dL displayed as **290%** and
  potassium 4.1 mEq/L as **410%** — a clinically nonsensical reading shown to coordinators. Before
  removing it, all 24,000 driver strings were scanned: **1,604 decimal values across 21 labels, all
  laboratory results; 3,131 genuine percentages, none containing a decimal**. Nothing needed the
  conversion. (Had a percentage ever carried a decimal, `97.5%` would have rendered as `9750%`.)
- **Provider attribution removed from the UI.** Four user-facing strings named Gemini; they now
  read "Generate insights", "Explain this week", "Explanation". Verified live — zero occurrences in
  the rendered page, including after triggering a real call. Python docstrings still name it, being
  developer documentation that never reaches the screen.

## Phase 34 — Risk bands fixed at 20 / 40

Bands were derived from the score distribution — High at the model's 60%-recall operating point
(22.43%), Medium at the median predicted risk (16.51%). Defensible statistically, unusable in
practice: the numbers meant nothing on screen and moved on every retrain, so a patient could change
band without anything about them changing.

- Now **Low under 20%, Medium 20–40%, High 40% and above**, fixed in
  `docs/mimic/band_thresholds_mimic.json`. The loader no longer recomputes them; the API and simulator
  fallbacks carry the same constants so a missing file cannot silently re-band the cohort.
- **`scripts/apply_risk_bands.py`** (new, idempotent) re-bands `patient_worklist.risk_band`,
  `current_band`, `weekly_monitoring` and `risk_registry`, then rebuilds `executive_summary`.
- Cohort moves: High 1,137 → **660**, Medium 316 → **582**, Low 2,547 → **2,758**. Boundaries
  verified exactly — 19.7 Low, 20.3 Medium, 39.6 Medium, 40.1 High — with **0 mismatches across
  32,000 scored records**.
- **A second bug surfaced.** The Executive Summary header said High 878 while the worklist filter
  returned 660. The header counted each patient's *discharge* band, frozen at load time; the
  worklist filters their *current* band after four weeks. They had never agreed — before this change
  it was 878 against 1,137. Both now read the current band.
- Caveat recorded: the old High floor *was* the model's 60%-recall operating point, so a team
  working only the High band now reviews fewer patients than the model was tuned to surface. The
  20/40 split is far easier to explain; it should not be claimed to correspond to any particular
  recall.

## Phase 35 — README, and a portable patient sample

- **`README.md`** rewritten from an 8-line stub into a full project account: workflow diagram,
  repository map, the three-dataset lineage, the model and all 94 features, the four load scripts,
  weekly monitoring, ICD grouping, bands, the cost model, all 32 endpoints, configuration, a
  runbook, and a known-limitations section. Every path, script, CLI flag and live figure was
  verified against the repository before delivery.
- **`scripts/export_patient_sample.py`** (new): exports N patients across every collection to a
  folder, CSV and JSON, with a generated README. Patients are chosen by round-robin across bands
  *then* groups — cycling groups first fills the whole sample from the High buckets before reaching
  a Medium one, which the first version did. Default run gives 4 High / 3 Medium / 3 Low across
  four clinical groups, 10 worklist rows, 50 weekly rows, 85 registry rows, all keyed to the same
  ten ids.

## Open items

1. **Old batch pipeline is inconsistent.** `pipeline/batch_flow.py` and
   `outputs/export_worklist.py` still import `models.driver_extractor` and score with the UCI
   DecisionTree from `mlruns`. Running either would write UCI-scored patients with incompatible
   driver labels into the same `patient_worklist` the MIMIC API reads.
2. ~~**"Weekly Risk Trend" needs relabelling.**~~ **Already fixed** in the 2026-09-01 commit; this
   list was stale. `WeeklyTrendPanel` switches every label on the response's `kind` — "Weekly
   Post-Discharge Monitoring" vs "Readmission Risk Trend", "Weeks Monitored" vs "Admissions Scored",
   "week" vs "admission".
3. ~~**`DriverCard.jsx`** multiplies any decimal driver value by 100 and appends `%`.~~
   **Closed in Phase 33.** The conversion is removed. All 24,000 stored driver strings were scanned
   first: every decimal value is a laboratory result and every genuine percentage already carries
   its own `%` without a decimal, so nothing needed it.
4. **Phase 2 weekly monitoring remains unsupported** by MIMIC. A real weekly cadence needs
   All of Us wearables or Preventra's own telemetry once live.
5. ~~**The ROI formula has no intervention-effectiveness term.**~~ **Closed in Phase 16** — a 25%
   effectiveness factor is applied, the arithmetic moved to `api/roi_model.py`, and every cost is
   an itemised line the UI can display. Remaining follow-up: the line items are published-average
   defaults, so a deploying organisation should substitute its own finance figures.
6. **Lab aggregation applies no physiological bounds.** `lab_*_max` features carry values like a
   glucose of 85,189 mg/dL. Harmless to the tree model, fatal to anything linear — and to any chart
   drawn on an unclipped axis. The `omr` parsing path already has the bounds logic to copy.
7. **There is no authentication.** Sign-in was removed in Phase 37, leaving one shared
   `X-API-Key` as the only gate — and that key is compiled into the public frontend bundle, so
   anyone who can load the dashboard can read it. No identity, no per-record scoping, no audit of
   who read what, and no way to revoke one client without rotating the key for all of them. This
   is the largest single gap between the demo and anything that could hold real patient data.
   `docs/ROADMAP.md` §1 is the plan.
8. **Atlas IP allowlist** must include the current IP; a mismatch surfaces as a TLS handshake
   failure, not an auth error.
9. **Monitoring feed names are placeholders.** The device hubs, medication apps, pharmacies and
   clinics shown on the weekly cards are generated from the patient id, not received from anyone.
   The document shape and the API do not change when a real integration lands — only
   `models/monitoring_rules.source_for` does — but until then no card should be read as evidence
   that a pharmacy actually reported anything.
10. ~~**`/api/patients?limit=500` takes about 27 seconds.**~~ **Closed in Phase 25** — server-side
    filtering, sorting and paging plus a denormalised trend summary brought it to 0.15-0.7s.
    Remaining: a full 4,000-row CSV export still takes ~26s because the link from Atlas moves
    about 110 KB/s and the payload is 2.7 MB. It runs behind a "Preparing…" state.
11. **The diagnosis extract keeps four diagnoses per stay**, against a mean of 11.7 coded.
    `N_SECONDARY = 3` in `models/mimic_diagnoses.py` keeps the principal plus three secondary
    *titles*, and only the principal keeps its ICD code. Three consequences, all still open:
    33% of patients default to "general" (against 16.7% measured on full MIMIC) because their
    condition was coded fifth; secondary matching is keyword-based on prose rather than exact on
    codes, which is why Phase 30's negation guards were needed at all; and the UI has to state how
    many diagnoses it cannot show. Re-exporting the parquet with `N_SECONDARY` raised and
    `(code, version)` retained closes all three — every function downstream already handles a
    longer list.

12. **The Kaggle API token needs rotating.** It was used outside this repository and should be
    treated as exposed. Expire it at kaggle.com → Settings → API and keep the replacement in
    Kaggle Secrets rather than anywhere it can be read.

13. **Re-hosting MIMIC-IV needs checking against the DUA.** PhysioNet's agreement prohibits
    redistribution, including to another platform. Any copy held outside PhysioNet should be
    private at minimum, and that is the floor rather than clearance.

14. **`DAYS_TO_NEXT_ADMISSION` may have leaked into the CMS feature set.** It determines
    `READMITTED_30D`, and it is the most plausible explanation for the 0.8593 that was reported
    before the figure was corrected to 0.6893 (Phase 33). A one-line check against the CMS training
    code would settle it; until then none of that run's other metrics should be quoted.

15. **The CMS 0.6893 and the UCI "decision tree, balanced" 0.6893 are the same number.** Two
    different models on two different datasets landing on an identical four-decimal figure is worth
    confirming is a coincidence rather than a transcription.

## Phase 36 — Repository filed by dataset phase

`data/`, `docs/` and the notebooks had accumulated three eras of the project in one flat layer,
with CMS and MIMIC artefacts interleaved and two notebook folders differing only in
capitalisation — `Notebooks/` and `notebooks/`, which is invisible on a case-insensitive
filesystem and a trap on a case-sensitive one.

- **Everything is now filed by phase**: `diabetic/`, `cms/`, `mimic/` inside each of `data/`,
  `docs/` and `notebooks/`. `data/` also gains `reference/` (public datasets used for comparison,
  belonging to no phase) and `runtime/` (what the running app reads and writes — `users.db`, the
  risk registry, batch `input/`/`output/`, exported samples).
- **`Notebooks/` is gone.** Its notebooks moved to `notebooks/cms/`; its CSVs were data and moved
  to `data/cms/`. Its eight `sample1_*.csv` were byte-identical to `data/CMS samples/` and were
  removed as duplicates.
- **Notebooks no longer live in `data/`.** The four under `data/Mimic_samples/` — including
  `phase1_discharge_risk_mimic.ipynb`, which builds the served model — moved to `notebooks/mimic/`.
- **Two long-standing path warts fixed**: `MIMC Phase1 model metadata` (typo, spaces) is now
  `data/mimic/model`, and `eda results` is `data/mimic/eda`.
- **79 moves, 206 references rewritten across 46 files** — Python constants including the
  `os.path.join` forms in `api/mimic_scoring.py`, plus every mention in the README, the timeline,
  HANDOVER, ROADMAP and the notebooks themselves.
- Verified after: no stale path in any source file, **42 path literals resolve and 0 break**, the
  model bundle loads from its new location, `users.db` resolves, `api.main` imports with 36 routes,
  `/api/patients` returns 200, and the dashboard renders 4,000 patients with a clean console.
- Git recorded **138 renames** rather than delete-and-add, so file history survives.
- Added `data/README.md`, `docs/README.md` and `notebooks/README.md`, each naming what belongs in
  the folder and — for `data/` and `docs/` — which paths are read at runtime and therefore cannot
  be moved without updating code alongside.

---

## Phase 37 — Sign-in removed

The username/password layer built in Phase 24 was already switched off by default
(`AUTH_ENABLED=false`), which meant the repository carried a full authentication implementation
that nothing exercised, plus a SQLite credential store that a container filesystem would wipe on
every redeploy. Ahead of deploying the backend, it was removed rather than shipped dormant.

- **Deleted from the backend**: `api/auth.py` (PBKDF2 hashing, HMAC-signed tokens),
  `api/user_store.py`, `scripts/seed_users.py`, `data/runtime/users.db`, the role-based access
  middleware in `api/main.py`, and six endpoints — `/api/auth/register`, `/api/auth/login`,
  `/api/auth/me`, and the three `/api/me/*` patient-portal routes. **32 endpoints → 26.**
- **Deleted from the frontend**: `src/auth/`, `pages/Login.jsx`, `pages/Register.jsx`,
  `pages/MyHealth.jsx`, the `localStorage` token handling and the 401 sign-out listener in
  `api/index.js`. `App.jsx` collapses from a role-branched route tree to one flat set of routes;
  `Layout`, `TopNav` and `Sidebar` no longer consult a user at all.
- **The patient portal went with it.** It resolved the patient from the signed token, so without
  sign-in it had no way to know who was asking. Rebuilding it is now part of `ROADMAP.md` §1
  rather than a standalone feature.
- **Environment variables dropped**: `AUTH_SECRET`, `AUTH_ENABLED`, `HOSPITAL_REGISTRATION_CODE`,
  `USERS_DB_PATH`, `VITE_AUTH_ENABLED`. The `data/users.db*` line left `.gitignore`.
- **What now guards the API**: only the shared `X-API-Key`, when `API_KEY` is set. The README
  section is retitled *Access control* and says plainly that this is a deployment control and not
  authentication — it cannot identify a person, scope anyone to a subset of records, or be revoked
  for one client. Logged as open item 7.
- Verified after: `api.main` imports with **26 routes**, `/api/auth/*` and `/api/me/*` return 404,
  `/api/summary` returns 401 without the key and 200 with it, the frontend builds clean, and the
  dashboard loads 4,000 patients with every request 200 and no login screen.
