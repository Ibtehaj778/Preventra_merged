# Consequence Model — Phase 3 Progress (Week 6 Complete)

**Plan reference:** [CONSEQUENCE_MODEL_IMPLEMENTATION_PLAN.md](../CONSEQUENCE_MODEL_IMPLEMENTATION_PLAN.md) §Phase 3
**Status:** Phase 3 complete. Weeks 1–6 of the 9-week plan delivered. Ready to start Phase 4 (Dashboard Integration).

---

## What Phase 3 set out to do

Combine the adherence probability (from Phase 0 outputs), the Markov downstream cost (Phase 1), and per-molecule drug cost into a single decision-ready ROI number per cluster — plus break-even adherence rate, intervention cost threshold, and time-to-positive ROI for the dashboard's Payer ROI panel.

---

## Registry extensions

Added two new sourced rows to [evidence/parameter_registry.csv](../evidence/parameter_registry.csv):

| Parameter | Value | Source | Purpose |
|---|---|---|---|
| `glp1_efficacy_glycemic_progression_rr` | 0.15 | SUSTAIN-6 / LEADER 4-5yr HbA1c trajectory; STEP-5 104-week | Relative risk of S0→S1 transition for on-therapy patients. Without this, the on-therapy Markov reduced only renal/CV transitions and left glycemic progression identical to off-therapy — which was wrong. |
| `glp1_payer_net_rebate_fraction` | 0.35 | SSR Health / IQVIA industry commentary; CRS R47487 | Rough midpoint of 30–40% observed rebate on GLP-1 list prices for commercial payers. Flagged as ASSUMED. Set to 0 for WAC upper-bound sensitivity. |

Both are documented as v1 assumptions in [DATA_AND_MODEL_DOCUMENTATION.md](../DATA_AND_MODEL_DOCUMENTATION.md) §10.4 (limitations 19, 21).

---

## Code added

| File | Purpose |
|---|---|
| [Model/consequence/roi.py](../../Model/consequence/roi.py) | Pure ROI math. `ROIInputs`, `ROIOutput`, `compute_roi`, `annuity_factor`, `expected_drug_cost`, `break_even_adherence`, `time_to_positive_roi`, `population_roi`. No I/O. |
| [Model/consequence/payer_roi.py](../../Model/consequence/payer_roi.py) | Entry script. Runs Markov twice per patient (off-therapy at LBXGH, on-therapy at effective HbA1c), aggregates per cluster, applies ROI formula at horizons 1..5. Writes 2 CSVs. |
| [Model/consequence/markov.py](../../Model/consequence/markov.py) | Extended: new `on_therapy_glycemic_rr` field on `MarkovParams` applied to S0→S1 for on-therapy patients. Backwards-compatible (default 1.0). |
| [Model/consequence/downstream_cost.py](../../Model/consequence/downstream_cost.py) | Wires the new glycemic RR through `build_params`. |
| [Model/consequence/tests/test_roi.py](../../Model/consequence/tests/test_roi.py) | 23 new unit tests. Combined consequence test suite is now **73 tests, all green**. |
| [Backend/schemas/consequence.py](../../Backend/schemas/consequence.py) | Added `PayerROIHorizon`, `PayerROICluster`, `PayerROIResponse`. |
| [Backend/routers/consequence.py](../../Backend/routers/consequence.py) | Added `GET /api/consequence/payer-roi?intervention_cost=<usd>`. Slider drives server-side recompute; no new Mongo writes. |
| [Backend/scripts/migrate_csv_to_mongo.py](../../Backend/scripts/migrate_csv_to_mongo.py) | Added `migrate_payer_roi()` and `migrate_payer_roi_yearly()` with unique indexes. |
| [DATA_AND_MODEL_DOCUMENTATION.md](../DATA_AND_MODEL_DOCUMENTATION.md) | §10.2a Payer ROI Synthesizer section; limitations 19–23. |

---

## ROI model design

### Per-patient rollouts

For each patient the script runs `markov.run_markov` twice:

- **Off-therapy branch:** entry state from raw LBXGH, on_therapy=False. Same math as Phase 1's `progression_cost.csv`.
- **On-therapy branch:** entry state from *effective on-therapy HbA1c* (LBXGH − per-molecule trial reduction, floored at 5.0 as in the rebound model). `on_therapy=True` applies:
  - Renal RR 0.64 to S1→S2 and S2→S3.
  - CV RR 0.74 to CV event hazards.
  - Glycemic RR 0.15 to S0→S1 progression.

Recomputing the entry state on effective HbA1c is what lets the model credit GLP-1 for keeping patients out of S1 entirely — a patient with LBXGH 7.2 has effective on-therapy HbA1c 5.6 and enters S0, not S1. Without this step (my first-pass draft), on-therapy ROI was ~$0 gap and break-even was 5x for the worst cluster.

### Cluster aggregation → ROI formula (per horizon t)

```
expected_downstream(t) = (1 − α)·C_dropout(t) + α·C_adherent(t)
gross_benefit(t)       = C_dropout(t) − expected_downstream(t) = α·(C_dropout(t) − C_adherent(t))
expected_drug_cost(t)  = α·D·annuity(t, r=0.03) + (1 − α)·D·(t_drop/365)
net_benefit(t)         = gross_benefit(t) − expected_drug_cost(t) − intervention_cost
ROI(t)                 = net_benefit(t) / expected_drug_cost(t)
break_even_α           = D_annual / (C_dropout − C_adherent)     (returns None if no positive spread)
intervention_threshold = gross_benefit(5) − expected_drug_cost(5)
```

The drug-cost formula is audit-compliant: dropout-cohort patients only pay for the days they were on therapy (avg cluster `time_to_dropout`), not a full 5-year stream. This was flagged in `cea_audit.md` §D as a required change from the existing `wasted_spend_per_pt` semantics.

---

## Outputs

| File | Rows | Purpose |
|---|---|---|
| [Backend/data/payer_roi.csv](../../Backend/data/payer_roi.csv) | 4 | Per-cluster wide format. All horizons in one row. |
| [Backend/data/payer_roi_yearly.csv](../../Backend/data/payer_roi_yearly.csv) | 20 | Per-cluster × year long format. Powers the dashboard time-to-positive line chart. |

---

## Sanity check — per-cluster ROI (intervention = $500/patient)

```
cluster  adherence  annual_drug   roi_1yr  roi_3yr  roi_5yr  break_even_α  interv_threshold_5yr
   0     0.208      $7,066         -1.15    -1.06    -1.02    5.03           −$8,284
   1     0.308      $7,575         -1.00    -0.84    -0.76    0.65           −$9,271
   2     0.854      $10,490        -0.96    -0.89    -0.86    1.37           −$36,463
   3     0.406      $5,850         -0.99    -0.82    -0.72    0.60           −$8,608

Population-weighted 5-yr ROI: -0.847
```

### Reading the table

**All clusters show negative 5-yr ROI on pure cost avoidance.** This is not a bug — it's consistent with the published health-economic view of GLP-1s. Real-world value comes from QALY gains (typically ~$50k/QALY cost-effective, well below the $150k WTP threshold), 10–15 year complication avoidance, and mortality reduction. The plan explicitly anticipated negative 1-year ROI ("the drug is a long-horizon investment, not a 12-month cost center"). The Phase 3 numbers extend that finding to 5 years, which is longer than the plan's illustrative example predicted but is what the actual math yields under conservative, sourced parameters.

**Cluster 3 (Moderate Risk Moderate Adherer) is closest to break-even (0.60).** These patients have moderately-elevated HbA1c (mean 6.55), moderate adherence (0.41), and cheaper drug mix ($5,850/yr net). If a targeted intervention could lift their adherence from 0.41 → 0.60, the program breaks even at 5 years.

**Cluster 1 (Financial Barrier Dropout Risk) has break-even 0.65 vs. current 0.31 adherence.** This is the direct payer message: closing a 34-point adherence gap flips this cluster from a loss to break-even. The intervention_cost_threshold (−$9,271) says any spend up to $9k/patient beyond drug cost stays within the same negative-ROI envelope; the goal is not to spend more but to lift the α term.

**Cluster 2 (Low Friction Strong Adherer) has break-even 1.37 — unreachable.** Even at 100% adherence, the on-therapy cost savings for this already-low-HbA1c cluster don't cover the drug. Interpretation: for a Cluster 2 patient the drug's value is elsewhere (weight loss, satisfaction, prevention) — not cost avoidance in the payer's own claims data. The dashboard should be explicit about this.

**Cluster 0 (Low Urgency Dropout Risk) has break-even 5.03 — the drug is clinically the wrong tool.** These are baseline-normal-HbA1c patients (mean 5.35) unlikely to progress to expensive complications; GLP-1 doesn't save meaningful downstream cost because there's little downstream cost to save. Real-world payers would apply prior authorization to filter these patients out; the dashboard should surface this cluster as a candidate for de-prescription or non-approval.

**None of the clusters reach positive ROI within the 1..5-year window.** `time_to_positive_roi_years` is None for all four. A 10-year sensitivity would probably show clusters 1 and 3 crossing to positive; that's a v2 extension.

---

## Backend endpoint — `GET /api/consequence/payer-roi`

Response shape (abridged, intervention_cost=500):

```json
{
  "by_cluster": [
    {
      "cluster_id": 1,
      "cluster_label": "Financial Barrier Dropout Risk",
      "n_patients": 2104,
      "adherence_probability": 0.3085,
      "avg_annual_drug_cost": 7575.16,
      "avg_time_to_dropout_days": 127.46,
      "horizons": [
        {"horizon_years": 1, "expected_drug_cost": 4166.00, "gross_benefit": 516.96, "intervention_cost": 500, "net_benefit": -4149.05, "roi": -0.996},
        {"horizon_years": 3, "expected_drug_cost": 8637.08, "gross_benefit": 1818.87, "intervention_cost": 500, "net_benefit": -7318.22, "roi": -0.847},
        {"horizon_years": 5, "expected_drug_cost": 12851.5, "gross_benefit": 3454.05, "intervention_cost": 500, "net_benefit": -9897.45, "roi": -0.770}
      ],
      "break_even_adherence_rate": 0.6765,
      "intervention_cost_threshold_5yr": -9271.07,
      "time_to_positive_roi_years": null
    }
  ],
  "population_roi_1yr": -0.9835,
  "population_roi_3yr": -0.9147,
  "population_roi_5yr": -0.8477,
  "intervention_cost_per_patient": 500,
  "n_patients_total": 7566
}
```

The `intervention_cost` query param drives server-side recompute of ROI and time-to-positive without persisting new documents — that's the mechanism for the dashboard slider. If the frontend sends `?intervention_cost=1200`, every horizon's `net_benefit` and `roi` are recalculated from the stored `gross_benefit` and `expected_drug_cost`.

Mongo collections consumed: `payer_roi` (per-cluster wide), `payer_roi_yearly` (per-cluster × year long) — used later for the time-to-positive chart.

---

## CSV output reference — field by field

The two CSVs `payer_roi.py` writes are the source of truth for everything downstream (Mongo docs, endpoint response, dashboard). Column-by-column detail:

### `payer_roi.csv` — per-cluster wide format (4 rows initially, 12 after Extension B)

| Column | Type | Source | Meaning |
|---|---|---|---|
| `cluster` | int (0-3) | Segment ID from Phase 1 K-means | Cluster identifier |
| `n_patients` | int | count within cluster | Patient population size |
| `adherence_probability` | float [0,1] | `is_adherent.mean()` per cluster | The α term in ROI math |
| `avg_annual_drug_cost` | USD | `patient_drug_cost_annual` averaged per cluster; per-molecule WAC × (1 − rebate) | The D term. Weighted by patient's assigned molecule. |
| `avg_time_to_dropout_days` | float | patients' `time_to_dropout` averaged | The `t_drop` term used to prorate drug cost for the dropout cohort |
| `downstream_dropout_{1..5,10}yr` | USD | Off-therapy Markov cumulative discounted cost | Per-patient expected downstream spend if patient drops (input to Δ) |
| `downstream_adherent_{1..5,10}yr` | USD | On-therapy Markov (with effective HbA1c + RRs) | Per-patient expected downstream spend if patient stays adherent |
| `gross_benefit_{h}yr` | USD | α × (dropout − adherent) at horizon h | Avoided cost the payer captures at each horizon |
| `expected_drug_cost_{h}yr` | USD | α·D·annuity(h) + (1−α)·D·t_drop/365 | Cumulative discounted per-patient drug spend |
| `intervention_cost_{h}yr` | USD | Passed through as-is (defaulted $500) | The intervention program spend applied at each horizon |
| `net_benefit_{h}yr` | USD | gross − drug − intervention | Payer's per-patient net cash position |
| `roi_{h}yr` | float | net_benefit / expected_drug_cost | ROI ratio — negative means program costs more than it saves |
| `break_even_adherence_rate` | float or null | D_annual / (C_dropout_5yr − C_adherent_5yr) | Minimum α for 1-year drug cost to equal 5-year avoided cost. Null if on-therapy isn't cheaper (unreachable) |
| `intervention_cost_threshold_5yr` | USD | gross_5 − drug_5 (pre-intervention net) | Max intervention spend that keeps 5-yr ROI ≥ 0. Negative means already under water |
| `time_to_positive_roi_years` | float or null | Linear interpolation of yearly ROI series crossing zero | Year at which ROI turns positive; null if never crosses in the horizon window |
| `payer_type` (added in Extension B) | string | `current` / `medicare_2028` / `post_generic` | Which pricing environment produced this row |

### `payer_roi_yearly.csv` — per-cluster × year long format (20 rows initially, 120 after Extensions A + B)

Row per (cluster × horizon_year). Used by the dashboard's ROI trajectory line chart in Panel 3.

| Column | Meaning |
|---|---|
| `cluster` | int 0-3 |
| `horizon_years` | int 1..10 (was 1..5 pre-Extension A) |
| `gross_benefit`, `expected_drug_cost`, `intervention_cost`, `net_benefit`, `roi` | Same definitions as the wide format, at this specific horizon |
| `payer_type` (Extension B) | Same values as wide format |

---

## Frontend integration — how Panel 3 consumes this endpoint

Every field in the `PayerROIResponse` maps to a specific UI element on Panel 3 of the "Cost of Inaction" screen ([Frontend/src/pages/CostOfInaction/PayerROIPanel.jsx](../../Frontend/src/pages/CostOfInaction/PayerROIPanel.jsx)). The mapping:

| Response field | Panel 3 UI element | How it's rendered |
|---|---|---|
| `n_patients_total` | Population summary strip — subtitle text | `${nTotal.toLocaleString()} patients` under the "Population 1-yr ROI" KPI card |
| `population_roi_1yr` | KPI card #1 | `KPICard label="Population 1-yr ROI"` — colour red if negative, green if ≥ 0 |
| `population_roi_3yr` | (Initial Week-8 KPI card, later replaced by population_roi_10yr in Extension A) | — |
| `population_roi_5yr` | KPI card #2 (labeled "Primary payer horizon") | Same KPICard component, red/green by sign |
| `population_roi_10yr` (Extension A) | KPI card #3 (labeled "Sensitivity — long horizon") | Same styling. Under `post_generic` scenario this turns green (+0.48) |
| `intervention_cost_per_patient` | KPI card #4 | Passed through from the slider; shown to remind the user of the current scenario cost |
| `by_cluster[i].cluster_id` + `cluster_label` | Per-cluster card header | Top-left of each of 4 cluster cards; border-top matches `SEGMENT_COLORS[cluster_id]` |
| `by_cluster[i].adherence_probability` | Break-even block on per-cluster card | Rendered inline as "Current: 30.8%" next to the break-even α value |
| `by_cluster[i].avg_annual_drug_cost` | Per-cluster card, bottom-right | Rendered as `fmtMoney` next to "Annual drug cost" label |
| `by_cluster[i].horizons[?horizon_years==1..5].roi` | ROIBarChart series | Recharts `<Bar>` with `dataKey="roi_1yr"` / `_3yr` / `_5yr`. Colour-scaled light → medium → dark blue |
| `by_cluster[i].horizons[?horizon_years==10].roi` (Extension A) | ROIBarChart 4th series + per-cluster 10-yr ROI badge | Dark navy bar; green/red badge on the card |
| `by_cluster[i].horizons[?].gross_benefit`, `.expected_drug_cost` | Per-cluster "10-yr cost-coverage bar" (Extension A) | Client-computed ratio `gross / drug` shown as a horizontal progress bar |
| `by_cluster[i].yearly_roi_series` (Extension A) | ROITrajectoryChart line for that cluster | Recharts `<Line>` with 10 points, one line per cluster |
| `by_cluster[i].break_even_adherence_rate` | "Break-even Adherence" block on per-cluster card | Either shown as a % with gap-to-current, or replaced with "Unreachable" copy when > 1.0 or null |
| `by_cluster[i].intervention_cost_threshold_5yr` | "5-yr headroom" row on per-cluster card | Colour-graded green/red by sign |
| `by_cluster[i].time_to_positive_roi_years` | Not shown as a raw number in v1 — implied by the trajectory chart's crossover point | Reserved for potential future callout marker on the trajectory chart |

### Hook + fetch flow

- Component owns local state: `interventionCost` (from Radix Slider) and `payerType` (from segmented control, Extension B).
- `usePayerROI(interventionCost, payerType)` debounces both inputs at 250 ms and re-fetches `/api/consequence/payer-roi?intervention_cost=<x>&payer_type=<y>`.
- Loading state: `SkeletonCard` / `SkeletonChart` renders while `data === null && loading`. Once the first response lands, subsequent re-fetches keep the previous data on screen so the UI doesn't flicker between updates.
- Error state: red text banner "Failed to load /api/consequence/payer-roi. Check the backend is running and Mongo is populated." — replaces the whole panel body until the next successful fetch.

### What's server-side vs client-side

The endpoint intentionally stores only the primitives that DON'T depend on `intervention_cost`: `gross_benefit_{h}yr` and `expected_drug_cost_{h}yr`. Everything else (ROI, net benefit, time-to-positive, population aggregates) is recomputed on the server per request using the caller's intervention value. This lets the slider work with a single Mongo collection and no per-slider-value document writes.

---

## Unit tests — 23 new (all passing)

```
Model/consequence/tests/test_roi.py
  test_annuity_zero_years                                    PASSED
  test_annuity_zero_discount_equals_years                    PASSED
  test_annuity_positive_discount_less_than_years             PASSED
  test_drug_cost_full_adherence_matches_annuity              PASSED
  test_drug_cost_zero_adherence_prorated                     PASSED
  test_drug_cost_mixed_cohort                                PASSED
  test_break_even_simple                                     PASSED
  test_break_even_none_when_no_savings                       PASSED
  test_break_even_returns_float_type                         PASSED
  test_compute_roi_returns_output_dataclass                  PASSED
  test_compute_roi_gross_benefit_formula                     PASSED
  test_compute_roi_expected_downstream_formula               PASSED
  test_compute_roi_positive_when_gross_exceeds_costs         PASSED
  test_compute_roi_negative_when_drug_dominates              PASSED
  test_compute_roi_intervention_reduces_net                  PASSED
  test_compute_roi_intervention_threshold_is_pre_intervention_net  PASSED
  test_compute_roi_horizon_1_matches_annual_cost             PASSED
  test_time_to_positive_year1_positive                       PASSED
  test_time_to_positive_interpolates_crossing                PASSED
  test_time_to_positive_returns_none_when_never_positive     PASSED
  test_time_to_positive_empty_input                          PASSED
  test_population_roi_weights_by_patient_count               PASSED
  test_population_roi_zero_drug_cost_safe                    PASSED

Combined suite (markov + rebound + roi): 73 passed in 1.59s
```

---

## Known v1 limitations (added to §10.4 of [DATA_AND_MODEL_DOCUMENTATION.md](../DATA_AND_MODEL_DOCUMENTATION.md))

| # | Limitation | Mitigation path |
|---|---|---|
| 19 | 35% net-of-rebate assumption is ASSUMED, not per-payer. | Set `glp1_payer_net_rebate_fraction=0` for WAC sensitivity. |
| 20 | QALY / QoL benefits not modeled — ROI is pure cost avoidance. | Framing: dashboard should say "budget impact" not "value". |
| 21 | On-therapy modifiers are population-average RRs. | Trial-sourced; documented. v2 could stratify by baseline severity. |
| 22 | Adherence assumed constant across horizon. | v2: year-specific α(t) from KM survival layer. |
| 23 | No mortality reduction credit for on-therapy. | Small conservative bias; deferred to v2. |

---

## How to reproduce

From project root:

```bash
# 1. Generate all Consequence Model CSVs
Backend/venv/Scripts/python.exe -m Model.consequence.downstream_cost      # Phase 1
Backend/venv/Scripts/python.exe -m Model.consequence.rebound_risk         # Phase 2
Backend/venv/Scripts/python.exe -m Model.consequence.payer_roi            # Phase 3

# 2. Run the full test suite (73 tests)
Backend/venv/Scripts/python.exe -m pytest Model/consequence/tests -v

# 3. Push everything into Mongo
cd Backend
PYTHONIOENCODING=utf-8 venv/Scripts/python.exe -m scripts.migrate_csv_to_mongo

# 4. Start the API and hit the endpoint
venv/Scripts/python.exe -m uvicorn main:app --reload

# Baseline (intervention = $500):
# GET http://localhost:8000/api/consequence/payer-roi

# Slider example (intervention = $1200):
# GET http://localhost:8000/api/consequence/payer-roi?intervention_cost=1200
```

---

## Open items still pending

Same list as after Phase 2; no new ones created:

1. Target payer type (Medicare vs commercial — the `payer_type` switch exists but is not API-exposed). **RESOLVED in a post-Phase-4 extension — see below.**
2. Default intervention cost ($500 placeholder — now user-configurable via query param).
3. 3-year vs 5-year primary ROI horizon for the dashboard headline.
4. Real adherence data plug-in.

---

## Extensions delivered after the initial Phase 3 recap

Two additions landed on Phase 3 artefacts (payer_roi.py, /payer-roi endpoint) during Phase 4, motivated by "why is ROI negative and how do we make it positive?" These are documented in full in [phase_4_progress.md](phase_4_progress.md) but recorded here for Phase 3 traceability:

### Extension A — Yearly horizon extended from 1..5 → 1..10

- `payer_roi.py` `YEARLY_HORIZONS = tuple(range(1, 11))` — every patient is now projected 10 years out under both off-therapy and on-therapy Markov rollouts.
- `PRIMARY_HORIZONS` extended from `(1, 3, 5)` → `(1, 3, 5, 10)`. Wide-format `payer_roi.csv` grew from 5 to 10 horizon-year columns per row.
- `time_to_positive_roi_years` now interpolates across years 1..10 (previously 1..5).
- `payer_roi_yearly.csv` grew from 20 rows (4×5) to 40 rows (4×10) — later 120 rows once payer_type was added below.
- Backend schema added `PayerROIYearlyPoint` and `yearly_roi_series: List[PayerROIYearlyPoint]` on `PayerROICluster`; `population_roi_10yr` added to the response.
- Verified: no cluster reaches positive ROI in 10 years under `current` scenario, confirming the "5-yr negative is real, not an artefact of horizon truncation" story.

### Extension B — Payer-type toggle with layered override registry

- **New directory `evidence/overrides/`** with `medicare_2028.csv` and `post_generic.csv` — each an evidence-linked sparse override listing only the parameters that differ from base (`glp1_wac_*` per molecule + `glp1_payer_net_rebate_fraction`). Base registry unchanged.
- **New module `Model/consequence/registry.py`** — single-source loader with `load_registry(payer_type)` merge logic and `available_payer_types()` discovery. Both `downstream_cost.py` and `payer_roi.py` import from here.
- **`payer_roi.py`** `main()` factored to iterate all payer_types by default. Writes a single tagged `payer_roi.csv` (12 rows: 4 clusters × 3 scenarios) and `payer_roi_yearly.csv` (120 rows).
- **Migration** — compound unique indexes `(payer_type, cluster)` and `(payer_type, cluster, horizon_years)`.
- **Endpoint**: `GET /api/consequence/payer-scenarios` (discovery) + `payer_type` query param on `/payer-roi` with graceful fallback to `current` when the requested scenario isn't populated.

**ROI results under each scenario (intervention=$500):**

| Scenario | Pop 5-yr | Pop 10-yr | Cluster crossings |
|---|---|---|---|
| `current` (baseline) | −0.847 | −0.758 | none |
| `medicare_2028` (projected CMS 2028) | −0.717 | −0.550 | none (c3 to −0.17) |
| `post_generic` (2032+ biosimilars) | −0.068 | **+0.479** | **c3: 2.5yr · c1: 3.1yr · c2: 6.8yr** |

**Adding a future scenario** = 1 new CSV in `evidence/overrides/`, no code change. The layered pattern was designed so that real-payer contract data (when it lands) becomes new override files rather than refactors.

---

## What's next — Phase 4 (Weeks 7–8)

Build the "Cost of Inaction" React screen. Three panels backed by the three
consequence endpoints:

- **Panel 1 — Downstream Cost** (Week 7a): stacked bar per cluster by cost
  driver (ESRD / CV event / Uncontrolled T2D), 5/10-year toggle. Fetches from
  `/api/consequence/downstream-cost`.
- **Panel 2 — Rebound Risk** (Week 7b): 12-month HbA1c line chart per cluster,
  severity gauge cards, early/median/late dropout timing sensitivity toggle.
  Fetches from `/api/consequence/rebound-risk`.
- **Panel 3 — Payer ROI** (Week 8): grouped bar of ROI at 1/3/5 yr per cluster,
  interactive intervention-cost slider that re-fetches
  `/api/consequence/payer-roi?intervention_cost=<x>` on change, "max spend
  before ROI goes negative" highlight card per cluster.

Phase 4 is the last build-heavy phase. Phase 5 (validation + demo script, Week 9) closes the plan.
