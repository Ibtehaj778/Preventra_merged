# NeuroShield ("Preventra") — Project Handover Documentation

This document exists to hand this project off to a new owner/developer. It explains what the
product does, how the pieces fit together, and what every file in the repository is for. Read
top to bottom once, then use it as a reference.

> **Product naming note:** the git repo and internal code call this project **NeuroShield**.
> The client-facing product name (seen in the frontend UI, the sidebar brand mark, and the
> `docs/deliverables/` client documents) is **Preventra**. Same product, two names.

---

## 1. What this project is

Preventra is a clinical dashboard that predicts a diabetic patient's risk of **30-day hospital
readmission** and gives care teams a worklist of at-risk patients, an explanation of *why* each
patient is high-risk (their top "drivers"), and workflow tools to act on that risk (manual
score-checking, editing a patient's data and re-scoring, assigning a care coordinator, logging
care notes, and getting alerted when a patient's risk jumps).

It has three main parts:

1. **An offline ML pipeline** (`features/`, `models/`) that cleans a raw diabetic-patient
   dataset, engineers ~25 clinical features, trains a model to predict 30-day readmission, and
   validates/calibrates it into High/Medium/Low risk bands.
2. **A batch scoring + serving backend** (`pipeline/`, `outputs/`, `api/`) that runs the trained
   model over a batch of patients on a schedule (or on-demand for one patient), writes results to
   MongoDB, and exposes everything over a FastAPI HTTP API — including a natural-language chatbot
   over the patient data.
3. **A React dashboard** (`frontend/`) that clinicians and care coordinators use day-to-day.

### Tech stack

| Layer | Technology |
|---|---|
| ML / data science | pandas, scikit-learn, XGBoost, SHAP, matplotlib/seaborn |
| Experiment tracking / model registry | MLflow (local `./mlruns` store) |
| Batch orchestration | Prefect |
| Database | MongoDB (via `pymongo`) |
| Backend API | FastAPI + Uvicorn |
| Chatbot LLM | Google Gemini (`google-genai`), function-calling only — never free-text DB queries |
| Frontend | React 19 + Vite + React Router v7 + Tailwind CSS v4 + Recharts + lucide-react |
| Testing | pytest (+ `mongomock` for DB-free unit tests) |

---

## 2. Architecture at a glance

```
                     ┌─────────────────────────────────────────────┐
                     │              OFFLINE / DEV-TIME              │
                     │                                               │
  data/*.csv  ──────▶│  features/*.py  ──▶  models/train_*.py       │
 (raw dataset)        │  (clean, label,        (train + tune,        │
                     │   engineer, CCI)         log to MLflow)       │
                     │                              │                │
                     │                              ▼                │
                     │                     models/calibrate.py       │
                     │                  (risk-band thresholds,       │
                     │                   validation reports, docs/)  │
                     └─────────────────────────────────────────────┘
                                          │
                                          │  registered model (MLflow, ./mlruns)
                                          ▼
                     ┌─────────────────────────────────────────────┐
                     │                 RUNTIME / SERVING             │
                     │                                               │
  new CSV  ─────────▶│  pipeline/batch_flow.py  (Prefect flow)       │
 (data/input/)        │  outputs/export_worklist.py (CLI equivalent) │
                     │       │                                       │
                     │       ▼                                       │
                     │   MongoDB: patient_worklist, risk_registry,   │
                     │            executive_summary, alerts,         │
                     │            care_actions                       │
                     │       │                                       │
                     │       ▼                                       │
                     │   api/main.py  (FastAPI)  ◀── chatbot service │
                     │       │                        (Gemini, api/  │
                     │       │                         chatbot_*.py) │
                     └───────┼───────────────────────────────────────┘
                             │  HTTPS / JSON
                             ▼
                     frontend/  (React dashboard, "Preventra")
```

Two parallel paths reach MongoDB / the model:

- **Batch path** — a new discharge CSV lands in `data/input/`, `pipeline/batch_flow.py` (or
  the equivalent standalone scripts in `outputs/`) engineers features, scores every patient,
  extracts drivers, and writes the whole cohort into `patient_worklist` + an audit snapshot into
  `risk_registry`.
- **Manual path** — a clinician fills out the "Manual Entry" or "Update Patient" form in the
  frontend; `api/main.py` engineers features and scores **that one patient inline** (a duplicated,
  self-contained reimplementation of the feature/CCI/driver logic — see §7 "Known
  duplication/tech debt" below) so a single form submission doesn't require running the full
  batch pipeline.

---

## 3. Repository map

```
neuroshield/
├── api/            FastAPI backend (HTTP API, chatbot, manual scoring)
├── features/       Data cleaning + feature engineering library
├── models/         Model training, calibration, and interpretability code
├── outputs/        Standalone CLI scripts: batch scoring / summary / registry seeding
├── pipeline/        Prefect-orchestrated production batch flow
├── scripts/        One-off/manual dev scripts (not part of the app or test suite)
├── tests/          Pytest unit tests
├── docs/           Generated model reports, data dictionaries, client deliverables
├── frontend/       React dashboard ("Preventra")
├── data/           Datasets, pipeline input/output (gitignored — see §6)
├── mlruns/         Local MLflow model registry (gitignored — see §6)
├── ingestion/      Reserved for future data-ingestion scripts (currently empty)
├── conftest.py     Pytest sys.path bootstrap
├── requirements.txt Python dependencies
└── .env            Backend secrets (gitignored — see §6)
```

---

## 4. File-by-file reference

### 4.1 `api/` — FastAPI backend

| File | Purpose |
|---|---|
| `main.py` | The FastAPI app and single backend entrypoint (`uvicorn api.main:app`). Connects to MongoDB via `MONGO_URI` on import. Optional `X-API-Key` auth (only enforced if `API_KEY` is set). Route groups: **Patients** (worklist, single-patient detail + score history), **Chatbot** (`POST /api/chatbot/query`), **Summary** (executive summary + history), **Model metrics**, **Analytics** (top drivers), **Pipeline** (CSV upload + an in-memory/simulated run tracker — this endpoint does *not* actually invoke `pipeline/batch_flow.py`), **Manual patient scoring** (predict / save-to-worklist / update / re-predict-on-update — an inlined, self-contained copy of the feature-engineering + CCI + driver-extraction logic so one form submission can be scored without the full pipeline), **Alerts** (list/acknowledge, raised when an update crosses a 15-point or risk-band jump), and **Care coordination** (assign coordinator, add notes, list care actions). |
| `chatbot_gemini.py` | Wraps the Gemini API for a strict two-stage design: Gemini either (1) selects one of 6 predefined query functions + arguments, or (2) phrases a natural-language answer from an already-computed JSON result. Gemini **never** writes MongoDB query syntax itself. Requires `GEMINI_API_KEY`. |
| `chatbot_queries.py` | The 6 predefined, parameterized MongoDB queries the chatbot is allowed to run (count by risk band, list by threshold, top-N risk patients, patient drivers, patient details, risk trend over time), each with its own input validation and sane limits. |
| `chatbot_service.py` | Orchestrates one chatbot turn end-to-end (select function → execute query → generate NL answer) and converts every failure mode into a safe user-facing string. Sole export: `answer_question(question, db)`. |
| `db_utils.py` | One shared helper: `get_latest_batch_date(db, collection_name)` — used everywhere a query needs to scope to "the current batch." |

### 4.2 `features/` — cleaning & feature engineering

| File | Purpose |
|---|---|
| `clean.py` | Loads raw `data/diabetic/diabetic_data.csv`, replaces the dataset's `"?"` null marker, drops unusable columns, imputes remaining nulls. First step of every training/pipeline run. |
| `cci.py` | Computes the Charlson Comorbidity Index from ICD-9 diagnosis codes (standard 1987 weight mapping). |
| `label.py` | Builds the binary readmission target in three variants: `add_label` (`<30`→1 only — original/strict), `add_balanced_label` (`<30` or `>30`→1), `add_balanced_label_with_importance` (same as balanced, plus a `sample_weight` column down-weighting `>30`-day cases to 0.5). **The `_with_importance` variant is what production uses.** |
| `engineer.py` | The bulk of feature engineering: admission/utilization counts, medication-change and high-risk-medication flags, complex-discharge and behavioral-health flags, a frailty proxy, and a no-show proxy (including `add_probabilistic_no_show`, which trains a small `LogisticRegression` from `data/reference/noshow.csv` at runtime — falls back to all-zeros if that file is missing). `run_feature_pipeline(df)` runs every step in order. |
| `build_features.py` | CLI orchestrator for the original (unbalanced-label) pipeline: clean → label → CCI → engineer → validate (row count, null count, positive-rate gate) → save `data/diabetic/features.csv`. |
| `eda.py` | Standalone diagnostic script — profiles `data/diabetic/features.csv` (class balance, distributions, missingness, correlation) and writes `docs/eda_summary.md`. Not imported by anything else. |

### 4.3 `models/` — training, calibration, interpretability

| File | Purpose |
|---|---|
| `train.py` | Original ("Week 3") baseline: unbalanced label, temporal 80/20 split, `DecisionTreeClassifier` + `GridSearchCV` tuning, logs `readmission-dt-baseline`/`-tuned` to MLflow. **Superseded — not used in production.** |
| `train_balanced.py` | Same shape as `train.py` but with the balanced label (both `<30`/`>30` = positive, unweighted). Logs `readmission-dt-balanced-baseline`/`-tuned`. **Superseded.** |
| `train_balanced_importance.py` | **The production training script.** Uses the balanced label *with* `sample_weight`. Trains and tunes both a `DecisionTreeClassifier` and an `XGBClassifier`. Registers `readmission-dt-balanced-importance` (the model actually served — see §5) and `readmission-xgb-balanced-importance` to MLflow. |
| `train_xgboost.py` | Experimental, explicitly-labeled XGBoost-only track on the original (unbalanced) label. Not referenced by the batch pipeline or API. |
| `calibrate.py` | Run after training: derives High/Medium/Low band thresholds from a scored test set, computes precision/recall/AUC at the high-risk threshold, plots calibration + ROC curves, and writes the corresponding `docs/diabetic/model_validation_report*.md` + `docs/band_thresholds*.json`. **`band_thresholds*.json` is what both `pipeline/batch_flow.py` and `api/main.py` read at runtime to turn a score into a band.** |
| `driver_extractor.py` | Decision-path interpretability engine for the (default, non-XGBoost) model: walks the fitted decision tree for one patient, depth-weights each split so patient-specific splits outrank shared root-level ones, and formats the top 3 into plain-English labels via a large `LABEL_MAP`. `extract_drivers_for_batch(...)` is what the batch pipeline calls. Also exports `load_model(...)` (tries the MLflow tracking server, falls back to local `./mlruns`). |
| `shap_utils.py` | SHAP-based driver extraction, used only when the active model name contains `"xgb"`. |

### 4.4 `pipeline/` — production batch orchestration

| File | Purpose |
|---|---|
| `batch_flow.py` | The production Prefect flow (`run_batch_pipeline`, default model `readmission-dt-balanced-importance`). Seven tasks: find the newest CSV in `data/input/` → engineer features → load the MLflow model → score every patient → assign risk bands → extract top-3 drivers (SHAP if XGBoost, decision-path otherwise) → write `patient_worklist` + week-over-week `executive_summary` → append an immutable snapshot to `risk_registry`. Run directly with `python pipeline/batch_flow.py`. |

### 4.5 `outputs/` — standalone CLI equivalents

These three scripts are a manual/scriptable alternative to `pipeline/batch_flow.py` — useful for backfills or one-off runs without Prefect.

| File | Purpose |
|---|---|
| `export_worklist.py` | Runs the full clean → engineer → score → band → drivers path from a raw CSV straight into `patient_worklist` (functionally batch_flow's tasks 2–6, without the summary/registry writes). |
| `export_summary.py` | Reads an already-exported worklist CSV, computes band counts + week-over-week change, and upserts `executive_summary`. |
| `risk_registry.py` | "Seed" script — takes an already-scored worklist CSV plus a `--model-version` string and writes to all three collections (`patient_worklist`, `risk_registry`, `executive_summary`) at once. Used for initial data loads/backfills. |

### 4.6 `scripts/`

| File | Purpose |
|---|---|
| `verify_gemini_selection.py` | Manual sanity-check script (not part of the test suite) — sends 8 representative dashboard questions to the **real** Gemini API and prints which function+arguments it selected, to validate the chatbot's function-calling prompt design. Costs real API quota; run manually, not in CI. |

### 4.7 `tests/` and test infra

| File | Purpose |
|---|---|
| `conftest.py` (root) | 7-line pytest bootstrap — puts the project root on `sys.path` so `api.*`/`features.*`/`models.*` imports resolve regardless of invocation directory. |
| `tests/units/test_chatbot_queries.py` | Unit tests for all 6 functions in `api/chatbot_queries.py`, using `mongomock` (no real DB needed). |
| `tests/units/test_features.py` | Unit tests for `features/cci.py`, `features/engineer.py`, `features/label.py` — one class per feature, happy-path + null-handling + boundary cases, plus a full-pipeline integration smoke test. |

### 4.8 Root-level notebooks

| File | Purpose |
|---|---|
| `eda.ipynb` | The earliest, lightest exploratory-data-analysis pass over the raw dataset. |
| `main_notebook.ipynb` | The primary end-to-end working notebook (largest, most recently active): EDA → feature pipeline → training via `train_balanced_importance` (DT + XGBoost) → SHAP → driver extraction → ad-hoc analysis of exported worklists. This is the notebook whose model track matches production. |
| `diabetic_readmission_model.ipynb` | A **self-contained, standalone experiment** — a hand-rolled heuristic scoring model (per-feature "raw score" summed into a patient score), structurally unrelated to the `models/train_*.py` scripts and **not wired into the production pipeline or API in any way**. Kept for reference; treat as exploratory, not part of the shipped system. |

### 4.9 Root config/misc files

| File | Purpose |
|---|---|
| `requirements.txt` | Python dependencies, grouped by purpose: web framework (FastAPI/Uvicorn), database (pymongo, certifi), ML (scikit-learn, XGBoost, SHAP, pandas/numpy), MLOps (MLflow), orchestration (Prefect), LLM (google-genai), plotting (matplotlib/seaborn), testing (pytest), notebooks (ipython/jupyter). Note: `Flask`/`flask-cors` are listed but not used anywhere in `api/main.py` (FastAPI is the actual framework) — likely a leftover. Most of the very long transitive tail (opentelemetry-*, jsonschema*, etc.) comes from MLflow/Prefect/FastAPI, not direct app dependencies. |
| `.gitignore` | Excludes `.env`, `.venv/`, `mlruns/`, `mlflow.db`, `data/`, `*.csv`, `__pycache__/`, logs, `.DS_Store`, `.vscode/`, `.claude/settings.local.json`, `node_modules/`, `dist/`. |
| `.env` (gitignored) | Backend secrets: `MONGO_URI`, `GEMINI_API_KEY`, `API_KEY` (optional — enables `X-API-Key` auth on the API). See §6. |
| `.claude/launch.json` | Dev-server launch config for Claude Code's browser preview tooling (`npm --prefix frontend run dev`). |

---

## 5. Which model is actually in production

There are **four parallel training tracks** (`train.py`, `train_balanced.py`,
`train_balanced_importance.py`, `train_xgboost.py`), each with its own MLflow-registered model,
`docs/diabetic/model_validation_report_*.md`, and `docs/band_thresholds_*.json`. Nothing in the repo
states in plain language which one is "the" model — this is documented here for the first time:

**`train_balanced_importance.py` → registered model `readmission-dt-balanced-importance` is
production.** Confirmed by code, not just convention: `api/main.py`
(`MANUAL_SCORING_MODEL_NAME`), `outputs/export_worklist.py` (`DEFAULT_MODEL_NAME`), and
`pipeline/batch_flow.py` (`run_batch_pipeline`'s default `model_name`) all hard-code this exact
name, and all three read `docs/diabetic/band_thresholds_balanced_importance.json` for band cutoffs. It's
also the best-performing track (AUC-ROC 0.706, the highest of the four) with the most clinically
usable precision/recall trade-off — the plain "balanced" track, by contrast, flags almost every
patient as high-risk (recall 0.995) and isn't actually discriminating.

| Track | Script | AUC-ROC | Validation gate (≥0.65) |
|---|---|---|---|
| Base | `train.py` | 0.646 | **Failed** |
| Balanced | `train_balanced.py` | 0.689 | Passed |
| **Balanced + importance (production)** | `train_balanced_importance.py` | **0.706** | Passed |
| XGBoost | `train_xgboost.py` | 0.670 | Passed |

---

## 6. Data, model registry, and environment setup

### 6.1 Not tracked in git (must exist locally to run anything)

| Path | What it is |
|---|---|
| `data/diabetic/diabetic_data.csv` | The raw UCI diabetic-readmission dataset — the source of truth for the whole pipeline. |
| `data/reference/noshow.csv` | A secondary dataset used only by `features.engineer.add_probabilistic_no_show` (transfer-learning source for the no-show proxy feature). Pipeline degrades gracefully (all-zeros) if absent. |
| `data/features*.csv`, `data/test_scored*.csv` | Generated intermediate/output files from the training scripts — one set per track. |
| `data/input/` | Drop new discharge-batch CSVs here for `pipeline/batch_flow.py` to pick up. |
| `data/output/` | Generated worklist/summary exports land here. |
| `data/diabetic/model_card.json` | Read by `GET /api/model/metrics` in `api/main.py`. |
| `mlruns/` | Local MLflow model registry/tracking store — this is where trained models actually live and get loaded from at serving time. |
| `mlflow.db` | Local MLflow tracking backend database. |

None of the above are in git (`.gitignore` excludes `data/`, `*.csv`, `mlruns/`, `mlflow.db`).
**A new environment needs these recreated or copied over before the pipeline/API will run.**

### 6.2 Environment variables

**Root `.env`** (backend, gitignored):
```
MONGO_URI=<MongoDB connection string>
GEMINI_API_KEY=<Google Gemini API key, required for the chatbot>
API_KEY=<optional — if set, the API requires this in the X-API-Key header>
```
Note: `MLFLOW_TRACKING_URI` and `GEMINI_MODEL` are **not** read from this file — they're
hard-coded constants inside `models/driver_extractor.py` / `models/train_*.py`
(`http://127.0.0.1:5000`, with automatic fallback to local `./mlruns`) and
`api/chatbot_gemini.py` (`gemini-flash-lite-latest`) respectively.

**`frontend/.env`** (gitignored):
```
VITE_USE_MOCK=false          # true = run against in-memory mock data, no backend needed
VITE_API_BASE_URL=http://localhost:8000
VITE_API_KEY=<must match the backend's API_KEY, only needed if the backend enforces it>
```

---

## 7. Running the project locally

```bash
# Backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
# populate .env (see §6.2) and data/diabetic/diabetic_data.csv (see §6.1)
.venv/bin/uvicorn api.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev            # serves on http://localhost:5173

# Run the batch pipeline manually
.venv/bin/python pipeline/batch_flow.py

# Run tests
.venv/bin/pytest
```

Training a model from scratch (only needed if retraining): run `features/build_features.py` (or
the in-script feature generation inside `models/train_balanced_importance.py`), then
`models/train_balanced_importance.py`, then `models/calibrate.py` to regenerate thresholds and
validation reports.

---

## 8. Known duplication / tech debt worth knowing about

- **Feature engineering, CCI, and driver-extraction logic is duplicated** between the real
  pipeline modules (`features/*.py`, `models/driver_extractor.py`) and inlined copies inside
  `api/main.py`'s manual-scoring endpoints. This exists so a single-patient form submission can
  be scored without running the full batch pipeline, but it means **a change to feature logic or
  driver labels must be made in both places** to stay consistent.
- **`docs/diabetic/roc_curve.png` is a single shared file**, not one per track — each
  `model_validation_report_*.md` links to the same path, so it only reflects whichever track was
  calibrated most recently (currently `balanced_importance`). Older reports' ROC image references
  are effectively stale.
- **No `docs/classification_report_balanced_importance.txt`** exists (the other three tracks have
  one) — that track's classification metrics only live inside its `.md` validation report.
- **`docs/diabetic/interpretability_review.txt`** is a manual sign-off checklist for the Week-3
  interpretability gate; its checkboxes are unchecked in the committed version, meaning that
  sign-off step was never formally closed out.
- **`Flask`/`flask-cors`** are listed in `requirements.txt` but unused (the API is FastAPI-only).
- Frontend: `pages/PatientDetail.jsx` imports `getSummaryHistory` from the API client but never
  calls it — stale import from a prior refactor. `pages/TestComponents.jsx` (route
  `/test-components`) is a developer-only component gallery, reachable but not linked from the
  sidebar nav — not a real product page.
- Two independent "patient detail" surfaces exist by design, not by accident: the Dashboard's
  slide-in `PatientDetailPanel` (quick view) and the full page at `/patients/:id`. Both fetch
  independently and both embed the care-coordination widget.

---

## 9. Where things live, quick reference

| I want to... | Look at |
|---|---|
| Understand what a model feature means | `docs/diabetic/feature_mapping.md`, `docs/diabetic/feature_notes.md` |
| Understand the prediction target | `docs/diabetic/label_definition.md` (documents the *original* label; the production model uses the balanced+importance variant from `features/label.py`) |
| See model performance / thresholds | `docs/diabetic/model_validation_report_balanced_importance.md`, `docs/diabetic/band_thresholds_balanced_importance.json` |
| Add/change an API endpoint | `api/main.py` |
| Change how risk drivers are worded | `models/driver_extractor.py`'s `LABEL_MAP` **and** the duplicated copy in `api/main.py` (see §8) |
| Change the batch pipeline | `pipeline/batch_flow.py` |
| Add a new frontend page | `frontend/src/pages/`, then register the route in `frontend/src/App.jsx` |
| Change what the chatbot can answer | Add a query function to `api/chatbot_queries.py`, register it as a `FunctionDeclaration` in `api/chatbot_gemini.py` |
| See client-facing project docs (requirements, progress decks) | `docs/deliverables/` |
