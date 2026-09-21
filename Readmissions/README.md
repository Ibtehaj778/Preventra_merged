# Preventra

**A 30-day hospital readmission risk system for care coordinators.** It scores every patient at
discharge, explains each score in clinical language, re-scores them weekly for a month, and says
whether an intervention is worth its cost.

Built on **MIMIC-IV** — real, de-identified hospital records from Beth Israel Deaconess. A
calibrated gradient-boosting model over 94 features, a FastAPI + MongoDB backend, and a React
dashboard.

| | |
|---|---|
| Discharge model | `HistGradientBoostingClassifier`, isotonic calibration, **AUC-ROC 0.7229** |
| Cohort in the dashboard | 4,000 patients · 20,000 weekly monitoring records |
| Clinical grouping | 11 condition groups derived from ICD codes |
| Stack | Python 3.10 · FastAPI · MongoDB Atlas · React 19 · Vite · Tailwind v4 |

---

## Table of contents

1. [Quick start](#quick-start)
2. [How it works, end to end](#how-it-works-end-to-end)
3. [Repository map](#repository-map)
4. [The data, and how we got here](#the-data-and-how-we-got-here)
5. [The discharge model](#the-discharge-model)
6. [From model to dashboard](#from-model-to-dashboard)
7. [Weekly monitoring](#weekly-monitoring)
8. [Clinical grouping from ICD codes](#clinical-grouping-from-icd-codes)
9. [Risk bands](#risk-bands)
10. [The cost model](#the-cost-model)
11. [The API](#the-api)
12. [The dashboard](#the-dashboard)
13. [Access control](#access-control)
14. [Configuration](#configuration)
15. [Runbook](#runbook)
16. [Documentation index](#documentation-index)
17. [Known limitations](#known-limitations)

---

## Quick start

**Prerequisites:** Python 3.10+, Node 18+, and a MongoDB connection string.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

```bash
npm --prefix frontend install
```

Create `.env` in the repository root:

```
MONGO_URI=mongodb+srv://user:password@cluster.mongodb.net/
API_KEY=<any random string>
GEMINI_API_KEY=<optional, for the chatbot and narrative endpoints>
```

And `frontend/.env`:

```
VITE_API_BASE_URL=http://localhost:8000
VITE_API_KEY=<same value as API_KEY>
```

Run the two processes:

```bash
.venv/bin/uvicorn api.main:app --reload --port 8000
```

```bash
npm --prefix frontend run dev
```

The dashboard is at `http://localhost:5173`. It reads data already loaded in MongoDB — see
[Runbook](#runbook) if the database is empty.

---

## How it works, end to end

There are two distinct halves, and keeping them separate is the central design decision.

```
     RAW MIMIC-IV TABLES                          ┌─── week 0: the real model ───┐
     admissions · patients · diagnoses_icd        │  94 features, calibrated,    │
     labevents (18.4 GB) · prescriptions          │  explained with real SHAP    │
     drgcodes · procedures_icd · omr              └──────────────────────────────┘
              │                                                  │
              │ phase1_discharge_risk_mimic.ipynb                │
              ▼                                                  ▼
     ┌────────────────────┐                       ┌──────────────────────────────┐
     │  94-feature matrix │──── train ──────────▶ │  weeks 1-4: a rule layer     │
     │  296,760 of 545,497│                       │  over weekly observations,   │
     └────────────────────┘                       │  weighted per condition      │
              │                                   └──────────────────────────────┘
              │ scripts/load_mimic_to_mongo.py                   │
              ▼                                                  │
     ┌───────────────────────────────────────────────────────────▼──────────────┐
     │                              MongoDB                                     │
     │  patient_worklist · weekly_monitoring · risk_registry                    │
     │  executive_summary · alerts · care_actions                               │
     └──────────────────────────────────┬───────────────────────────────────────┘
                                        │ FastAPI (api/main.py, 32 endpoints)
                                        ▼
                            React dashboard (frontend/)
```

**Week 0 is the trained model alone.** It reads 94 discharge-time features and produces a
calibrated probability, explained with genuine SHAP attribution.

**Weeks 1–4 are both.** Every weekly score is literally:

```
score  =  the model's calibrated discharge probability      ← the trained model
        + this week's rule adjustment                       ← the rule layer
        + a carry term from last week's adjustment          ← the rule layer
```

The model's output is not replaced or re-run — it is passed in unchanged as the anchor of every
week, so the *level* a patient sits at remains the trained model's judgement of them. The rules
supply only the *movement* around it.

**Why split it this way.** The model was trained on discharge-time features and contains no
vitals, no adherence and no pharmacy feature, so it cannot react to what happens at home — it has
nothing to react with. The rule layer covers exactly that gap: it is bounded (the worst possible
week adds about 27 points, the best removes about 6), explicit, and it carries an unresolved
problem forward so it compounds instead of resetting every Monday.

This is the standard shape for a monitoring programme that does not yet have post-discharge
outcome data of its own: a transparent clinical guardrail wrapped around a calibrated statistical
baseline, with each half doing what only it can. The two contributions are labelled separately
everywhere they surface, so nobody reads a rule adjustment as a model prediction.

---

## Repository map

| Path | What lives there |
|---|---|
| `api/` | FastAPI application — 26 endpoints, scoring, ROI, Gemini integrations |
| `models/` | Feature engineering, ICD grouping, monitoring rules, SHAP driver extraction, training scripts |
| `scripts/` | Operational scripts: load, simulate, refresh, re-band, backfill |
| `frontend/` | React 19 + Vite + Tailwind v4 dashboard |
| `features/` | Cleaning, labelling and Charlson index for the original UCI pipeline |
| `pipeline/` | `batch_flow.py` — the legacy end-to-end batch scorer for the UCI model |
| `notebooks/` | One folder per phase — `diabetic/`, `cms/`, `mimic/` |
| `data/` | One folder per phase, plus `reference/` and `runtime/` — see `data/README.md` |
| `docs/` | One folder per phase, plus cross-phase documents — see `docs/README.md` |
| `mlruns/` | MLflow run history from the UCI phase |

Everything is filed by the dataset phase it belongs to, so the three eras of this project
(`diabetic` → `cms` → `mimic`) stay separable:

```
data/        diabetic/  cms/  mimic/  reference/  runtime/
docs/        diabetic/  cms/  mimic/  deliverables/  + the cross-phase documents
notebooks/   diabetic/  cms/  mimic/
```

Two paths the application reads at runtime, worth knowing before moving anything:
`data/mimic/model/results/phase1_model.joblib` (the served model) and
`docs/mimic/band_thresholds_mimic.json` (the live risk bands).

### The modules that matter most

| File | Responsibility |
|---|---|
| `api/main.py` | Every HTTP route. Worklist filtering/sorting/paging, patient detail, weekly trend, manual scoring, alerts, care coordination |
| `api/mimic_scoring.py` | Loads the model bundle, scores a feature frame, assigns a risk band |
| `api/roi_model.py` | Itemised cost model and the break-even decision |
| `models/mimic_drivers.py` | SHAP over the calibrated model → three clinician-readable reasons per patient |
| `models/monitoring_rules.py` | The weekly rule layer: 19 signal rules, per-group weights, phrasing and score normalisation |
| `models/icd_groups.py` | ICD codes → one of 11 clinical groups, with the evidence it matched on |
| `models/discharge_baseline.py` | Per-patient reference points (dry weight, usual saturation, usual walking distance, pain) |
| `models/mimic_diagnoses.py` | Builds the per-admission diagnosis index from `diagnoses_icd` + `d_icd_diagnoses` |

---

## The data, and how we got here

Three datasets, in order. The full account with every figure sourced is in
[`docs/project_timeline.md`](docs/project_timeline.md).

### Stage 0 — UCI Diabetes 130-US Hospitals

101,766 encounters, diabetic inpatients only, 34 features. Four approaches were trained and
validated against a pass mark of AUC-ROC 0.65:

| Approach | AUC-ROC | Verdict |
|---|---:|---|
| Decision tree, plain | 0.6463 | did not pass |
| Decision tree, balanced | 0.6893 | passed |
| **Decision tree, balanced + importance** | **0.7063** | **shipped** |
| XGBoost | 0.6702 | passed |

It proved the pipeline end to end and set the yardstick every later model was measured against.
It could not be the product: one condition, where the hospital needed all-cause adult inpatients.

### Stage 1 — CMS DE-SynPUF

1,332,755 encounters × 58 features, 10.02% 30-day readmission, 5-fold validation grouped by
patient, **ROC-AUC 0.6893**. Not adopted, for reasons the metric cannot show:

1. **It is synthetic.** DE-SynPUF preserves each variable's distribution while deliberately
   weakening the relationships *between* them. CMS publishes it for building and testing
   software, not for drawing conclusions about real beneficiaries.
2. **No clinical measurements.** All 58 columns are administrative — what was billed, paid and
   claimed. Zero laboratory results, zero vital signs.
3. **Unusable explanations.** The dashboard names three reasons per patient. From claims those
   read *"prior outpatient payment sum"*, which held 54% of the prototype's importance and which
   no coordinator can act on.
4. **ICD-9 only**, freezing the disease coding in an edition the US stopped using in 2015.
5. **Medicare-only, and claims settle weeks late**, so weekly monitoring is structurally
   impossible on it.

### Stage 2–3 — MIMIC-IV

The `hosp` module, credentialed access.

| | |
|---|---:|
| Admissions | 545,497 |
| Patients | 223,291 |
| Diagnosis records | 6,364,488 |
| Distinct ICD codes | 28,562 across all 20 chapters |
| ICD-9 / ICD-10 split | 45.7% / 54.3% |
| Diagnoses per stay | 11.7 on average |

That is the full dataset. The model is trained on a subset of it — see
[The discharge model](#the-discharge-model).

The finding that shaped everything after it: **patients do not have one disease.** Only 1.2% of
stays involve a single condition; 96.1% span two or more body-system chapters, averaging 6.1.
Readmission climbs from 8.5% for a single-diagnosis stay to 28.2% for twenty or more.

---

## The discharge model

**Where it lives:** `data/mimic/phase1_discharge_risk_mimic.ipynb`, with the trained
bundle in `data/mimic/model/results/phase1_model.joblib`.

| | |
|---|---|
| Source | all of MIMIC-IV `hosp` — **545,497 admissions, 223,291 patients** |
| Modelling cohort | **296,760 stays, 148,669 patients** — the subset below |
| Excluded | in-hospital death, hospice discharge, observation stays — a 30-day readmission cannot be measured on a patient who had no chance of one |
| Label | 30-day unplanned readmission — elective returns excluded |
| Prevalence | 19.63% |
| Features | 94 |
| Model | `HistGradientBoostingClassifier` + `CalibratedClassifierCV` (isotonic) |
| Split | `GroupShuffleSplit` by `subject_id` — no patient in two folds |

Those two population figures appear throughout the project and are easy to confuse. **545,497 /
223,291 is the whole dataset**; **296,760 / 148,669 is what remains after the exclusions above** —
about 46% of stays drop out, most of them observation stays. Cohort-level statistics (readmission
rates, comorbidity burden) are computed on the modelling cohort; dataset-level statistics
(diagnosis counts, code frequencies) on all of it.

**Measured on a 59,835-admission test fold containing 11,743 real readmissions:**

| Metric | Value |
|---|---:|
| AUC-ROC | **0.7229** |
| AUC-PR | 0.3921 |
| Brier score | 0.1404 |
| Calibration ratio | 1.01 |

AUC-ROC is a mark out of 1 for how well the model sorts patients riskiest-first: 0.50 is random
guessing, 1.00 is perfect. Calibration is the line that mattered most downstream — a score of 40%
means a real 40% chance, which is what allows a cost model to be multiplied by it.

### The 94 features

**48 laboratory features** — 12 analytes (albumin, bicarbonate, BUN, creatinine, glucose, HbA1c,
haemoglobin, INR, platelets, potassium, sodium, white cell count) × `_last` / `_min` / `_max`,
plus an abnormal-result count for each.

**46 others** — demographics; prior-admission history; the 17 Charlson comorbidity flags plus the
weighted score; length of stay, diagnosis and procedure counts, DRG severity and mortality; drug
order counts and five medication-class flags (insulin, anticoagulant, opioid, diuretic,
antipsychotic); ED usage; discharge disposition.

### Building it

Labs and prescriptions are streamed, not loaded: `labevents.csv` is 18.4 GB. The pattern is read
a chunk with `usecols` only, drop out-of-cohort rows immediately, reduce to per-admission
aggregates, free the chunk, and re-compact partial aggregates periodically so the accumulator
cannot grow unbounded.

Two correctness guards are worth knowing:

- **The next admission is computed on the full sequence *before* exclusions are applied.**
  Filtering first would lose a readmission that happened to follow an excluded stay.
- **Comorbidity regexes run across both ICD editions.** The same code string is valid in ICD-9
  and ICD-10 and means different things, so every lookup uses the `(code, version)` pair.

---

## From model to dashboard

Four scripts, run in order. Each is idempotent.

### 1. `scripts/load_mimic_to_mongo.py`

Scores the cohort, runs SHAP for the top three drivers per patient, translates each into a
clinician-readable sentence, attaches diagnoses, classifies the clinical group, and writes
`patient_worklist`, `risk_registry` and `executive_summary`.

```bash
.venv/bin/python scripts/load_mimic_to_mongo.py --limit 4000
```

`--preserve-existing` keeps already-loaded patients and tops the cohort up rather than replacing
it.

### 2. `scripts/simulate_weekly_monitoring.py`

Generates the 30-day monitoring window. Week 0 is the real model with real SHAP; weeks 1–4 apply
the rule layer.

```bash
.venv/bin/python scripts/simulate_weekly_monitoring.py --weeks 4
```

**Data provenance.** MIMIC ends at the hospital door and holds no post-discharge measurements of
any kind. The weekly observations are therefore **augmented** — generated to exercise the
monitoring layer, with trajectories drawn from the model's own calibrated discharge probability
so the cohort reproduces the real event rate and puts deterioration where the model expects it.
Every document carries `source` and the interface labels it. Neither the document shape nor the
API changes when a real telemetry feed replaces it.

### 3. `scripts/backfill_group_membership.py`

Writes `clinical_groups` (every condition a patient has) alongside `clinical_group` (the single
plan they are monitored under), and builds the multikey index the condition filter runs on.

### 4. `scripts/refresh_worklist_summary.py`

Denormalises each patient's current score, band, trend, weeks tracked and primary driver onto
their worklist row, then builds 11 indexes.

This is the reason the worklist is fast. The endpoint used to read every worklist row, aggregate
the whole weekly collection, normalise the lot in Python and only then slice out the requested
page — **27 seconds** against Atlas at 2,000 patients, growing with the cohort. Filtering,
sorting and paging now happen in MongoDB against an index and latency no longer scales with
cohort size: **0.3–0.7 s** at 4,000.

### Collections

| Collection | Contents |
|---|---|
| `patient_worklist` | One row per patient per batch — score, band, drivers, diagnoses, clinical group, denormalised trend summary |
| `weekly_monitoring` | One document per patient per week — score, band, drivers, observations, data sources |
| `risk_registry` | Score history across batches |
| `executive_summary` | Band counts per batch, for the dashboard header |
| `alerts` | Raised when an update crosses a 15-point or band jump |
| `care_actions` | Coordinator assignments and notes |

---

## Weekly monitoring

A discharge score is one number on one day. The monitoring layer re-scores every seven days
across the 30-day window, so a patient deteriorating at home becomes visible before they return.

### What is monitored

Signals a real programme actually records, not a repeat lab panel:

| Signal | Range of effect |
|---|---:|
| Weight change since discharge | −1.0 … +7.0 |
| Medication adherence | −1.5 … +8.0 |
| Pharmacy refill collected | −0.8 … +5.0 |
| Follow-up appointment attended | −2.0 … +4.5 |
| Systolic blood pressure | −0.5 … +4.0 |
| Resting heart rate | 0 … +3.5 |
| Oxygen saturation | −0.5 … +5.0 |

Plus ten condition-specific signals used only for the groups they apply to: orthopnoea, ankle
swelling, walking distance, rescue-inhaler use, sputum change, temperature, wound appearance,
pain trend, antibiotic-course completion, and confusion.

**The weights are deliberately asymmetric** — the worst possible week adds about 27 points while
the best removes about 6. Deterioration is strong evidence of trouble; perfect adherence is only
weak evidence of safety, since a patient can take every pill and still decompensate.

### Personal reference points

`models/discharge_baseline.py` gives every patient their own baseline — dry weight, usual
saturation, usual walking distance, pain at discharge — so a reading is measured against *that
patient* rather than a population threshold. A 2 kg gain means something different in heart
failure than after a knee replacement.

Two rules invert or replace outright by group: weight **loss** is the risk signal in cancer, and
oxygen saturation is judged against the 88–92% target range in chronic lung disease rather than a
population floor.

### Score normalisation

A group with ten signals would out-score a group with seven simply for having more boxes to tick,
and the worklist sorts by score. Every group's contributions are scaled so the worst possible
week is +37.00 and the best −6.30 regardless of how many signals it has.

### Source attribution

Every weekly signal is attributed to a named feed — a home device hub, a medication app, a named
pharmacy, a clinic scheduling system, or the patient's own check-in. A pharmacy dispensing record
and a self-reported adherence figure are different kinds of claim and a coordinator should weigh
them differently. A week with no contact reads "carried forward" rather than naming feeds that
never reported.

---

## Clinical grouping from ICD codes

`models/icd_groups.py` maps a patient's diagnoses onto one of **11 groups**, using the same Quan
et al. (2005) Charlson crosswalk the model's own `charlson_score` is built from. Validated across
534,227 MIMIC admissions against a 19.02% base readmission rate:

| Group | Share of admissions | Readmitted | vs base |
|---|---:|---:|---:|
| Oncology | 8.4% | 27.7% | 1.46× |
| Heart failure | 15.1% | 23.6% | 1.24× |
| Mental health | 13.7% | 23.6% | 1.24× |
| Renal | 8.7% | 23.0% | 1.21× |
| Sepsis / infection | 1.6% | 22.9% | 1.20× |
| Respiratory | 11.6% | 19.2% | 1.01× |
| Diabetes | 8.7% | 16.9% | 0.89× |
| Surgical / injury | 8.4% | 14.4% | 0.76× |
| Cardiac, other | 5.3% | 13.8% | 0.72× |
| Neuro / stroke | 1.9% | 12.2% | 0.64× |
| General | 16.7% | 10.0% | 0.53× |

Respiratory sits at 1.01× — almost exactly the base rate. It still earns its own rules for a
different reason: the *signals* differ. An oxygen saturation of 91% is alarming after a pulmonary
embolism and near-normal in advanced COPD.

### One plan, many conditions

Two fields, deliberately:

- **`clinical_group`** — the single group a patient is *monitored under*. The highest-priority
  condition wins, because a patient can only be on one plan.
- **`clinical_groups`** — *every* condition they have. **21.8% of the cohort carries two or
  more.** The dashboard filters on this, so a diabetic heart-failure patient appears under both.

Filtering on the plan alone hid people: 288 patients are monitored for heart disease, but 547
have it.

### Negation and history guards

Substring matching cannot tell *"Personal history of malignant neoplasm of breast"* from active
cancer, nor *"Hypertensive heart disease **without** heart failure"* from the real thing. A
clause-scoped negation guard handles both — scoped so it cannot over-fire, since *"Diabetes
mellitus without mention of complication"* is still diabetes.

---

## Risk bands

Fixed, deliberately round thresholds:

| Band | Range | Patients |
|---|---|---:|
| **Low** | under 20% | 2,758 |
| **Medium** | 20% to under 40% | 582 |
| **High** | 40% and above | 660 |

They used to be derived from the score distribution — High at the model's 60%-recall operating
point (22.43%), Medium at the median predicted risk (16.51%). Statistically defensible and
unusable in practice: the numbers meant nothing on screen and moved every time the model was
retrained, so a patient could change band without anything about them changing.

Thresholds live in `docs/mimic/band_thresholds_mimic.json`. To change them, edit that file and run:

```bash
.venv/bin/python scripts/apply_risk_bands.py && .venv/bin/python scripts/refresh_worklist_summary.py
```

---

## The cost model

`api/roi_model.py` — ten named line items, not a lump sum:

| | |
|---|---:|
| Readmission episode (5 items) | $15,500 |
| Intervention delivery (5 items) | $350 |
| Intervention effectiveness | 25% |
| **Break-even risk** | **9.0%** |

The effectiveness factor is the difference between a 32× and an 8× return on the same patient,
and an earlier version omitted it silently.

**The model refuses below break-even.** Of the 2,000-patient cohort at the time, 867 patients
were being shown "expected savings" that the same arithmetic scores as money lost. They now read
*"no intervention case — routine monitoring"*. A patient whose risk is *falling* gets a step-down
recommendation rather than an intervention pitch.

---

## The API

`uvicorn api.main:app` — 26 endpoints. Optional `X-API-Key` header, enforced only when `API_KEY`
is set. There is no per-user sign-in; see [Access control](#access-control).

| Group | Endpoints |
|---|---|
| **Worklist** | `GET /api/patients` — server-side filter, sort and page; `GET /api/patient-groups` |
| **Patient** | `GET /api/patients/{id}`, `/trend`, `/edit`, `/care-actions` |
| **Scoring** | `POST /api/patients/predict`, `/worklist-add`, `/{id}/predict-update`, `/{id}/update` |
| **Narrative** | `POST /api/ai-insights`, `/week-narrative`, `/chatbot/query` |
| **Dashboard** | `GET /api/summary`, `/summary/history`, `/model/metrics`, `/analytics/top-drivers` |
| **Ops** | `GET /api/alerts`, `POST /api/alerts/{id}/acknowledge`, `/patients/{id}/assign`, `/notes`, `POST /api/cache/clear` |

### Worklist query parameters

```
GET /api/patients?group=heart_failure,diabetes&match=all&band=High&status=NeedsAttention
                 &q=albumin&sort=score-desc&page=1&limit=25
```

`group` accepts several condition keys; `match=any` is the union (default), `match=all` the
intersection. 413 patients have heart failure and 302 have diabetes; **24 have both**, and that
intersection was unreachable before.

Every filter runs against an index. A 60-second TTL cache sits in front of the count query;
`POST /api/cache/clear` drops it.

---

## The dashboard

React 19 · Vite · Tailwind v4 · Recharts · lucide-react.

| Screen | What it does |
|---|---|
| **Dashboard** | Executive summary, filter bar, ranked worklist, patient detail drawer |
| **Patient detail** | All diagnoses, three named drivers, four-week trend, ROI panel, care coordination |
| **Manual entry** | Score a patient from a form without running the pipeline |
| **Analytics** | Top drivers across the cohort, model metrics |
| **My Health** | Patient-facing view with a weekly self-report form |

### Notable components

- **`ConditionFilter.jsx`** — multi-select conditions with counts, chips, and an any/all toggle.
  Selections are URL parameters, so a filtered worklist is shareable.
- **`DiagnosisList.jsx`** — every diagnosis on the record, each tagged with the condition it
  evidences, so a stay admitted for liver disease shows exactly why it appears under heart
  failure.
- **`DriverCard.jsx`** — one clinical reason, its value, and what it means.
- **`WeeklyTrendPanel.jsx`** — the 30-day series with per-week reasoning and data sources.

Filter state, sort and page all live in the URL. All of it is applied server-side.

---

## Access control

**There is no sign-in and there are no user accounts.** The app opens directly on the care-team
dashboard, and every caller sees the same thing. The only gate in front of the data is the shared
`X-API-Key` header, checked when `API_KEY` is set.

That is a deployment control, not authentication. It distinguishes "this client was given the
key" from "this client was not"; it does not identify a person, does not scope anyone to a subset
of records, and cannot be revoked for one user without rotating it for all of them. The key also
ships inside the frontend bundle — every `VITE_`-prefixed variable is compiled into public
JavaScript — so anyone who can load the dashboard can read it.

Adequate for a single-tenant demo. Not adequate for real patient data, which needs per-user
authentication, an audit trail of who read which record, and server-side authorisation on every
endpoint. See [`docs/ROADMAP.md`](docs/ROADMAP.md).

---

## Configuration

### Backend — `.env`

| Variable | Required | Purpose |
|---|---|---|
| `MONGO_URI` | yes | MongoDB connection string |
| `MONGO_DB` | no | Database name, defaults to `neuroshield` |
| `API_KEY` | no | When set, every request needs an `X-API-Key` header |
| `GEMINI_API_KEY` | no | Chatbot, ROI narrative and week-narrative endpoints |
| `GEMINI_MODEL` | no | Model name override |
| `MIMIC_MODEL_PATH` | no | Override the model bundle location |

### Frontend — `frontend/.env`

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | Backend origin |
| `VITE_API_KEY` | Must match `API_KEY` |
| `VITE_USE_MOCK` | Serve fixtures instead of the API |

---

## Runbook

### Load a cohort from scratch

```bash
.venv/bin/python scripts/load_mimic_to_mongo.py --limit 4000
```

```bash
.venv/bin/python scripts/simulate_weekly_monitoring.py --weeks 4
```

```bash
.venv/bin/python scripts/backfill_group_membership.py
```

```bash
.venv/bin/python scripts/refresh_worklist_summary.py
```

### Add more patients without disturbing the existing ones

```bash
.venv/bin/python scripts/load_mimic_to_mongo.py --limit 6000 --preserve-existing
```

Then re-run the simulator, backfill and refresh.

### After changing the clinical grouping rules

```bash
.venv/bin/python scripts/backfill_group_membership.py && .venv/bin/python scripts/refresh_worklist_summary.py
```

If the change moves patients between groups, re-run the simulator too — weekly reasoning is
written in group-specific language, so a label change alone leaves stale narratives.

### After changing risk band thresholds

```bash
.venv/bin/python scripts/apply_risk_bands.py && .venv/bin/python scripts/refresh_worklist_summary.py
```

### The dashboard shows stale numbers

```bash
curl -X POST -H "X-API-Key: $API_KEY" localhost:8000/api/cache/clear
```

### Rebuild the client deck

```bash
.venv/bin/python scripts/build_client_deck.py
```

---

## Documentation index

| Document | Contents |
|---|---|
| [`docs/project_timeline.md`](docs/project_timeline.md) | Every stage in order, with each figure traced to its artefact |
| [`docs/mimic/icd_codes_explained.md`](docs/mimic/icd_codes_explained.md) | Plain-English guide to the disease coding, and the cohort demographics |
| [`docs/mimic/mimic_disease_landscape.md`](docs/mimic/mimic_disease_landscape.md) | The ICD analysis in depth |
| [`docs/mimic/icd_feature_engineering.md`](docs/mimic/icd_feature_engineering.md) | The ICD feature experiment and why it was rejected |
| [`docs/HANDOVER.md`](docs/HANDOVER.md) | File-by-file architecture reference |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Planned work |
| [`docs/diabetic/model_validation_report_*.md`](docs/) | The four UCI training tracks |
| [`donesofar.md`](donesofar.md) | Full change history |

### One experiment that returned a negative result

The question was whether ICD codes could be engineered into features that improve the discharge
model. Twenty-one new features were built and trained on the same split with the same
hyperparameters:

| Metric | Baseline | With ICD features | Difference |
|---|---:|---:|---:|
| AUC-ROC | 0.7229 | 0.7257 | +0.0027 |
| AUC-PR | 0.3921 | 0.3922 | +0.0001 |
| Readmissions in the top 500 by risk | **341** | 336 | **−5** |

The AUC gain is statistically significant and operationally invisible: at a fixed intervention
budget the enriched model catches slightly *fewer* readmissions. It was not adopted. The feature
predicted to be strongest, `principal_chapter`, ranked 110th of 115 and was effectively unused.

---

## Known limitations

**The diagnosis extract keeps only four diagnoses per stay.** Patients average 11.7 coded
diagnoses, but `N_SECONDARY = 3` in `models/mimic_diagnoses.py` keeps the principal plus three
secondaries — and only the principal keeps its ICD code. Consequences: 33% of patients default to
"General recovery" because their condition was coded fifth; secondary matching is keyword-based
on prose rather than exact on codes; and the UI has to state how many diagnoses it cannot show.
Re-exporting the parquet with `N_SECONDARY` raised and codes retained fixes all three — every
function downstream already handles a longer list.

**The weekly observations are augmented.** MIMIC has no post-discharge data. See
[Weekly monitoring](#weekly-monitoring).

**The pipeline upload endpoint is a simulation.** `POST /api/pipeline/upload` tracks a run in
memory; it does not invoke `pipeline/batch_flow.py`.

**CSV export is bandwidth-bound.** About 26 seconds for the full filtered set — the constraint is
the Atlas link (~110 KB/s for 2.7 MB), not the query.

**Legacy UCI rows remain.** 47 non-MIMIC patients from the original pipeline are still in
`patient_worklist` under an older batch date.

---

## Licence and data access

MIMIC-IV requires credentialed access through PhysioNet and a signed data use agreement. No MIMIC
data is committed to this repository beyond small samples under `data/mimic/`. CMS
DE-SynPUF is public. The UCI Diabetes dataset is public.
