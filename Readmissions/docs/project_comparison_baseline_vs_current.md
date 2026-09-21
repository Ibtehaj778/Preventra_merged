# Preventra — Baseline (Denovonet) vs. Current Project (CMS-MIMIC)

A side-by-side account of what the handed-over Denovonet repository contained, and what has been
built on top of it in `Preventra-CMS-MIMIC` since.

- **Baseline:** `/home/denovo/Desktop/Preventra-Readmission-Denovonet` → `github.com/denovonet/Preventra-Readmission`
- **Current:** `/home/denovo/Desktop/Preventra-CMS-MIMIC` → `github.com/Ibtehaj778/Preventra-CMS-MIMIC`

Compiled 2026-09-01 from the two working trees, both git histories, `donesofar.md`, `docs/HANDOVER.md`,
`docs/ROADMAP.md`, and the model artefacts on disk. Every figure below was read from a file in one of
the two repositories, not carried over from a summary.

---

## 1. The two repositories at a glance

| | Baseline — Denovonet | Current — CMS-MIMIC |
|---|---|---|
| Git history | 28 commits, 2026-03-19 → 2026-08-02 | 4 commits, 2026-08-21 → 2026-09-01 (fresh history) |
| Relationship | The handover state (`1799c17`) | Forked from that state, re-initialised as its own repo |
| Head commit | `1799c17` *Remove dead files, add handover and roadmap docs* | `c9f2a31` *Fix: UI consistency* |
| Dataset | UCI Diabetes 130-US-Hospitals — `diabetic_data.csv`, 101,766 rows × 50 cols | MIMIC-IV `hosp` — 296,760 index stays, 148,669 patients |
| Production model | DecisionTree, `readmission-dt-balanced-importance` (MLflow) | `HistGradientBoostingClassifier` + isotonic calibration (joblib) |
| Backend size | `api/main.py` 1,159 lines | `api/main.py` 1,520 lines |
| API endpoints | 20 | 24 |
| Scope | Single-disease diabetic readmission | All-cause adult inpatient readmission |

The current repo is not a rewrite — it keeps the baseline's architecture (FastAPI + MongoDB + Prefect +
React) and replaces the data, the model, and the interpretability engine underneath it.

---

## 2. What the Denovonet baseline delivered

The baseline was a complete, working product. Its four-and-a-half months of work produced:

**ML pipeline (`features/`, `models/`)**
- `clean.py`, `label.py`, `engineer.py`, `build_features.py`, `cci.py` — ~25 engineered clinical
  features from the raw UCI file; Charlson Comorbidity Index from ICD-9 codes (1987 weights).
- Four parallel training tracks — `train.py` (AUC 0.646, failed the ≥0.65 gate), `train_balanced.py`
  (0.689), `train_balanced_importance.py` (**0.706, production**), `train_xgboost.py` (0.670).
- `calibrate.py` produced risk-band thresholds and `docs/diabetic/model_validation_report_*.md` per track.
- MLflow as local model registry (`./mlruns`).

**Serving (`pipeline/`, `outputs/`, `api/`)**
- `pipeline/batch_flow.py` — Prefect flow: new discharge CSV → features → score → drivers →
  MongoDB (`patient_worklist`, `risk_registry`, `executive_summary`, `alerts`, `care_actions`).
- `outputs/*.py` — standalone CLI equivalents of the same steps.
- `api/main.py` — 20 endpoints: worklist, patient detail + score history, summary, model metrics,
  analytics, pipeline upload, manual scoring (predict / save / update / re-predict), alerts on a
  15-point jump, care coordination.
- Gemini chatbot with a deliberately safe two-stage design (`chatbot_gemini.py`,
  `chatbot_queries.py`, `chatbot_service.py`): the LLM selects one of **6 pre-written, parameterised
  MongoDB queries** and never writes query syntax itself.

**Frontend (`frontend/`)**
- React 19 + Vite + React Router v7 + Tailwind v4 + Recharts dashboard: worklist, patient detail
  page and slide-over panel, manual entry, update-and-re-score, alerts, care coordination.

**Documentation**
- `docs/HANDOVER.md` (339 lines) — architecture, file-by-file reference, and the first plain-language
  statement of which of the four models is actually in production.
- `docs/ROADMAP.md` (299 lines) — a scoped feature catalogue for a new hire: auth/RBAC, dataset
  acquisition and multi-disease generalisation, a more capable chatbot, synthetic-data fallback.

**Limitations recorded at handover:** feature-engineering, CCI and driver logic duplicated between
`features/` and an inlined copy inside `api/main.py`; no authentication of any kind beyond one shared
`X-API-Key`; single-disease, single-encounter data with no longitudinal signal.

---

## 3. What has been done in the current project

Nine phases are logged in [`donesofar.md`](../donesofar.md); a tenth landed in the 2026-09-01 commit
after that log was last written.

### Phase 1 — AI insights: ROI and counterfactual
`api/gemini_insights.py` (337 lines) calls Gemini with an enforced JSON response schema for two
things: an ROI estimate for enrolling the patient in post-discharge care coordination (cost avoided
vs. intervention cost), and a counterfactual — which driver, if addressed, would most lower the score.
`POST /api/ai-insights` is button-triggered rather than auto-fired, to control LLM cost and latency.
`AiInsightsPanel.jsx` mounts on every verdict surface; `BulletList.jsx` was written after Tailwind's
`list-disc list-inside` produced an inconsistent marker gap.

### Phase 2 — Weekly trend monitoring
`GET /api/patients/{id}/trend` builds a series from `risk_registry` and classifies each patient as
`stable` / `deteriorating` / `improving` / `action_required` / `insufficient_data`.
`POST /api/week-narrative` explains why a given week moved. New UI: `WeeklyTrendPanel.jsx` (322 lines),
`TrendStatusBadge.jsx`, a `/patients/:id/trend` route and page.

### Phase 3 — Dashboard: current vs. discharge risk
The worklist had been ranking on the stale discharge-time score, so a patient who had deteriorated to
98% could rank *below* one who had recovered to 40%. A single shared classifier
(`_classify_trend_status()`, `_weekly_series_by_patient()`) now backs the dashboard, the detail panel
and the trend page, so they cannot disagree. The worklist shows current score primary, discharge score
as a sub-line, a delta column, a trend badge, trend filters, and a clickable "Needs Attention" tile.

### Phase 4 — UI polish
Found that every `animate-in` / `slide-in-from-*` class in the app was a **no-op** — the
`tailwindcss-animate` plugin had never been installed. The dashboard slide-over was rebuilt on real
`transition-transform` / `translate-x` with deferred unmount so the close animation actually plays.

### Phase 5 — Dataset research and the DE-SynPUF finding
Triggered by "we need a well-trained model, and for that a good dataset."

**CMS DE-SynPUF was ruled out.** CMS's own Data User's Guide states that its disclosure treatment
destroys correlations between variables. A supervised model only learns `P(readmit | features)`; if
those relationships were synthesised away, the model trains, reports an AUC, and means nothing.
`docs/cms/cms_migration_guide.md` and `NewData.md` (the full 8-file DE-SynPUF schema investigation and
feature-mapping work) remain in the repo as the record of that evaluation.

Two live defects were found in the then-production model while checking artefacts:

| Defect | Detail |
|---|---|
| Model card overstated precision | `data/diabetic/model_card.json` advertises `precision: 0.72`; actual positive-class precision was **0.49** (6,212 FP vs. 6,077 TP) — and it was being served to clinicians via `/api/model/metrics`. |
| Risk scores inflated ≈3.5× | Trained on a rebalanced set (~39.6% positives) while the true `<30`-day rate in `diabetic_data.csv` is **11.2%**. This also corrupted the ROI panel, which reads `risk_score` as a probability. |

### Phase 6 — MIMIC-IV feasibility, measured
`scripts/mimic_feasibility.py` (244 lines), run against the demo and then the full extract:
- **Phase 1 (discharge risk): GO** — the label constructs cleanly.
- **Phase 2 (weekly monitoring): NO GO from MIMIC** — `omr` is the only outpatient table and holds
  only Weight, BP, BMI and Height, recorded opportunistically. On the full extract, median **22 days**
  to the first post-discharge observation and only **16.9%** of discharges have observations in two
  distinct weeks of the 30-day window — against the notebook's own 25% viability line. Not a
  sample-size problem — the cadence does not exist.
- **New blocker found:** MIMIC diagnoses split **61.8 / 38.2** ICD-9 / ICD-10, but the baseline's `_CCI_PATTERNS`
  were ICD-9 only, so half the cohort would have silently scored **CCI = 0**.

### Phase 7 — Training notebooks built around the real constraint
`labevents.csv` is **18.4 GB** and a Kaggle CPU session has **32 GB RAM**. Tables over ~500 MB are
streamed in chunks, filtered to the cohort, reduced to per-admission aggregates and discarded;
`emar` (8.7 GB), `poe` (5.1 GB) and `pharmacy` (4 GB) are never touched at all.

Correctness guards built in: **`GroupShuffleSplit` on `subject_id`** (patients average ~2 admissions —
a row-level split leaks the same person across folds), a three-way train/calibrate/test split, a
`calib_ratio` metric that surfaces exactly the 3.5× inflation bug, and a dual ICD-9 + ICD-10 Charlson
mapping (Quan et al. 2005). Four further bugs were caught by *executing* cells rather than reading
them: variable shadowing, `pd.concat([])` on empty chunk results, `object` vs `int64` join keys, and
duplicate `subject_id` producing `_x`/`_y` suffixes.

### Phase 8 — Trained results and the transfer test
Trained on full MIMIC-IV: 296,760 index stays, 148,669 patients, 19.63% readmission rate.

| Evaluation | AUC-ROC | AUC-PR | Calib. ratio |
|---|---|---|---|
| MIMIC test fold, all 94 features | **0.723** | **0.392** | **1.01** |
| MIMIC test fold, UCI features only | 0.662 | 0.300 | 0.80 |
| UCI Diabetes, transferred as-is | 0.544 | 0.125 | 1.09 |
| UCI Diabetes, after recalibration | 0.545 | 0.125 | 1.00 |
| Control: retrained on the same 39 features | 0.670 | 0.217 | — |

- On MIMIC the model is credible **and calibrated** (ratio 1.01). The logistic baseline in the same
  run scored 2.37 — a live reproduction of the `class_weight="balanced"` inflation bug.
- **It does not transfer.** Missing features cost only −0.061; domain and label shift cost −0.118.
  Recalibration does not help, so this is broken *discrimination*, not miscalibration.
- The control retrain (0.670 on the same 39 mapped features) proves the feature mapping is sound and
  the transfer failure is genuine.
- **Conclusion: the pipeline is the transferable asset, not the weights.**

Script: `scripts/test_mimic_model_on_diabetes.py` (299 lines); results in `data/mimic/transfer_test_results.json`.

### Phase 9 — Full switch to MIMIC
Decision: full replacement of the UCI scoring path.

*The blocker.* The MIMIC model is `HistGradientBoostingClassifier` inside `CalibratedClassifierCV` —
no `.tree_`, no `.decision_path`, so the baseline's interpretability engine
(`models/driver_extractor.py`, `_extract_top3_drivers`) **could not run on it at all**.

- `models/mimic_drivers.py` (398 lines) — SHAP-based per-patient drivers against the inner HGB, plus
  clinician-facing labels for all 94 features, emitted in the `"Label: value (explanation)"` format
  the dashboard already parses.
- `api/mimic_scoring.py` (243 lines) — 94-feature builder, banding, scoring, driver extraction.
- `api/main.py` — **−292 lines**: UCI model loader, `_CCI_PATTERNS`, `_build_feature_vector`,
  `_LABEL_MAP_INFER`, `_extract_top3_drivers` and `_get_risk_band` all removed.
- `GET /api/manual-entry/schema` — field list and valid category values, so the form can be driven
  from the model instead of hardcoded.
- `scripts/load_mimic_to_mongo.py` (347 lines) — ETL into the existing dashboard schema.

Verified rather than assumed:
- The model pickles under scikit-learn 1.6.1 (Kaggle) while the venv runs 1.7.2. A minimal
  `_RemainderColsList` shim makes it load, and predictions are **bitwise identical** to a genuine
  1.6.1 environment across 3,000 rows — so no venv downgrade was needed.
- SHAP on HGB is **approximate**: ~8% additivity error against the model margin, top-3 driver
  agreement 2.45/3 versus interventional SHAP. Documented in the module — drivers are indicative,
  not exact Shapley values. Still a large improvement on "cannot compute at all".
- Two bugs caught by testing: the NaN guard used `isinstance(x, float)`, which misses numpy scalar
  NaNs; and the driver parser split on the *first* `" ("`, truncating any label containing brackets.

`ManualPatientInput` is now all-optional by design — HGB learned a split direction for missing values
during training, so a blank field scores as genuinely unknown rather than as zero.

**Loaded to MongoDB:** 2,000 patients / 3,869 admissions, **derived data only** — score, band, three
driver strings, a rebuilt date. No labs, ICD codes, notes or real MIMIC timestamps leave the machine.
Dates are reconstructed from `n_prior_adm` + `days_since_prev` + `los_days`, anchored so each patient's
last discharge lands today: within-patient intervals are exact, only the absolute epoch moves. This
also neutralises MIMIC's 2110–2201 de-identification shift, which would otherwise look broken in the UI.

### Phase 10 — Diagnoses, weekly simulation, UI consistency (2026-09-01 commit, post-log)
- `models/mimic_diagnoses.py` (141 lines) — attaches the principal ICD diagnosis (`seq_num == 1`) plus
  three secondaries to each scored row, so a risk score sits next to a clinical reason. It also
  documents a join blocker honestly: `phase1_matrix.parquet` does not carry `hadm_id`, and recovering
  the key by matching the 48 lab columns was **measured and rejected** — 32% of rows match more than
  one `hadm_id`, which would label patients with another patient's diagnosis. The fix is one line in
  the Phase 1 notebook's final cell.
- `scripts/simulate_weekly_monitoring.py` (426 lines) — a stand-in for the Phase 2 cadence MIMIC
  cannot supply. Simulated: the weekly lab panel and which patients deteriorate. Real: the model doing
  the scoring, the SHAP attribution, and the discharge-time feature vector. Deterioration is drawn
  from the model's own calibrated probability — which is exactly what calibration licenses — rather
  than from the censored `readmit_30d` label of a last admission. Every document written carries
  `source="simulated"`, and the module states plainly that this is not a validated post-discharge
  monitor.
- Model artefacts retrained and re-exported (`phase1_diagnoses.parquet`, `phase1_timeline.parquet`,
  `mimic_feature_spec.json`), plus worklist / trend-panel / badge consistency fixes.

---

## 4. Quantified delta

**New backend modules — 1,119 lines**

| File | Lines |
|---|---|
| `models/mimic_drivers.py` | 398 |
| `api/gemini_insights.py` | 337 |
| `api/mimic_scoring.py` | 243 |
| `models/mimic_diagnoses.py` | 141 |

**New scripts — 1,316 lines**

| File | Lines |
|---|---|
| `scripts/simulate_weekly_monitoring.py` | 426 |
| `scripts/load_mimic_to_mongo.py` | 347 |
| `scripts/test_mimic_model_on_diabetes.py` | 299 |
| `scripts/mimic_feasibility.py` | 244 |

**Frontend — 4 new files (534 lines), 9 modified**

| File | Change |
|---|---|
| `components/dashboard/WeeklyTrendPanel.jsx` | new, 322 |
| `components/shared/AiInsightsPanel.jsx` | new, 124 |
| `components/shared/TrendStatusBadge.jsx` | new, 67 |
| `pages/PatientTrend.jsx` | new, 39 |
| `components/shared/BulletList.jsx` | new, 21 |
| `api/mock.js` | 146 → 467 |
| `components/dashboard/PatientWorklist.jsx` | 271 → 336 |
| `components/dashboard/PatientDetailPanel.jsx` | 138 → 183 |
| `components/dashboard/SummaryPanel.jsx` | 122 → 160 |
| `components/dashboard/FilterBar.jsx` | 88 → 119 |

**API surface:** 20 → 24 endpoints. New: `GET /api/patients/{id}/trend`, `POST /api/ai-insights`,
`POST /api/week-narrative`, `GET /api/manual-entry/schema`.

**New analysis documents:** `donesofar.md`, `NewData.md` (DE-SynPUF schema investigation),
`lateFusionApproach.md`, `WhatToDoWhenModelPlateaus.md`, `docs/cms/cms_migration_guide.md`,
`docs/mimic/mimic_feature_spec.json`, `docs/mimic/band_thresholds_mimic.json`.

**New notebooks — 6:** `notebooks/cms/cms_phase1_phase2_feature_engineering.ipynb`,
`notebooks/cms/phase1_readmission_model.ipynb`, `data/mimic/mimic_eda_phase1_phase2.ipynb`,
`phase1_discharge_risk_mimic.ipynb`, `phase2_postdischarge_trend_mimic.ipynb`, `phase-1-solved.ipynb`.

---

## 5. Model comparison

| | Baseline — UCI DecisionTree | Current — MIMIC HGB |
|---|---|---|
| Dataset | UCI Diabetes 130 US hospitals, 101,766 encounters | MIMIC-IV `hosp`, 296,760 index stays / 148,669 patients |
| Population | Diabetic inpatients, single encounter | All-cause adult inpatient, longitudinal |
| Features | ~25–34 | **94** |
| Algorithm | DecisionTree (balanced + importance weighting) | HistGradientBoosting + isotonic calibration |
| Prevalence | 11.2% true (trained at ~39.6% rebalanced) | 19.63%, trained as-is |
| AUC-ROC | 0.706 | **0.7229** |
| AUC-PR | not reported | **0.3921** |
| Brier | not reported | 0.1404 |
| Calibration ratio | ≈3.5× inflated | **1.01** |
| Precision (readmit) | 0.49 actual vs. **0.72 advertised** | 0.342 at 0.601 recall |
| Split discipline | Row-level | **GroupShuffleSplit on `subject_id`** |
| Explainability | Decision-path walker | SHAP on inner HGB (~8% additivity error, documented) |
| Band thresholds | `band_thresholds_balanced_importance.json` | `band_thresholds_mimic.json` — high 22.43, low 16.18 |
| Registry | MLflow (`./mlruns`) | `phase1_model.joblib` + `model_card_phase1.json` |

The AUC gain is modest and that is the honest expectation — a 2025 meta-analysis puts the pooled
readmission AUC at **0.71**, so the baseline's ~0.70 was already at the literature norm. What changed
is not the headline number but its trustworthiness: honest calibration, a patient-level split, an
all-cause population, and a precision figure that matches reality.

---

## 6. Decisions and negative results

The most durable output of this phase is a set of options closed with evidence, each one saving the
project from a wrong turn:

| Question | Verdict | Evidence |
|---|---|---|
| Train on CMS DE-SynPUF? | **No** | CMS's own Data User's Guide: disclosure treatment destroys inter-variable correlations. |
| Get weekly post-discharge monitoring from MIMIC? | **No** | Only 16.9% of discharges have two distinct observation weeks in 30 days, against a 25% viability line; and the 71.6% who do return readmit at 22.0% vs 13.8%, so the observed subgroup is self-selected. |
| Transfer the MIMIC model to UCI patients? | **No** | AUC 0.544; decomposed to −0.061 missing features, −0.118 domain/label shift; control retrain at 0.670 proves the mapping is sound. |
| Recover `hadm_id` by matching lab columns? | **No** | 32% of rows match more than one admission. |
| Downgrade the venv to scikit-learn 1.6.1? | **Not needed** | A shim loads the model and predictions are bitwise identical across 3,000 rows. |
| How to combine claims and clinical models later? | **Late fusion** | `lateFusionApproach.md` — two calibrated experts, a fusion layer, and calibration as the hard prerequisite. |
| What to do when the model plateaus? | **Fix the system** | `WhatToDoWhenModelPlateaus.md` — rank don't classify, deterministic guardrails, asymmetric risk, data-centric pivot. |

---

## 7. What is still open

Verified against the working tree today, not just copied from the log.

1. ~~**Manual Entry frontend still collects UCI fields.**~~ **Closed 2026-09-01.** The form was rebuilt
   on the 94-feature MIMIC contract and is now driven by `GET /api/manual-entry/schema`; blank fields
   send `null` rather than `0`. See `donesofar.md` Phase 11.
2. **The old batch pipeline is inconsistent with the new API.** `pipeline/batch_flow.py:30` and
   `outputs/export_worklist.py:22` still import `models.driver_extractor` and score with the UCI
   DecisionTree `readmission-dt-balanced-importance` from `mlruns`. Running either would write
   UCI-scored patients with incompatible driver labels into the same `patient_worklist` the MIMIC API
   reads.
3. **`hadm_id` is not saved in `phase1_matrix.parquet`**, so `models/mimic_diagnoses.py` cannot attach
   diagnoses to the current matrix. One-line fix documented in the module's docstring; needs a notebook
   re-run.
4. ~~**"Weekly Risk Trend" needs relabelling.**~~ **Not actually open** — `donesofar.md`'s list was
   stale here. `WeeklyTrendPanel` already switches every label between weekly and per-admission
   wording based on the response's `kind`, as of the 2026-09-01 commit.
5. **`DriverCard.jsx` multiplies any decimal driver value by 100 and appends `%`** — an albumin of
   2.6 g/dL renders as `260%`. `formatValue` at [DriverCard.jsx:33](frontend/src/components/shared/DriverCard.jsx:33)
   assumes a decimal is a 0–1 probability, which was true of UCI drivers and is false of every MIMIC one.
6. **Phase 2 weekly monitoring remains unsupported by real data.** The simulator is an explicit
   stand-in; a real cadence needs All of Us wearables or Preventra's own telemetry once live.
7. **No authentication or RBAC.** `ROADMAP.md` §1 is still open — the API is gated by one optional
   shared `X-API-Key` and nothing else. There are no user accounts, no roles, and no record of who
   read or changed which patient. The key is also compiled into the public frontend bundle.
8. **Atlas IP allowlist** must include the current IP; a mismatch surfaces as a TLS handshake failure,
   not an auth error.

---

## 8. Summary

The Denovonet baseline delivered a complete product on a dataset that could not support it: a single
flat file of diabetic encounters, a model whose scores were inflated ~3.5×, and a model card that
advertised a precision it did not have.

The current project kept the product and replaced its foundation. Two candidate datasets were
evaluated and one was rejected on documented grounds; the surviving one was trained at full scale with
patient-level splits and honest calibration; the interpretability engine was rebuilt from scratch
because the new model architecture made the old one impossible to run; and the transfer question was
settled with a measurement rather than an assumption. Along the way, the two production defects the
baseline was shipping were found and fixed.

The headline AUC moved 0.706 → 0.723. The real change is that the number now means what it says.
