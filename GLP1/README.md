# GLP-1 Adherence & Cost Intelligence Platform

An end-to-end analytics platform that predicts GLP-1 (semaglutide, tirzepatide, dulaglutide, liraglutide) therapy adherence over a ~180-day window and surfaces payer-relevant intelligence: risk triage, cost of dropout, break-even ROI on adherence interventions, and metabolic rebound trajectories.

The stack is a **FastAPI + MongoDB backend**, a **React + Vite dashboard**, and an **offline data / ML pipeline** built on public health datasets (NHANES, MEPS, FAERS, ClinicalTrials.gov, CMS Medicare Part D).

---

## Table of contents
1. [What the platform does](#what-the-platform-does)
2. [Repository layout](#repository-layout)
3. [Prerequisites](#prerequisites)
4. [Quick start](#quick-start-local-dev)
5. [First-time setup: seeding MongoDB](#first-time-setup-seeding-mongodb)
6. [Rebuilding the data & model pipeline from scratch](#rebuilding-the-data--model-pipeline-from-scratch)
7. [Architecture at a glance](#architecture-at-a-glance)
8. [Key concepts to read before contributing](#key-concepts-to-read-before-contributing)
9. [Documentation index](#documentation-index)
10. [Troubleshooting](#troubleshooting)

---

## What the platform does

Given a cohort of patients, the platform answers three questions:

| Question | Layer that answers it |
|---|---|
| **Who will drop off?** — patient-level dropout probability + top drivers | Gradient Boosting classifier + per-patient SHAP |
| **What does dropout cost?** — downstream medical spend, metabolic rebound | Consequence Model (Markov + rebound engine) |
| **Is intervention worth it?** — break-even adherence, payer ROI, budget impact | Payer ROI Synthesizer + Budget Simulator |

The dashboard organises this into eight screens: Executive Summary, Patient Risk Panel, Patient Detail, Segment Explorer, Survival Analysis, Cost Effectiveness, Budget Simulator, and **Cost of Inaction** (the consequence-model workspace).

> **Important context.** The adherence target (`is_adherent`) is *simulated* from a transparent behavioral equation because no public patient-level adherence outcome dataset exists for GLP-1s. Model AUC (~0.89) reflects how well GB recovers that equation, not clinical performance. Molecule assignment is random-seeded. See [docs/DATA_AND_MODEL_DOCUMENTATION.md §7 & §10.4](docs/DATA_AND_MODEL_DOCUMENTATION.md) for the full limitations list — read this before making any clinical or product claims.

---

## Repository layout

```
GLP-1_Adherence/
├── README.md                      ← you are here
├── .gitignore
│
├── Data_Collection/               ← Step 1: pull raw public-health data
│   ├── NHANES/                    ← demographics + clinical baseline
│   ├── MEPS/                      ← out-of-pocket cost signal
│   ├── FAERS/                     ← real-world adverse events
│   ├── ClinicalTrials/            ← trial-grade AEs & outcomes
│   └── Medicare Part D Prescribers - by Provider and Drug/
│                                  ← prescriber refill continuity
│
├── Fusion/                        ← Step 2: stack raw sources into one training table
│   ├── layer_1.py                 ← NHANES + MEPS → patient baseline + cost
│   ├── layer_2.py                 ← + FAERS + trials → bio_friction
│   ├── layer_3.py                 ← + CMS Part D → system reliability
│   ├── final.py                   ← + simulated is_adherent label
│   ├── mapper.py, inspect_sources.py
│
├── Processing/
│   └── cleanup.ipynb              ← Step 3: schema check, null-impute, upsample → GLP1_CLEANED.csv
│
├── Model/                         ← Step 4: train + downstream analytics
│   ├── model.ipynb                ← GB training, SHAP, K-Means, KM survival, CEA
│   └── consequence/               ← Step 5: consequence-model layer (pure Python, unit-tested)
│       ├── markov.py              ← 6-state Markov chain
│       ├── downstream_cost.py     ← Phase 1 — per-patient projected cost
│       ├── rebound.py, rebound_risk.py
│       │                          ← Phase 2 — HbA1c/BMI rebound engine
│       ├── roi.py, payer_roi.py   ← Phase 3 — break-even + ROI synthesizer
│       ├── registry.py            ← loads clinical/economic params from docs/evidence/
│       └── tests/                 ← 73 unit tests (pytest)
│
├── Backend/                       ← FastAPI service (talks to MongoDB, serves dashboard)
│   ├── main.py                    ← app entrypoint (uvicorn)
│   ├── core/                      ← settings, Motor client, model & artifact loaders
│   ├── routers/                   ← one router per dashboard area (summary, patients,
│   │                                segments, survival, cost, budget, shap, info,
│   │                                consequence)
│   ├── schemas/                   ← Pydantic response models
│   ├── scripts/migrate_csv_to_mongo.py
│   │                              ← one-shot seeder: pipeline CSVs → Mongo collections
│   ├── data/                      ← pipeline output CSVs (gitignored; seed source)
│   ├── requirements.txt           ← API runtime deps only (what a host installs)
│   ├── requirements-dev.txt       ← + seeder, notebooks, tests, collectors
│   └── README.md                  ← backend-specific docs
│
├── Frontend/                      ← React + Vite dashboard
│   ├── package.json
│   └── src/
│       ├── pages/                 ← one file per screen; CostOfInaction/ has 3 sub-panels
│       ├── components/            ← layout/, charts/ (Recharts), shared/
│       ├── hooks/                 ← one hook per API endpoint (with mockData fallback)
│       ├── context/               ← RoleContext, PatientsContext
│       └── data/                  ← api.js (fetch wrapper), mockData.js, config.js
│
└── docs/                          ← every markdown lives here
    ├── DATA_AND_MODEL_DOCUMENTATION.md   ← the single "read once, understand everything" doc
    ├── DATA_DICTIONARY.md
    ├── DATA_REQUEST.md
    ├── CONSEQUENCE_MODEL_IMPLEMENTATION_PLAN.md
    ├── ROI_CALCULATION_METHODOLOGY.md
    ├── PAYER_ROI_PROGRESS_REPORT.md
    ├── progress/                  ← phase-by-phase build notes (was updates/)
    └── evidence/                  ← audit trail + parameter registry (was evidence/)
        ├── parameter_registry.csv ← ALL clinical/economic constants for the consequence model
        ├── cea_audit.md
        ├── markov_scope_decision.md
        └── overrides/             ← per-payer pricing scenarios (medicare_2028, post_generic)
```

---

## Prerequisites

| Tool | Version | Why |
|---|---|---|
| **Python** | 3.11 | Backend + data pipeline + consequence model |
| **Node.js** | ≥ 18 | Frontend (Vite 7 + React 19) |
| **MongoDB** | Atlas free tier, or local `mongod` ≥ 6 | Backend data store |
| **Git** | any | Cloning |
| **npm / yarn** | any | Frontend deps |

Optional (only if regenerating training data):
- Jupyter (for `Processing/cleanup.ipynb` and `Model/model.ipynb`)
- Raw dataset files from CMS/NHANES/MEPS/FAERS/ClinicalTrials (paths are hardcoded in each collector script — see [docs/DATA_REQUEST.md](docs/DATA_REQUEST.md))

---

## Quick start (local dev)

Fresh-clone friendly: pipeline CSVs and the trained model file are committed under [Backend/data/](Backend/data/), so you only need MongoDB + Python + Node to get the whole stack running. Seven steps end-to-end.

### 1. Clone & install backend

```bash
git clone <repo-url>
cd GLP-1_Adherence/Backend
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt # runtime + seeder/notebook/test deps
```

### 2. Set up MongoDB

You have two options — pick one.

**Option A — MongoDB Atlas (free M0, recommended for new contributors)**

1. Sign in at [cloud.mongodb.com](https://cloud.mongodb.com) → **Create Project** → **Build a Database** → choose the free **M0** tier.
2. **Create a database user** (Security → Database Access → Add New Database User). Save the username + password — you'll paste them into the URI.
3. **Whitelist your IP** (Security → Network Access → Add IP Address → "Allow access from anywhere" `0.0.0.0/0` is fine for dev). Without this step every query hangs.
4. On the cluster overview, click **Connect** → **Drivers** → copy the connection string. It looks like:
   ```
   mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
   Replace `<username>` and `<password>` inline. If the password contains `@ : / ? # [ ] &`, URL-encode them (`@` → `%40`, `:` → `%3A`, etc.) or the URI parser will misread them.

You do **not** need to create the `glp1_analytics` database manually — Mongo creates it on the first `insert_many` when the seeder runs.

**Option B — Local MongoDB**

Install and start `mongod` locally (Docker: `docker run -d -p 27017:27017 --name glp1-mongo mongo:7`). No auth needed for dev.

### 3. Configure backend env

Create `Backend/.env`:

```env
# Atlas example:
MONGODB_URI=mongodb+srv://your_user:URL_ENCODED_PWD@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
# Local example:
# MONGODB_URI=mongodb://localhost:27017

MONGODB_DB_NAME=glp1_analytics
DATA_DIR=./data
CORS_ORIGINS=["http://localhost:5173","http://localhost:4173"]
SECRET_KEY=<run: python -c "import secrets; print(secrets.token_hex(32))">
```

### 4. Confirm pipeline artifacts are present

The 15 CSVs + `final_gb_model.pkl` + `shap_values_test.npy` needed by the backend are **committed** under [Backend/data/](Backend/data/) — a fresh clone already has them. Skip to step 5 unless you're regenerating the pipeline (see [Rebuilding](#rebuilding-the-data--model-pipeline-from-scratch)).

### 5. Seed MongoDB (one-time)

```bash
cd Backend
python -m scripts.migrate_csv_to_mongo
```

Expected output (12 collections, ~7,566 patients, all ✅s — no ⚠️ skips):
```
📂  Reading CSVs from: .../Backend/data
🔌  Connecting to:     glp1_analytics on Atlas
🚚  Migrating…
  ✅  patients: 7,566
  ✅  cost_effectiveness: 4
  ✅  segment_profiles: 4
  ✅  survival_checkpoints: 4
  ✅  survival_curves: 4
  ✅  progression_cost: 7,566
  ✅  rebound_risk: 7,566
  ✅  rebound_trajectory: 60
  ✅  rebound_sensitivity: 12
  ✅  payer_roi: 12
  ✅  payer_roi_yearly: 60
  ✅  model_meta: 1
✅  Migration complete.
```

The script drops-and-reinserts each collection, so re-running after a pipeline re-export always produces a clean snapshot.

If you see `❌ Atlas connection failed: ...` — your IP isn't whitelisted (Atlas → Network Access) or the password in the URI isn't URL-encoded.

### 6. Start the backend

```bash
uvicorn main:app --reload --port 8000
```

- Health check → http://localhost:8000/health
- Swagger UI → http://localhost:8000/docs

### 7. Start the frontend

In a second terminal:

```bash
cd Frontend
npm install
npm run dev
```

- Dashboard → http://localhost:5173

Optional `Frontend/.env`:
```env
VITE_API_URL=http://localhost:8000     # default; override if backend is elsewhere
```

Frontend hooks fall back to `src/data/mockData.js` if any API call fails, so the UI stays usable during backend outages.

---

## First-time setup: seeding MongoDB

The backend is Mongo-native — CSV files are only used to *seed* collections. The relationship:

```
pipeline outputs (CSV/npy/pkl in Backend/data/)
              │
              ▼
    migrate_csv_to_mongo.py
              │
              ▼
   MongoDB `glp1_analytics` DB
              │
              ▼
   FastAPI routers (async queries via Motor)
              │
              ▼
   React hooks (fetch → api.js → components)
```

Collections seeded (from [Backend/scripts/migrate_csv_to_mongo.py](Backend/scripts/migrate_csv_to_mongo.py)):

| Collection | Source file(s) |
|---|---|
| `patients` | `GLP1_FINAL_WITH_SURVIVAL.csv` ⨝ `shap_patient_drivers.csv` |
| `segment_profiles` | computed from `patients` |
| `cost_effectiveness` | `cost_effectiveness.csv` ⨝ `icer_by_segment.csv` |
| `survival_checkpoints`, `survival_curves` | `survival_checkpoints.csv` + KM fit |
| `progression_cost` | `progression_cost.csv` |
| `rebound_risk`, `rebound_trajectory`, `rebound_sensitivity` | `rebound_*.csv` |
| `payer_roi`, `payer_roi_yearly` | `payer_roi*.csv` |
| `model_meta` | hardcoded notebook metrics |

Binary ML artifacts (`final_gb_model.pkl`, `shap_values_test.npy`) stay on disk in `Backend/data/` — loaded at startup by [Backend/core/loader.py](Backend/core/loader.py) and [Backend/core/model.py](Backend/core/model.py).

---

## Rebuilding the data & model pipeline from scratch

Only needed when refreshing data or changing pipeline logic. Full detail lives in [docs/DATA_AND_MODEL_DOCUMENTATION.md §9](docs/DATA_AND_MODEL_DOCUMENTATION.md).

1. Place raw source files into their respective `Data_Collection/<source>/` folders (paths hardcoded per script).
2. Run collectors in any order:
   ```bash
   python Data_Collection/NHANES/nhanes.py
   python Data_Collection/MEPS/meps.py
   python Data_Collection/FAERS/fares.py
   python Data_Collection/ClinicalTrials/clinical_trials.py
   python "Data_Collection/Medicare Part D Prescribers - by Provider and Drug/glp1_cms_processor.py"
   ```
3. Run fusion **in order** (each layer consumes the previous):
   ```bash
   python Fusion/layer_1.py    # NHANES + MEPS
   python Fusion/layer_2.py    # + FAERS + trials
   python Fusion/layer_3.py    # + CMS
   python Fusion/final.py      # + simulated is_adherent
   ```
4. Run [Processing/cleanup.ipynb](Processing/cleanup.ipynb) end-to-end → produces `GLP1_CLEANED.csv` (7,566 × 15).
5. Run [Model/model.ipynb](Model/model.ipynb) end-to-end → trains GB v2, runs SHAP, K-Means (k=4), Kaplan-Meier survival, and CEA. Emits all `Backend/data/*.csv` + `.pkl` + `.npy` files.
6. Run the consequence-model scripts (pure Python, use `docs/evidence/parameter_registry.csv`):
   ```bash
   python -m Model.consequence.downstream_cost
   python -m Model.consequence.rebound_risk
   python -m Model.consequence.payer_roi
   ```
7. Re-seed Mongo: `cd Backend && python -m scripts.migrate_csv_to_mongo`.

### Running the consequence-model tests

```bash
cd GLP-1_Adherence
python -m pytest Model/consequence/tests/ -q
```
Expect 73 tests passing.

---

## Architecture at a glance

```
┌───────────────────────────────────────────────────────────────┐
│  OFFLINE (Python, run when data changes)                      │
│                                                               │
│  Data_Collection/  →  Fusion/  →  Processing/  →  Model/      │
│  (raw pulls)         (stack)      (cleanup)       (train +    │
│                                                    SHAP + KM  │
│                                                    + CEA)     │
│                              ↓                                │
│                    Model/consequence/                         │
│                    (Markov + rebound + ROI, pure Python)      │
│                              ↓                                │
│                     Backend/data/*.csv                        │
└───────────────────────────────────────────────────────────────┘
                              ↓  (one-shot seed)
                    scripts/migrate_csv_to_mongo.py
                              ↓
                     ┌──────────────────┐
                     │  MongoDB Atlas   │
                     │  glp1_analytics  │
                     └──────────────────┘
                              ↑
                              │  async queries (Motor)
                     ┌──────────────────┐
                     │  FastAPI         │  ← binary .pkl / .npy
                     │  Backend/main.py │    loaded from disk at startup
                     └──────────────────┘
                              ↑
                              │  fetch (mockData fallback)
                     ┌──────────────────┐
                     │  React + Vite    │
                     │  Frontend/       │
                     └──────────────────┘
```

**API surface** (all under `/api`, full list in [Backend/README.md](Backend/README.md)):
`summary`, `shap/global`, `patients`, `segments`, `survival`, `cost-effectiveness`, `budget-impact`, `model/info`, plus the consequence-model routes `consequence/downstream-cost`, `consequence/rebound-risk`, `consequence/payer-roi?intervention_cost=<usd>`.

---

## Key concepts to read before contributing

1. **The four risk segments** (K-Means k=4). Every screen slices by these:
   - Cluster 0 — Low Urgency Dropout Risk
   - Cluster 1 — Financial Barrier Dropout Risk
   - Cluster 2 — Low Friction Strong Adherer
   - Cluster 3 — Moderate Risk Moderate Adherer

2. **`docs/evidence/parameter_registry.csv` is the source of truth** for every clinical / economic constant in the consequence model (transition rates, drug costs, discount rate, rebound plateaus). Two rows are flagged `"ASSUMED, NOT SOURCED"` — treat them accordingly.

3. **Payer-type overrides live in `docs/evidence/overrides/`.** Adding a new pricing scenario is just adding one CSV (`medicare_2028.csv`, `post_generic.csv`, ...); no code changes required — [Model/consequence/registry.py](Model/consequence/registry.py) picks up any stem present in that folder.

4. **The frontend has a mock-data fallback** in `src/data/mockData.js`. Every hook will fail-soft to it if the API is down, so you can develop UI without the backend.

5. **Role-based UI is client-side only.** `RoleContext` toggles between `case_manager` and `insurer` views (e.g., Payer ROI is hidden from case managers). No auth layer.

---

## Documentation index

| Document | Read when |
|---|---|
| [docs/DATA_AND_MODEL_DOCUMENTATION.md](docs/DATA_AND_MODEL_DOCUMENTATION.md) | Onboarding — full data → model → consequence walkthrough with limitations |
| [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md) | You need to know what a column means |
| [docs/DATA_REQUEST.md](docs/DATA_REQUEST.md) | You need to procure raw source data |
| [docs/CONSEQUENCE_MODEL_IMPLEMENTATION_PLAN.md](docs/CONSEQUENCE_MODEL_IMPLEMENTATION_PLAN.md) | Working on Markov / rebound / ROI code |
| [docs/ROI_CALCULATION_METHODOLOGY.md](docs/ROI_CALCULATION_METHODOLOGY.md) | Debugging or extending the ROI formula |
| [docs/PAYER_ROI_PROGRESS_REPORT.md](docs/PAYER_ROI_PROGRESS_REPORT.md) | Status of the payer-ROI feature |
| [docs/progress/](docs/progress/) | Phase-by-phase build notes (Phase 0 → Phase 4 week 7) |
| [docs/evidence/cea_audit.md](docs/evidence/cea_audit.md) | Sanity-checking any CEA output |
| [docs/evidence/markov_scope_decision.md](docs/evidence/markov_scope_decision.md) | Why the Markov has the states it does |
| [Backend/README.md](Backend/README.md) | Backend-only setup, API list, data-file inventory |

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'core'` when running the backend.**
Run from inside `Backend/`, not the repo root: `cd Backend && uvicorn main:app --reload`.

**`FileNotFoundError` on `docs/evidence/parameter_registry.csv` from a consequence-model script.**
Run consequence scripts as modules from the repo root: `python -m Model.consequence.payer_roi`. `PROJECT_ROOT` is resolved via `Path(__file__).resolve().parents[2]`.

**Backend starts but every endpoint returns empty.**
You forgot to seed Mongo. Run `python -m scripts.migrate_csv_to_mongo` from `Backend/`.

**Frontend loads but everything looks like `undefined`.**
Backend is unreachable and mock-fallback loaded silently. Open browser devtools → Network to see the failing calls, then check `VITE_API_URL` and that the backend is up on port 8000.

**Model-file errors at backend startup.**
`final_gb_model.pkl` or `shap_values_test.npy` missing from `Backend/data/`. Regenerate via `Model/model.ipynb` or obtain from the team.

**Pytest can't find `pytest`.**
Use the Backend venv: `./Backend/venv/Scripts/python.exe -m pytest Model/consequence/tests/ -q` (Windows) or activate the venv first.
