# Preventra — Consequence Model Expansion
## Implementation Plan: Downstream Cost, Rebound Risk & Payer ROI

**Version:** 1.0  
**Prepared for:** Denovonet / Preventra  
**Author:** Internal — Planning Reference  
**Base build at time of writing:** MVP complete (Weeks 3–4). FastAPI backend live, 8-screen React dashboard, synthetic adherence labels, post-SHAP pipeline operational.

---

## Context & Problem Statement

The current Preventra MVP answers one question well: *who is likely to drop off GLP-1 therapy, and why?* The model predicts adherence, segments patients into four risk clusters, and provides per-patient SHAP-driven explanations.

What it does not answer is the question insurers actually budget around: *what does dropout cost us, and is the drug worth it?*

This plan adds a consequence layer on top of the existing prediction layer. Three analytical modules compose it:

1. **Downstream Cost Model** — the medical spend a payer absorbs when a patient drops out and their condition progresses (diabetes complications, CKD, dialysis).
2. **Metabolic Rebound Risk Engine** — the probability that a given patient tips into worsened or new-onset T2D after stopping GLP-1 therapy, given their baseline HbA1c, BMI, and predicted dropout timing.
3. **Payer ROI Synthesizer** — a per-segment net value calculation combining drug cost, adherence probability, avoided downstream spend, and intervention program cost into a single decision-ready number.

Together these form a new pipeline layer and a new dashboard screen: **"Cost of Inaction."**

---

## Dependency Map — Existing Pipeline Integration

```
Existing outputs consumed by this expansion:
─────────────────────────────────────────────────────────
GLP1_CLEANED.csv              → patient baselines (HbA1c, BMI, income_cost_pressure)
GLP1_SEGMENTED.csv            → cluster labels per patient
GLP1_FINAL_WITH_SURVIVAL.csv  → per-patient time_to_dropout, event flag
survival_checkpoints.csv      → 30/60/90/180-day dropout rates per cluster
cost_effectiveness.csv        → existing CEA outputs (ICER, wasted spend)
budget_impact.csv             → existing 15% dropout reduction model
final_gb_model.pkl            → adherence probability scores
─────────────────────────────────────────────────────────

New outputs this plan produces:
─────────────────────────────────────────────────────────
rebound_risk.csv              → per-patient metabolic rebound probability
progression_cost.csv          → per-patient projected downstream medical spend
payer_roi.csv                 → per-segment ROI, break-even, NPV
consequence_model.pkl         → serialized Markov transition matrices + params
─────────────────────────────────────────────────────────
```

---

## Phases Overview

| Phase | Title | Duration | Output |
|---|---|---|---|
| 0 | Foundation & Evidence Audit | Week 1 | Evidence table, parameter registry |
| 1 | Downstream Cost Model | Weeks 2–3 | `progression_cost.csv`, backend endpoint |
| 2 | Metabolic Rebound Risk Engine | Weeks 4–5 | `rebound_risk.csv`, backend endpoint |
| 3 | Payer ROI Synthesizer | Week 6 | `payer_roi.csv`, backend endpoint |
| 4 | Dashboard Integration | Weeks 7–8 | New "Cost of Inaction" screen in React |
| 5 | Validation & Documentation | Week 9 | Updated data docs, limitation registry |

Total timeline: **9 weeks** from kickoff to a documented, demo-ready build.

---

## Phase 0 — Foundation & Evidence Audit
**Duration: Week 1**

### Problem

Every number in the consequence model will be challenged by any technically literate insurer or pharma partner. The downstream cost estimates, progression probabilities, and rebound rates all need defensible published sources — not internal assumptions.

### Tasks

**0.1 — Assemble the parameter registry**

Create `evidence/parameter_registry.csv` as the single source of truth for every hardcoded clinical value in the consequence model. Each row captures:

| Field | Description |
|---|---|
| `parameter_name` | e.g., `esrd_annual_cost_usd` |
| `value` | 92,000 |
| `unit` | USD/year |
| `source` | USRDS 2023 Annual Data Report |
| `source_url` | https://usrds-adr.niddk.nih.gov |
| `year` | 2023 |
| `notes` | Medicare fee-for-service ESRD patients, US average |

Minimum parameters to populate in Week 1:

- Annual cost of uncontrolled T2D management (AHRQ, ADA Economic Standards)
- Annual ESRD / dialysis cost (USRDS Annual Data Report)
- Diabetic nephropathy CKD stage transition probabilities per HbA1c range (published Markov models in *Diabetes Care* or *JASN*)
- Cardiovascular event cost per incident (CMS inpatient claims literature)
- HbA1c rebound rate post-GLP-1 discontinuation (SUSTAIN extension trial data, STEP extension)
- BMI rebound rate post-discontinuation (same trials)
- T2D incidence rate for pre-diabetic patients by HbA1c range (DPP trial, NHANES follow-up)

**0.2 — Audit the existing CEA engine**

Before building on top of `cost_effectiveness.csv`, verify:
- Do the per-cluster `avg_annual_cost` values align with published GLP-1 wholesale acquisition costs?
- Is the 15% dropout reduction assumption in `budget_impact.csv` sourced or assumed? Flag if assumed.
- Confirm `time_to_dropout` exponential lambda values are defensible given the cluster adherence rates.

Produce a one-page audit memo (`evidence/cea_audit.md`) with pass/flag/fail per item.

**0.3 — Scope the Markov model**

Decide on CKD staging granularity:
- **Option A (simple):** Two-state model — controlled vs. uncontrolled T2D. Faster to build, easier to explain.
- **Option B (full):** Five-state Markov chain — Pre-DM → T2D → CKD3 → CKD4/5 → ESRD. More accurate for long-horizon ROI, requires more sourced transition probabilities.

Recommendation: implement Option A for Phase 1 delivery, build Option B in parallel as a configurable upgrade. Document the choice.

### Deliverables
- `evidence/parameter_registry.csv` — populated, sourced
- `evidence/cea_audit.md` — CEA engine audit
- `evidence/markov_scope_decision.md` — staging decision with rationale

---

## Phase 1 — Downstream Cost Model
**Duration: Weeks 2–3**

### Problem

When a patient drops out, the payer's liability does not end — it shifts from drug cost to complication management. Preventra currently shows "wasted spend" on the drug itself. It does not show what the payer pays *next*.

### Architecture

The Downstream Cost Model is a **Markov state transition model** applied per patient, parameterized by that patient's baseline HbA1c, BMI, diabetes diagnosis status, and predicted dropout timing from the KM survival layer.

```
Patient state at dropout → Transition matrix × years at risk → Expected future cost
```

**States (Option A — recommended for v1):**
- S0: Controlled glycemia (HbA1c < 7.0, on therapy or well-managed off)
- S1: Uncontrolled T2D (HbA1c ≥ 7.0, off therapy)
- S2: CKD / nephropathy (elevated creatinine, proteinuria)
- S3: ESRD / dialysis
- S4: CV event (non-fatal MI, stroke)
- S_absorb: Death / out of model

Transition probabilities are sourced from the parameter registry (Phase 0).

### Implementation

**Script: `Model/consequence/downstream_cost.py`**

```
Inputs:
  GLP1_FINAL_WITH_SURVIVAL.csv   (time_to_dropout, cluster, HbA1c, BMI)
  GLP1_SEGMENTED.csv             (cluster label)
  evidence/parameter_registry.csv

Process:
  1. For each patient, determine entry state at dropout based on LBXGH:
       LBXGH < 5.7  → Low risk (pre-DM, unlikely to progress fast)
       5.7 ≤ LBXGH < 6.5 → Pre-DM state
       LBXGH ≥ 6.5  → T2D state at dropout
  2. Run discrete Markov chain forward for a configurable time horizon
     (default 5 years; 10 years as sensitivity analysis)
  3. Weight state occupancy by state-specific annual cost from registry
  4. Produce per-patient: expected_downstream_cost_5yr, expected_downstream_cost_10yr
  5. Discount at 3% annual rate (standard health economics convention)

Outputs:
  progression_cost.csv
    columns: patient_id, cluster, lbxgh_baseline, bmxbmi_baseline,
             time_to_dropout_days, entry_state, 
             expected_downstream_cost_5yr, expected_downstream_cost_10yr,
             esrd_probability_5yr, cv_event_probability_5yr,
             primary_cost_driver (ESRD / CV / Uncontrolled_T2D)
```

**Validation check:** Aggregate expected downstream cost per cluster. "Financial Barrier Dropout Risk" cluster should show the highest downstream burden — these are high-HbA1c patients dropping early due to cost. If another cluster ranks higher, inspect the transition probabilities and entry state logic.

### Backend Endpoint

`GET /api/consequence/downstream-cost`

Response schema:
```json
{
  "by_cluster": [
    {
      "cluster_id": 1,
      "cluster_label": "Financial Barrier Dropout Risk",
      "avg_downstream_cost_5yr": 42800,
      "avg_downstream_cost_10yr": 89300,
      "esrd_probability_5yr": 0.14,
      "cv_event_probability_5yr": 0.22,
      "n_patients": 1843
    }
  ],
  "population_total_5yr": 187400000,
  "primary_cost_driver_distribution": {
    "ESRD": 0.31,
    "CV_event": 0.44,
    "Uncontrolled_T2D": 0.25
  }
}
```

### Deliverables
- `Model/consequence/downstream_cost.py`
- `progression_cost.csv`
- FastAPI endpoint registered and tested
- Unit tests for Markov transition logic

---

## Phase 2 — Metabolic Rebound Risk Engine
**Duration: Weeks 4–5**

### Problem

GLP-1 therapy suppresses appetite, improves insulin sensitivity, and reduces HbA1c. Discontinuation reverses these effects within weeks. For pre-diabetic patients, dropping out may mean crossing the T2D threshold. For diabetic patients, glycemic control collapses. The existing pipeline has no mechanism to quantify this risk per patient.

### Data Inputs

Published evidence (to be sourced in Phase 0) provides:
- Mean HbA1c increase per month post-discontinuation (from SUSTAIN-1 and STEP-1 extension arms)
- Mean BMI increase per month post-discontinuation (same trials)
- T2D incidence rate for pre-diabetic patients by HbA1c stratum (DPP trial 10-year follow-up)

These are not derived from your data — they are sourced parameters applied to your patient population.

### Architecture

```
Per patient:
  1. Determine baseline risk stratum from LBXGH at time of dropout
  2. Apply time-varying HbA1c rebound trajectory using published monthly increment
  3. Estimate months until HbA1c crosses T2D threshold (6.5%) for pre-DM patients
  4. For T2D patients: estimate months until HbA1c exceeds uncontrolled threshold (8.0%)
  5. Compute:
       - p_new_t2d_12mo    (for pre-DM patients only)
       - p_uncontrolled_12mo (for T2D patients)
       - expected_hba1c_at_6mo, expected_hba1c_at_12mo
       - rebound_severity_score (0–1 composite)
```

**Script: `Model/consequence/rebound_risk.py`**

```
Inputs:
  GLP1_FINAL_WITH_SURVIVAL.csv
  evidence/parameter_registry.csv

Outputs:
  rebound_risk.csv
    columns: patient_id, cluster, lbxgh_baseline, dm_status_at_dropout,
             expected_hba1c_6mo, expected_hba1c_12mo,
             p_new_t2d_12mo, p_uncontrolled_12mo,
             months_to_t2d_threshold (nullable — only for pre-DM),
             rebound_severity_score
```

### Sensitivity Analysis

Run rebound projections under three dropout timing scenarios using the KM checkpoint data:
- Early dropout (day 30 — from `survival_checkpoints.csv`)
- Median dropout (cluster median from KM)
- Late dropout (day 150)

This shows that a patient who drops at day 30 has a meaningfully different rebound trajectory than one who persists to day 150, giving the insurer a rationale for early intervention programs.

### Backend Endpoint

`GET /api/consequence/rebound-risk`

Response includes per-cluster rebound severity, population-level T2D incidence projection, and the sensitivity analysis trio.

### Limitation to Document

The rebound trajectory is derived from published trial populations (predominantly European, controlled clinical settings). Your NHANES-seeded patient population differs demographically. Flag this explicitly in the model documentation — the rebound rates are directionally correct but not calibrated to your specific population.

### Deliverables
- `Model/consequence/rebound_risk.py`
- `rebound_risk.csv`
- FastAPI endpoint
- Sensitivity analysis output
- Limitation added to `DATA_AND_MODEL_DOCUMENTATION.md`

---

## Phase 3 — Payer ROI Synthesizer
**Duration: Week 6**

### Problem

The existing `budget_impact.csv` estimates net savings from a 15% dropout reduction at $500/patient intervention cost. This is useful directionally but rests on a flat assumption. The ROI Synthesizer replaces that flat assumption with model-derived adherence probabilities and consequence model outputs, producing a per-segment ROI that an insurer can stress-test.

### Formula

```
For each cluster c:

  drug_cost_per_patient     = avg_annual_glp1_cost (from CEA engine, per molecule mix)
  adherence_probability     = cluster adherence rate from GLP1_SEGMENTED.csv
  downstream_cost_if_dropout = avg_downstream_cost_5yr from progression_cost.csv
  downstream_cost_if_adherent = avg_downstream_cost_5yr (reduced, from trial efficacy data)
  
  expected_downstream_cost  = (1 - adherence_probability) × downstream_cost_if_dropout
                            + adherence_probability × downstream_cost_if_adherent

  gross_benefit             = downstream_cost_if_dropout - expected_downstream_cost
  net_benefit_per_patient   = gross_benefit - drug_cost_per_patient
  
  ROI                       = net_benefit_per_patient / drug_cost_per_patient
  
  break_even_adherence_rate = drug_cost / (downstream_cost_if_dropout - downstream_cost_if_adherent)
```

Apply a 3% annual discount rate for multi-year projections. Run at 1-year, 3-year, and 5-year horizons.

**Script: `Model/consequence/payer_roi.py`**

```
Inputs:
  GLP1_SEGMENTED.csv
  progression_cost.csv
  rebound_risk.csv
  cost_effectiveness.csv (existing CEA outputs)
  evidence/parameter_registry.csv

Outputs:
  payer_roi.csv
    columns: cluster_id, cluster_label, n_patients, 
             adherence_probability, avg_drug_cost_annual,
             expected_downstream_cost_5yr, gross_benefit_5yr,
             net_benefit_per_patient_5yr, roi_5yr,
             break_even_adherence_rate,
             intervention_cost_threshold (max spend per patient to remain ROI positive)
```

### Intervention Cost Threshold

This is the number the insurer wants: *how much can we spend on case management, copay assistance, or adherence programs per patient before the ROI goes negative?* Compute per cluster:

```
intervention_cost_threshold = gross_benefit - drug_cost
```

For "Financial Barrier Dropout Risk" patients, where downstream cost is highest and adherence is lowest, this threshold will be the largest — directly supporting the case that targeted copay assistance programs pay for themselves.

### Backend Endpoint

`GET /api/consequence/payer-roi`

Response:
```json
{
  "by_cluster": [
    {
      "cluster_label": "Financial Barrier Dropout Risk",
      "roi_1yr": -0.31,
      "roi_5yr": 2.14,
      "break_even_adherence_rate": 0.58,
      "intervention_cost_threshold_per_patient": 6200
    }
  ],
  "population_roi_5yr": 1.87,
  "time_to_positive_roi_years": 2.3
}
```

Note that 1-year ROI will likely be negative for most clusters — GLP-1 drugs are expensive and complication avoidance accrues over years. This is expected and should be framed proactively in the dashboard: the drug is a long-horizon investment, not a 12-month cost center.

### Deliverables
- `Model/consequence/payer_roi.py`
- `payer_roi.csv`
- FastAPI endpoint
- 1/3/5-year sensitivity outputs

---

## Phase 4 — Dashboard Integration
**Duration: Weeks 7–8**

### New Screen: "Cost of Inaction"

Add a ninth screen to the React dashboard, accessible from the Insurer role sidebar. The screen has three panels corresponding to the three modules.

**Panel 1 — Downstream Cost (Week 7, first half)**

- Stacked bar chart: per-cluster expected downstream cost breakdown by cost driver (ESRD, CV event, uncontrolled T2D) — rendered with Recharts `BarChart` with stacking
- Metric cards: population total 5-year downstream exposure, average cost per dropout
- Toggle: 5-year / 10-year horizon

**Panel 2 — Rebound Risk (Week 7, second half)**

- Line chart: projected HbA1c trajectory post-dropout for each cluster over 12 months (four lines, one per cluster, x-axis = months post-dropout, y-axis = expected HbA1c)
- Risk gauge cards: per-cluster rebound severity score (color-coded — green < 0.3, amber 0.3–0.6, red > 0.6)
- Sensitivity toggle: early / median / late dropout timing

**Panel 3 — Payer ROI (Week 8)**

- Grouped bar chart: ROI at 1/3/5 years per cluster
- Break-even line displayed on chart (horizontal reference line at ROI = 0)
- Intervention budget calculator: interactive slider — insurer enters planned intervention spend per patient, dashboard updates net ROI in real time
- Highlight card: "Maximum intervention spend before ROI goes negative" per cluster

**Component structure:**

```
src/
  screens/
    ConsequenceModel/
      index.jsx                  ← screen root, tab navigation
      DownstreamCostPanel.jsx
      ReboundRiskPanel.jsx
      PayerROIPanel.jsx
      components/
        InterventionBudgetSlider.jsx
        ReboundTrajectoryChart.jsx
        ROIBarChart.jsx
        CostDriverStackedBar.jsx
  api/
    consequenceApi.js            ← fetch wrappers for three new endpoints
```

**API integration:** All three panels fetch from the three new FastAPI endpoints established in Phases 1–3. Loading states and error boundaries follow the existing pattern in the dashboard.

### Deliverables
- Three new React components, production-quality (Tailwind + Recharts)
- `consequenceApi.js` integration layer
- Screen registered in role-based routing (Insurer view only)
- Responsive layout matching existing dashboard design system

---

## Phase 5 — Validation & Documentation
**Duration: Week 9**

### Tasks

**5.1 — End-to-end sanity checks**

Run the full consequence pipeline from `GLP1_FINAL_WITH_SURVIVAL.csv` through to `payer_roi.csv` and verify:

- "Financial Barrier Dropout Risk" cluster has the highest downstream cost and the highest intervention cost threshold (directional sense check)
- "Low Friction Strong Adherer" cluster shows positive ROI at 3 years (they stay on the drug; downstream cost is lower)
- Population-level 5-year downstream exposure figure is in a plausible range given cluster sizes and published T2D complication rates
- No cluster shows ROI > 10× at 5 years (if so, inspect parameter registry for mis-sourced cost estimates)

**5.2 — Update `DATA_AND_MODEL_DOCUMENTATION.md`**

Add Section 10: Consequence Model Layer, covering:
- Architecture overview (how the three modules connect)
- All hardcoded parameters with sources (link to `parameter_registry.csv`)
- New known limitations:
  - Rebound trajectory sourced from trial populations, not validated against your NHANES cohort
  - Markov transition probabilities are population-level averages, not patient-specific
  - Long-horizon projections (10-year) are illustrative; uncertainty compounds significantly beyond 5 years
  - Dialysis cost estimate is Medicare fee-for-service; commercial insurance costs may differ

**5.3 — Demo script update**

Update the existing Insurer demo flow to route through the new "Cost of Inaction" screen. Suggested talking track:

1. Open the Adherence Risk screen — "Here's who is at risk of dropping out, by segment."
2. Click through to the new screen — "Here's what happens to your budget when they do."
3. Use the intervention slider on the ROI panel — "Here's the maximum you can spend on a support program before it stops paying off."

**5.4 — Stakeholder briefing note**

One-page internal memo for the verbal manager briefing: what was built, what the numbers mean, what the next data milestone is (real prescription fill data to replace synthetic labels).

### Deliverables
- Sanity check report (`evidence/validation_checks.md`)
- Updated `DATA_AND_MODEL_DOCUMENTATION.md`
- Updated demo script
- Stakeholder briefing note

---

## Timeline Summary

```
Week 1   ████████  Phase 0 — Evidence audit, parameter registry, Markov scope
Week 2   ████████  Phase 1 — Downstream cost model (Markov logic + CSV output)
Week 3   ████████  Phase 1 — Backend endpoint, unit tests, validation
Week 4   ████████  Phase 2 — Rebound risk engine (trajectory + probability outputs)
Week 5   ████████  Phase 2 — Sensitivity analysis, endpoint, limitation docs
Week 6   ████████  Phase 3 — Payer ROI synthesizer, break-even, intervention threshold
Week 7   ████████  Phase 4 — Dashboard: Downstream Cost + Rebound Risk panels
Week 8   ████████  Phase 4 — Dashboard: Payer ROI panel + intervention slider
Week 9   ████████  Phase 5 — Validation, documentation, demo script, briefing note
```

---

## Open Questions to Resolve Before Phase 1 Starts

1. **Markov horizon:** Default to 5 years in v1? Or does the insurer persona think in 3-year budget cycles? This affects which ROI number gets top billing in the dashboard.

2. **Commercial vs. Medicare cost estimates:** USRDS data is Medicare-based. If Preventra's target insurers are commercial payers, the dialysis cost figure needs a commercial claims source (Milliman, HCCI). Confirm target payer type.

3. **Discount rate:** 3% is standard health economics convention (US Panel on Cost-Effectiveness). Confirm this is acceptable or whether the insurer persona would prefer an undiscounted figure for simplicity.

4. **Intervention program cost:** The budget impact model uses $500/patient. Is there a preferred figure, or should the ROI panel treat this as a fully user-configurable input (the slider approach proposed in Phase 4)?

5. **Real data timeline:** The consequence model will be more defensible once real prescription fill data replaces the synthetic `is_adherent` label. Does the post-MVP data partnership roadmap (CMS PDE DUA, insurance company partnerships) have a target date? If so, the consequence model should be built to accept real adherence probabilities as a drop-in replacement.

---

## Files This Plan Will Produce

```
evidence/
  parameter_registry.csv
  cea_audit.md
  markov_scope_decision.md
  validation_checks.md

Model/consequence/
  downstream_cost.py
  rebound_risk.py
  payer_roi.py

Data outputs/
  progression_cost.csv
  rebound_risk.csv
  payer_roi.csv
  consequence_model.pkl

Backend/
  routes/consequence.py          ← three new FastAPI routes

Frontend/src/screens/
  ConsequenceModel/
    index.jsx
    DownstreamCostPanel.jsx
    ReboundRiskPanel.jsx
    PayerROIPanel.jsx
    components/ (four chart components)
  api/consequenceApi.js

Documentation/
  DATA_AND_MODEL_DOCUMENTATION.md  ← updated with Section 10
  demo_script_v2.md
  stakeholder_briefing_consequence.md
```
