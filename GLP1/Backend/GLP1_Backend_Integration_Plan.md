# GLP-1 Platform — Backend & Integration Plan
## FastAPI + React Full-Stack Architecture

**Project:** GLP-1 Adherence & Cost Intelligence Platform
**Backend Stack:** Python 3.11 · FastAPI · Pandas · scikit-learn · SHAP · lifelines
**Frontend:** React 18 (already built) — mock data layer to be replaced
**Date:** May 2026

---

## 1. What the Backend Needs to Do

The React frontend was built with a mock data layer (`src/data/mockData.js`) that mirrors all API response shapes exactly. The backend's job is to reproduce those shapes from real data — the CSV files, the trained model pickle, and the SHAP arrays — and serve them through a FastAPI application that the frontend calls instead of the mock.

There are three distinct categories of work:

**Static data serving** — Load the CSV files produced by the Jupyter notebook pipeline into memory at startup and expose them as JSON endpoints. No computation at request time, just serialization. Covers: summary KPIs, segment profiles, survival checkpoints, cost-effectiveness ratios, ICER table, patient list.

**Dynamic computation** — Endpoints that take request parameters and compute results on the fly. The budget impact simulator is the primary case: the frontend sends slider values, the backend recalculates waste recovered and net saving using the actual CEA data, and returns the result. The patient prediction endpoint also fits here.

**Model serving** — Load `final_gb_model.pkl` at startup and expose a prediction endpoint that accepts patient features, runs them through the trained GradientBoostingClassifier, applies the decision threshold, and returns dropout probability + prediction label. SHAP values are pre-computed for the test set and served from `shap_values_test.npy` — they do not need to be recomputed per request.

---

## 2. Project Structure

```
glp1-backend/
│
├── main.py                    # FastAPI app, CORS, startup loader
├── requirements.txt
├── .env                       # DATA_DIR path, CORS origins
│
├── core/
│   ├── __init__.py
│   ├── config.py              # Settings from .env
│   ├── loader.py              # Loads all data at startup into memory
│   └── model.py               # Model + scaler + SHAP loader
│
├── routers/
│   ├── __init__.py
│   ├── summary.py             # GET /api/summary
│   ├── patients.py            # GET /api/patients, GET /api/patients/{id}
│   ├── segments.py            # GET /api/segments, GET /api/segments/{id}
│   ├── survival.py            # GET /api/survival
│   ├── cost.py                # GET /api/cost-effectiveness
│   ├── budget.py              # POST /api/budget-impact
│   ├── shap.py                # GET /api/shap/global
│   └── info.py                # GET /api/model/info
│
├── schemas/
│   ├── __init__.py
│   ├── summary.py             # Pydantic response models
│   ├── patients.py
│   ├── segments.py
│   ├── survival.py
│   ├── cost.py
│   └── budget.py
│
└── data/                      # Symlink or copy of notebook output files
    ├── GLP1_FINAL_WITH_SURVIVAL.csv
    ├── GLP1_SEGMENTED.csv
    ├── segment_profiles.csv
    ├── survival_checkpoints.csv
    ├── cost_effectiveness.csv
    ├── icer_by_segment.csv
    ├── budget_impact.csv
    ├── shap_patient_drivers.csv
    ├── shap_values_test.npy
    └── final_gb_model.pkl
```

---

## 3. Dependencies

```txt
# requirements.txt
fastapi==0.115.0
uvicorn[standard]==0.30.0
pandas==2.2.0
numpy==1.26.4
scikit-learn==1.4.0
shap==0.45.0
lifelines==0.29.0
python-dotenv==1.0.0
pydantic==2.7.0
pydantic-settings==2.3.0
```

Install and run:
```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

---

## 4. Startup Data Loading

All data is loaded once at application startup into module-level variables. No database required — the dataset is ~7,500 rows and fits entirely in memory.

```python
# core/loader.py

import pandas as pd
import numpy as np
import pickle
from pathlib import Path
from core.config import settings

# Module-level state — loaded once at startup
df_main: pd.DataFrame = None       # GLP1_FINAL_WITH_SURVIVAL.csv
df_shap: pd.DataFrame = None       # shap_patient_drivers.csv
df_segments: pd.DataFrame = None   # segment_profiles.csv
df_survival: pd.DataFrame = None   # survival_checkpoints.csv
df_cea: pd.DataFrame = None        # cost_effectiveness.csv
df_icer: pd.DataFrame = None       # icer_by_segment.csv
df_budget: pd.DataFrame = None     # budget_impact.csv
shap_values: np.ndarray = None     # shap_values_test.npy
model_pkg: dict = None             # final_gb_model.pkl contents

def load_all():
    global df_main, df_shap, df_segments, df_survival
    global df_cea, df_icer, df_budget, shap_values, model_pkg

    d = Path(settings.data_dir)
    df_main     = pd.read_csv(d / "GLP1_FINAL_WITH_SURVIVAL.csv")
    df_shap     = pd.read_csv(d / "shap_patient_drivers.csv")
    df_segments = pd.read_csv(d / "segment_profiles.csv")
    df_survival = pd.read_csv(d / "survival_checkpoints.csv")
    df_cea      = pd.read_csv(d / "cost_effectiveness.csv")
    df_icer     = pd.read_csv(d / "icer_by_segment.csv")
    df_budget   = pd.read_csv(d / "budget_impact.csv")
    shap_values = np.load(d / "shap_values_test.npy")

    with open(d / "final_gb_model.pkl", "rb") as f:
        model_pkg = pickle.load(f)

    print(f"✅ Data loaded — {len(df_main):,} patient records")
    print(f"✅ Model loaded — threshold: {model_pkg['threshold']:.4f}")
    print(f"✅ SHAP values loaded — shape: {shap_values.shape}")
```

```python
# main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from core.loader import load_all
from routers import summary, patients, segments, survival, cost, budget, shap, info

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_all()          # ← runs once on startup
    yield
    # cleanup on shutdown if needed

app = FastAPI(
    title="GLP-1 Analytics API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(summary.router,  prefix="/api")
app.include_router(patients.router, prefix="/api")
app.include_router(segments.router, prefix="/api")
app.include_router(survival.router, prefix="/api")
app.include_router(cost.router,     prefix="/api")
app.include_router(budget.router,   prefix="/api")
app.include_router(shap.router,     prefix="/api")
app.include_router(info.router,     prefix="/api")
```

---

## 5. All API Endpoints — Full Specification

---

### GET /api/summary

**Purpose:** Executive Summary KPI strip — 5 cards + adherence by segment + global SHAP bar data

**Computation:** Aggregate `df_main` at startup. All values static after load.

**Response shape:**
```json
{
  "kpis": {
    "total_patients": 7566,
    "adherence_rate": 0.47,
    "dropout_rate": 0.53,
    "avg_annual_cost": 10603,
    "wasted_spend_annual": 40069863
  },
  "adherence_by_segment": [
    {"cluster": 0, "segment": "Low Urgency Dropout", "adherence": 0.208, "n": 1902, "color": "#EF5350"},
    {"cluster": 1, "segment": "Financial Barrier Dropout", "adherence": 0.309, "n": 2104, "color": "#FF7043"},
    {"cluster": 2, "segment": "Low Friction Strong Adherer", "adherence": 0.854, "n": 2383, "color": "#43A047"},
    {"cluster": 3, "segment": "Moderate Risk Moderate Adherer", "adherence": 0.406, "n": 1177, "color": "#1E88E5"}
  ],
  "dropout_by_window": [
    {"window": "By Day 30",  "seg0": 356, "seg1": 303, "seg2": 11,  "seg3": 100},
    {"window": "By Day 60",  "seg0": 645, "seg1": 490, "seg2": 18,  "seg3": 179},
    {"window": "By Day 90",  "seg0": 827, "seg1": 655, "seg2": 26,  "seg3": 246},
    {"window": "By Day 180", "seg0": 1507, "seg1": 1455, "seg2": 349, "seg3": 699}
  ]
}
```

**Implementation notes:**
- `adherence_by_segment` computed from `df_main.groupby('cluster')['is_adherent'].agg(['mean','count'])`
- `dropout_by_window` computed from `df_main.groupby(['cluster','time_to_dropout'])` binned at 30/60/90/180
- `wasted_spend_annual` = sum of `annual_drug_cost * (1 - is_adherent)` across all rows
- Cache result at startup — never recomputes

---

### GET /api/patients

**Purpose:** Patient Risk Panel table — paginated, filtered, sorted list

**Query parameters:**
```
page:          int     default=0
page_size:     int     default=20, max=100
segment:       int     optional (0-3) — filter by cluster
molecule:      str     optional — filter by assigned_molecule
min_risk:      float   optional (0.0-1.0) — filter dropout_prob >= value
prediction:    str     optional ("Dropout Risk" | "Likely Adherent")
sort_by:       str     default="dropout_prob"
sort_dir:      str     default="desc" ("asc" | "desc")
search:        str     optional — text match on driver_1
```

**Response shape:**
```json
{
  "total": 1514,
  "page": 0,
  "page_size": 20,
  "patients": [
    {
      "patient_idx": 42,
      "dropout_prob": 0.8912,
      "prediction": "Dropout Risk",
      "cluster": 0,
      "segment": "Low Urgency Dropout",
      "assigned_molecule": "SEMAGLUTIDE",
      "avg_oop_cost": 87.50,
      "driver_1": "Financial pressure relative to income",
      "driver_1_direction": "increases dropout risk",
      "driver_2": "Provider & pharmacy refill reliability",
      "driver_2_direction": "increases dropout risk",
      "driver_3": "Blood sugar control (HbA1c)",
      "driver_3_direction": "reduces dropout risk",
      "BMXBMI": 38.4,
      "RIDAGEYR": 52
    }
  ],
  "summary": {
    "high_risk_count": 234,
    "financial_barrier_count": 187
  }
}
```

**Implementation notes:**
- Source: merge `df_main` with `df_shap` on `patient_idx`
- Filter in pandas, then slice for pagination
- `summary.high_risk_count` = count where `dropout_prob >= 0.75` in the filtered set
- `summary.financial_barrier_count` = count where `driver_1` contains "financial" or "cost"

---

### GET /api/patients/{patient_idx}

**Purpose:** Patient Detail — single patient full profile with SHAP drivers

**Response shape:**
```json
{
  "patient": {
    "patient_idx": 42,
    "dropout_prob": 0.8912,
    "prediction": "Dropout Risk",
    "cluster": 0,
    "segment_label": "Low Urgency Dropout Risk",
    "segment_short": "Low Urgency Dropout",
    "assigned_molecule": "SEMAGLUTIDE",
    "drug_generation": 2,
    "RIDAGEYR": 52,
    "BMXBMI": 38.4,
    "LBXGH": 6.1,
    "comorbidity_score": 1,
    "bio_friction": 0.521,
    "avg_oop_cost": 87.50,
    "income_cost_pressure": 42.3,
    "system_refill_score": 1.14,
    "time_to_dropout": 28,
    "event_occurred": 1
  },
  "shap_drivers": [
    {"rank": 1, "feature": "Financial pressure relative to income", "direction": "increases dropout risk", "shap_value": -0.3812},
    {"rank": 2, "feature": "Provider & pharmacy refill reliability", "direction": "increases dropout risk", "shap_value": -0.2104},
    {"rank": 3, "feature": "Blood sugar control (HbA1c)", "direction": "reduces dropout risk", "shap_value": 0.0843}
  ],
  "segment_survival": {
    "day30": 0.187, "day60": 0.339, "day90": 0.434, "day180": 0.792
  }
}
```

**Implementation notes:**
- Look up by patient_idx in `df_main` (raise 404 if not found)
- Join with `df_shap` to get driver fields
- `segment_survival` pulled from `df_survival` filtered to same cluster
- If `patient_idx` not in `df_shap` (patient was in training set, not test set), return null shap_drivers with explanation

---

### GET /api/segments

**Purpose:** Segment Explorer — all 4 segment profiles

**Response shape:**
```json
{
  "segments": [
    {
      "cluster": 0,
      "label": "Low Urgency Dropout Risk",
      "short": "Low Urgency Dropout",
      "n": 1902,
      "adherence": 0.208,
      "age": 45.0,
      "bmi": 35.9,
      "hba1c": 5.35,
      "oop_cost": 40.51,
      "cost_pressure": 25.4,
      "bio_friction": 0.566,
      "refill_score": 1.19,
      "comorbidity": 0.30,
      "wasted_per_pt": 8412,
      "cost_per_hba1c": 25311,
      "cost_per_weight": 2806
    }
  ]
}
```

**Source:** `df_cea` merged with computed aggregates from `df_main`

---

### GET /api/segments/{cluster_id}

**Purpose:** Single segment deep profile for Segment Explorer tab view

**Response shape:** Single segment object (same fields as above) + feature distributions

```json
{
  "cluster": 2,
  "profile": { "...all fields above..." },
  "distributions": {
    "bmi":  {"mean": 34.7, "std": 6.1, "min": 18.5, "p25": 30.2, "p75": 38.8, "max": 68.0},
    "age":  {"mean": 55.3, "std": 14.2, "min": 21, "p25": 44, "p75": 67, "max": 80},
    "hba1c":{"mean": 6.20, "std": 1.1, "min": 4.2, "p25": 5.4, "p75": 7.1, "max": 15.2}
  }
}
```

**Implementation notes:**
- Filter `df_main` to cluster, compute describe() on BMI/age/HbA1c
- Used by the histogram charts in Segment Explorer

---

### GET /api/survival

**Purpose:** Survival Analysis — KM curve data points + checkpoint table

**Response shape:**
```json
{
  "curves": [
    {
      "cluster": 0,
      "label": "Low Urgency Dropout Risk",
      "color": "#EF5350",
      "adherence": 0.208,
      "data": [
        {"day": 0, "survival": 1.0},
        {"day": 5, "survival": 0.962},
        {"day": 10, "survival": 0.921},
        "..."
      ]
    }
  ],
  "checkpoints": [
    {"cluster": 0, "segment": "Low Urgency Dropout Risk", "day30": 0.187, "day60": 0.339, "day90": 0.434, "day180": 0.792},
    "..."
  ],
  "median_survival": [112, 179, 999, 179],
  "logrank": {
    "test_statistic": 2354.82,
    "p_value": 0.0,
    "significant": true
  }
}
```

**Implementation notes:**
- KM curves are refit at startup using `lifelines.KaplanMeierFitter` on `df_main`
- Curve data points sampled at every 5 days (36 points per cluster)
- `median_survival`: use `kmf.median_survival_time_` — 999 represents >180
- Log-rank test rerun at startup — store result in memory

---

### GET /api/cost-effectiveness

**Purpose:** Cost-Effectiveness Studio — CEA ratios + ICER by segment

**Response shape:**
```json
{
  "cea": [
    {
      "cluster": 0, "label": "Low Urgency Dropout",
      "n": 1902, "annual_cost": 10622,
      "weight_loss": 3.8, "hba1c_reduction": 0.42,
      "cost_per_weight": 2806, "cost_per_hba1c": 25311,
      "icer_insulin_weight": 5622, "icer_insulin_hba1c": 149477,
      "icer_sglt2_weight": 1487,  "icer_sglt2_hba1c": 30145
    }
  ],
  "benchmarks": {
    "glp1": {
      "SEMAGLUTIDE": {"weight_loss_pct": 14.9, "hba1c_reduction": 1.6, "annual_cost": 13000},
      "TIRZEPATIDE": {"weight_loss_pct": 20.9, "hba1c_reduction": 2.1, "annual_cost": 16000},
      "LIRAGLUTIDE": {"weight_loss_pct": 8.0,  "hba1c_reduction": 1.1, "annual_cost": 7800},
      "DULAGLUTIDE": {"weight_loss_pct": 4.5,  "hba1c_reduction": 1.4, "annual_cost": 7200}
    },
    "comparators": {
      "insulin_glargine": {"weight_loss_pct": -1.5, "hba1c_reduction": 1.5, "annual_cost": 3500},
      "sglt2_inhibitor":  {"weight_loss_pct":  3.0, "hba1c_reduction": 0.8, "annual_cost": 5800}
    },
    "icer_threshold": 50000
  }
}
```

**Source:** `df_cea`, `df_icer` — loaded directly from CSVs

---

### POST /api/budget-impact

**Purpose:** Budget Impact Simulator — recalculate net saving with custom parameters

**Request body:**
```json
{
  "dropout_reduction_pct": 15,
  "intervention_cost_per_patient": 500,
  "population_scope_pct": 100
}
```

**Response shape:**
```json
{
  "total_net_saving": 2212479,
  "total_waste_recovered": 5995479,
  "total_intervention_cost": 3783000,
  "break_even_month": 8,
  "segments": [
    {
      "cluster": 0,
      "label": "Low Urgency Dropout",
      "n_in_scope": 1902,
      "baseline_dropout_rate": 0.792,
      "new_dropout_rate": 0.673,
      "baseline_wasted_spend": 14250622,
      "waste_recovered": 2137593,
      "intervention_cost": 951000,
      "net_saving": 1186593,
      "roi_positive": true
    }
  ]
}
```

**Implementation — full calculation logic:**
```python
@router.post("/budget-impact")
async def budget_impact(req: BudgetRequest):
    reduction    = req.dropout_reduction_pct / 100
    scope        = req.population_scope_pct / 100
    interv_cost  = req.intervention_cost_per_patient

    segments_out = []
    total_net = total_waste = total_interv = 0

    for cluster_id in range(4):
        sub = loader.df_cea[loader.df_cea['cluster'] == cluster_id].iloc[0]
        n_scope       = int(sub['n'] * scope)
        annual_cost   = sub['avg_annual_cost']
        dropout_rate  = 1 - sub['adherence_rate']

        baseline_wasted  = annual_cost * dropout_rate * n_scope
        new_dropout      = dropout_rate * (1 - reduction)
        new_wasted       = annual_cost * new_dropout * n_scope
        waste_recovered  = baseline_wasted - new_wasted
        i_cost           = interv_cost * n_scope
        net_saving       = waste_recovered - i_cost

        total_net   += net_saving
        total_waste += waste_recovered
        total_interv+= i_cost

        segments_out.append({
            "cluster": cluster_id,
            "label": sub['segment'],
            "n_in_scope": n_scope,
            "baseline_dropout_rate": round(dropout_rate, 4),
            "new_dropout_rate": round(new_dropout, 4),
            "baseline_wasted_spend": round(baseline_wasted),
            "waste_recovered": round(waste_recovered),
            "intervention_cost": round(i_cost),
            "net_saving": round(net_saving),
            "roi_positive": net_saving > 0,
        })

    # Break-even: month where cumulative saving exceeds upfront cost
    monthly_saving = total_waste / 12
    break_even = (ceil(total_interv / monthly_saving)
                  if monthly_saving > 0 and total_net > 0 else None)

    return {"total_net_saving": round(total_net), ...}
```

---

### GET /api/shap/global

**Purpose:** Global SHAP drivers for Executive Summary — mean absolute impact per feature

**Response shape:**
```json
{
  "drivers": [
    {"feature": "Provider & pharmacy refill reliability", "importance": 0.541},
    {"feature": "Financial pressure relative to income",  "importance": 0.162},
    {"feature": "Blood sugar control (HbA1c)",            "importance": 0.081},
    "..."
  ]
}
```

**Implementation notes:**
- `mean_abs_shap = np.abs(shap_values).mean(axis=0)`
- Map feature indices to FEATURE_LABELS (same dict as notebook)
- Sort descending
- Computed once at startup, cached

---

### GET /api/model/info

**Purpose:** Settings page — model performance metrics and metadata

**Response shape:**
```json
{
  "name": "GradientBoostingClassifier v2",
  "params": "n_estimators=200, lr=0.05, max_depth=4, max_features=sqrt",
  "threshold": 0.48,
  "train_size": 6052,
  "test_size": 1514,
  "metrics": {
    "accuracy": 0.791,
    "precision": 0.876,
    "recall": 0.646,
    "f1": 0.744,
    "auc_roc": 0.879
  },
  "last_trained": "May 2026",
  "feature_count": 17,
  "features": ["RIDAGEYR", "gender_female", "BMXBMI", "..."]
}
```

**Implementation notes:**
- `threshold` and `features` extracted directly from `model_pkg` (the pickle contains these)
- Accuracy/precision/recall/F1/AUC are static values from the notebook — hardcode as constants in `info.py` or store in a metadata JSON file alongside the pickle

---

## 6. Frontend Integration — What Changes in the React Code

The mock data file is replaced by an API client module. Nothing else in the component tree changes — all screens already use the mock data shapes, which match the API responses exactly.

### Step 1 — Create API client

```javascript
// src/data/api.js — replaces mockData.js imports for live data

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function get(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API ${path} returned ${res.status}`);
  return res.json();
}

async function post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API ${path} returned ${res.status}`);
  return res.json();
}

export const api = {
  getSummary:          ()           => get("/api/summary"),
  getPatients:         (params)     => get("/api/patients?" + new URLSearchParams(params)),
  getPatient:          (id)         => get(`/api/patients/${id}`),
  getSegments:         ()           => get("/api/segments"),
  getSegment:          (id)         => get(`/api/segments/${id}`),
  getSurvival:         ()           => get("/api/survival"),
  getCostEffectiveness:()           => get("/api/cost-effectiveness"),
  getBudgetImpact:     (body)       => post("/api/budget-impact", body),
  getGlobalSHAP:       ()           => get("/api/shap/global"),
  getModelInfo:        ()           => get("/api/model/info"),
};
```

### Step 2 — Create a data hook per screen

Each screen gets a `useQuery`-style hook that handles loading, error, and caching. Example:

```javascript
// src/hooks/useSummary.js
import { useState, useEffect } from "react";
import { api } from "../data/api";

export function useSummary() {
  const [data, setData]     = useState(null);
  const [loading, setLoad]  = useState(true);
  const [error, setError]   = useState(null);

  useEffect(() => {
    api.getSummary()
      .then(setData)
      .catch(setError)
      .finally(() => setLoad(false));
  }, []);

  return { data, loading, error };
}
```

Create the same pattern for: `usePatients`, `usePatient`, `useSegments`, `useSurvival`, `useCostEffectiveness`, `useModelInfo`.

Budget impact is different — it's triggered by slider changes, not on mount:

```javascript
// src/hooks/useBudgetImpact.js
import { useState, useCallback } from "react";
import { api } from "../data/api";
import { calcBudgetImpact } from "../data/mockData"; // fallback

export function useBudgetImpact() {
  const [result, setResult]   = useState(null);
  const [loading, setLoading] = useState(false);

  const calculate = useCallback(async (params) => {
    setLoading(true);
    try {
      const data = await api.getBudgetImpact(params);
      setResult(data);
    } catch {
      // Fallback to client-side calculation if backend unavailable
      setResult(buildFromLocal(params));
    } finally {
      setLoading(false);
    }
  }, []);

  return { result, loading, calculate };
}
```

### Step 3 — Add loading skeletons

Add a `<LoadingSkeleton>` component that renders grey shimmer boxes in the shape of the real content. Show it when `loading === true` in each hook. This prevents layout shift and signals to the user that data is being fetched.

```jsx
// src/components/shared/LoadingSkeleton.jsx
export function SkeletonCard({ h = 120 }) {
  return (
    <div className="card overflow-hidden" style={{ height: h }}>
      <div className="animate-pulse bg-gray-100 w-full h-full" />
    </div>
  );
}

export function SkeletonTable({ rows = 5 }) {
  return (
    <div className="card p-4 space-y-3">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="h-8 bg-gray-100 rounded animate-pulse" style={{ animationDelay: `${i * 0.05}s` }} />
      ))}
    </div>
  );
}
```

### Step 4 — Add error boundaries

Wrap each screen in an `<ErrorBoundary>` component so a failed API call doesn't crash the entire app:

```jsx
// src/components/shared/ErrorBoundary.jsx
import { Component } from "react";

export class ErrorBoundary extends Component {
  state = { error: null };
  static getDerivedStateFromError(e) { return { error: e }; }
  render() {
    if (this.state.error) return (
      <div className="card p-6 text-center text-sm text-red-600">
        <div className="font-semibold mb-1">Failed to load this section</div>
        <div className="text-xs text-gray-500">{this.state.error.message}</div>
        <button onClick={() => this.setState({ error: null })}
          className="mt-3 text-xs text-blue-600 underline">Retry</button>
      </div>
    );
    return this.props.children;
  }
}
```

### Step 5 — Environment variable

```bash
# .env (frontend)
VITE_API_URL=http://localhost:8000

# .env.production
VITE_API_URL=https://your-deployed-api.com
```

### Step 6 — Screen-by-screen swap

Replace mock data imports one screen at a time and verify each before moving to the next. Suggested order:

1. **Settings** — `/api/model/info` (simplest, no user interaction)
2. **Executive Summary** — `/api/summary` (static aggregates)
3. **Segment Explorer** — `/api/segments`
4. **Survival Analysis** — `/api/survival`
5. **Cost-Effectiveness** — `/api/cost-effectiveness`
6. **Patient Risk Panel** — `/api/patients` (pagination + filtering)
7. **Patient Detail** — `/api/patients/{id}`
8. **Budget Simulator** — `/api/budget-impact` (POST, live recalculation)

---

## 7. CORS Configuration

The frontend runs on `localhost:5173` (dev) and the API on `localhost:8000`. Without CORS headers the browser will block every API call.

```python
# Already in main.py above — verify these origins match your setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",    # Vite dev server
        "http://localhost:4173",    # Vite preview
        "https://your-domain.com",  # Production frontend URL
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
```

---

## 8. Pydantic Response Models

Define strict response models so FastAPI validates and documents every response automatically. Example for patients:

```python
# schemas/patients.py
from pydantic import BaseModel
from typing import Optional, List

class PatientRow(BaseModel):
    patient_idx: int
    dropout_prob: float
    prediction: str
    cluster: int
    segment: str
    assigned_molecule: str
    avg_oop_cost: float
    driver_1: str
    driver_1_direction: str
    driver_2: Optional[str] = None
    driver_2_direction: Optional[str] = None
    driver_3: Optional[str] = None
    driver_3_direction: Optional[str] = None
    BMXBMI: float
    RIDAGEYR: int

class PatientSummary(BaseModel):
    high_risk_count: int
    financial_barrier_count: int

class PatientsResponse(BaseModel):
    total: int
    page: int
    page_size: int
    patients: List[PatientRow]
    summary: PatientSummary
```

Define similar models for every response. FastAPI uses these to generate the `/docs` Swagger UI automatically — useful for frontend debugging.

---

## 9. Build Order

Build in this sequence to keep the frontend unblocked throughout:

### Days 1–2 — Scaffold + Static Endpoints
- FastAPI project scaffold with folder structure
- `core/loader.py` + `core/config.py` + `core/model.py`
- `main.py` with CORS and lifespan
- `/api/model/info` endpoint (hardcoded metrics)
- `/api/summary` endpoint (aggregates from df_main)
- `/api/segments` and `/api/segments/{id}`
- Test with `curl` and the `/docs` Swagger UI

### Days 3–4 — Analytical Endpoints
- `/api/survival` — refit KM curves at startup, expose data
- `/api/cost-effectiveness` — load from CSVs
- `/api/shap/global` — compute from shap_values_test.npy

### Day 5 — Patient Endpoints
- `/api/patients` with full pagination + filtering + sorting
- `/api/patients/{id}` with SHAP join

### Day 6 — Dynamic Endpoint
- `/api/budget-impact` POST — full recalculation logic
- Validate against notebook Cell 58 results with default parameters

### Days 7–8 — Frontend Integration
- Create `src/data/api.js`
- Create one hook per screen
- Swap screens in order (Settings → Summary → … → Budget)
- Add loading skeletons
- Add error boundaries

### Day 9 — QA & Polish
- Test all 8 screens with real data
- Verify budget simulator live-update speed (<200ms round-trip on local)
- Test edge cases: patient not in SHAP set, API timeout fallback
- Cross-origin check: ensure production CORS origins are configured

### Day 10 — Documentation & Handoff
- Update `/docs` Swagger descriptions for all endpoints
- Document data directory setup in README
- Record any data shape mismatches between notebook output and API response

---

## 10. Key Integration Risks

**Risk 1: patient_idx alignment between df_main and df_shap**
The SHAP values were computed only on the test set (1,514 patients). The full dataset has 7,566 patients. Patients in the training set won't have SHAP driver records. The `/api/patients/{id}` endpoint must handle this gracefully — return the patient's clinical data but set `shap_drivers: null` with an explanatory note. The Patient Detail screen already conditionally renders SHAP cards so this will not break the UI.

**Risk 2: system_refill_score direction anomaly**
Documented in the limitations. When displaying feature importance from SHAP in the global summary, the negative correlation (higher score = lower adherence) may confuse clinical readers. Add a note in the `/api/shap/global` response: `"direction_note": "system_refill_score shows negative correlation with adherence — interpret as lower reliability being associated with higher dropout"`.

**Risk 3: Budget impact calculation drift**
The frontend mock uses hardcoded base values. The backend recalculates from `df_cea` which comes from the notebook output. If the notebook was re-run with different parameters between the dashboard build and backend build, numbers will differ. Lock the notebook output CSVs and model pkl to a specific run before backend integration begins.

**Risk 4: KM curve data volume**
36 data points × 4 segments = 144 records per API call. Fine for the dashboard. If performance becomes an issue, cache the KM response at startup and serve it as a static dict rather than reserializing on every request.

**Risk 5: SHAP recomputation time**
`shap_values_test.npy` was pre-saved in the notebook. The backend loads it directly — do not attempt to recompute SHAP values per request. Recomputing SHAP for a single patient takes ~200ms with TreeExplainer on a GBM; recomputing for the full test set takes 30–60 seconds. Always serve from the pre-saved array.

---

*This document covers the complete backend build and frontend swap-in. Combined with the frontend plan, this is the full-stack specification for the GLP-1 Analytics Platform.*
