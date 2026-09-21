# Consequence Model — Phase 2 Progress (Weeks 4–5 Complete)

**Plan reference:** [CONSEQUENCE_MODEL_IMPLEMENTATION_PLAN.md](../CONSEQUENCE_MODEL_IMPLEMENTATION_PLAN.md) §Phase 2
**Status:** Phase 2 complete. Weeks 1–5 of the 9-week plan delivered. Ready to start Phase 3 (Payer ROI Synthesizer).

This document consolidates Weeks 4–5. Week-4-only narrative lives in [phase_2_week_4_progress.md](phase_2_week_4_progress.md) for reference; this is the canonical Phase 2 recap.

---

## What Phase 2 set out to do

Per the plan, the Metabolic Rebound Risk Engine answers the question: *what happens to a patient's glycemic and weight control if they stop GLP-1 therapy?*

Three deliverables: per-patient rebound projection, per-cluster trajectory data for the dashboard line chart, and a sensitivity analysis showing how dropout timing changes the outcome.

---

## Code added across Weeks 4 & 5

| File | Purpose | Week |
|---|---|---|
| [evidence/parameter_registry.csv](../evidence/parameter_registry.csv) | +11 new sourced rows (per-molecule efficacy, GLP-1 steady state, ADA thresholds). 1 row revised (`hba1c_rebound_rate_per_month`: 0.18 → 0.10). | 4 |
| [Model/consequence/rebound.py](../../Model/consequence/rebound.py) | Pure trajectory + threshold logic. `ReboundParams`, `hba1c_trajectory`, `bmi_trajectory`, `dm_status_at_dropout`, `months_to_threshold`, `p_new_t2d_12mo`, `p_uncontrolled_12mo`, `rebound_severity_score`, `reduction_attained`. No I/O. | 4 |
| [Model/consequence/rebound_risk.py](../../Model/consequence/rebound_risk.py) | Entry script. Computes per-patient projection + per-cluster trajectory + sensitivity. Produces 3 CSVs. | 4 (per-patient) + 5 (trajectory + sensitivity) |
| [Model/consequence/tests/test_rebound.py](../../Model/consequence/tests/test_rebound.py) | 30 unit tests for rebound logic. | 4 |
| [Backend/schemas/consequence.py](../../Backend/schemas/consequence.py) | Pydantic response models for the rebound endpoint. | 5 |
| [Backend/routers/consequence.py](../../Backend/routers/consequence.py) | `GET /api/consequence/rebound-risk` endpoint. Aggregates from 3 Mongo collections. | 5 |
| [Backend/scripts/migrate_csv_to_mongo.py](../../Backend/scripts/migrate_csv_to_mongo.py) | Adds `migrate_rebound_risk()`, `migrate_rebound_trajectory()`, `migrate_rebound_sensitivity()` with indexes. | 5 |
| [DATA_AND_MODEL_DOCUMENTATION.md](../DATA_AND_MODEL_DOCUMENTATION.md) | New §10 covering the consequence-model layer; limitations 11–18 added to the registry. | 5 |

### Test suite

- **50 tests total, all passing** (20 Phase 1 Markov + 30 Phase 2 rebound).
- Run: `Backend/venv/Scripts/python.exe -m pytest Model/consequence/tests -v`

---

## Model design

### Per-patient projection (Week 4 core)

```
1. Look up trial HbA1c reduction + weight-loss % for the patient's molecule.
2. Prorate by min(time_to_dropout / 90 days, 1.0)  — accounts for early
   dropouts who never reached steady state.
3. Apply clinical floor: on-therapy HbA1c cannot drop below 5.0 (corrects
   for trial benchmarks coming from T2D cohorts with baseline ~8).
4. HbA1c at dropout = baseline − attained_reduction.
5. Post-dropout rebound: linear at 0.10/month, capped at
   attained × 0.66 plateau (34% of the benefit is durable).
6. BMI follows the same shape with rate=0.42 kg/m²/month, plateau=0.67.
7. Threshold crossings produce per-patient probabilities:
     p_new_t2d_12mo   (for pre-DM patients only)
     p_uncontrolled_12mo  (for T2D patients only)
8. Composite severity score blends:
     40% HbA1c rebound magnitude (normalized at 2 pts)
     30% BMI rebound magnitude (normalized at 5 kg/m²)
     30% threshold-crossing probability
```

### Sensitivity analysis (Week 5)

Per cluster, every patient is re-projected at three dropout-timing scenarios:

- **Early:** day 30 (lower bound of the survival window)
- **Median:** cluster-empirical median of `time_to_dropout` among observed dropouts (`event_occurred == 1`), clipped to `[31, 149]`
- **Late:** day 150 (upper end of the synthetic survival window)

Output is averaged at the cluster level — 12 rows total (4 clusters × 3 scenarios), the structure the dashboard sensitivity toggle expects.

---

## Outputs

| File | Rows | Purpose |
|---|---|---|
| [Backend/data/rebound_risk.csv](../../Backend/data/rebound_risk.csv) | 7,566 | Per-patient projection using each patient's actual `time_to_dropout`. |
| [Backend/data/rebound_trajectory.csv](../../Backend/data/rebound_trajectory.csv) | 60 | Per-cluster × scenario × month (4 × 3 × 5 = 60). HbA1c + BMI averages at months {0, 3, 6, 9, 12}. Powers the dashboard line chart. |
| [Backend/data/rebound_sensitivity.csv](../../Backend/data/rebound_sensitivity.csv) | 12 | Per-cluster × scenario summary at 12 months. Severity, T2D probability, uncontrolled-T2D probability. Powers the sensitivity toggle. |

---

## Sanity check — per-cluster averages (actual dropout timing)

```
cluster  n_patients  hba1c_at_dropout  hba1c_12mo  bmi_at_dropout  bmi_12mo  severity  p_new_t2d_12mo  p_uncontrolled_12mo
   0     1902        5.02              5.24        33.38           35.05     0.151     0.025           N/A
   1     2104        5.78              6.43        30.97           32.76     0.315     0.160           0.721
   2     2383        5.27              5.86        27.54           32.07     0.429     0.079           0.908
   3     1177        5.71              6.26        31.80           33.43     0.271     0.136           0.540
```

### Sensitivity — 12-month severity by cluster × scenario

```
scenario  early  median   late
cluster
0         0.093   0.173  0.190
1         0.186   0.360  0.360
2         0.213   0.431  0.431
3         0.142   0.298  0.298
```

### How to read these tables

- **Cluster 2 has the highest severity (0.429).** Counterintuitive at first glance — these are the Strong Adherers — but correct under the consequence-model framing: they attained the largest on-therapy benefit, so the rebound pool *if they drop* is largest.
- **Severity rises monotonically with dropout timing within each cluster.** Day-30 dropouts have the smallest rebound pool because they barely reached steady state; day-150 dropouts have the full benefit to lose.
- **Median ≈ late in clusters 1–3** because the cluster medians are all ≥ 100 days, by which point patients have already attained the full trial reduction. This is the dashboard's payer message: *the dropout-cost curve is steep for the first 90 days and then flat*. Late retention beyond day 90 is dominated by adherence, not biology.
- **Population-level T2D incidence ≈ 6% over 12 months** (weighted across pre-DM patients), with cluster 1 (Financial Barrier) carrying the heaviest load at 16%.

A subtle finding from the unit tests deserves a callout: **late-dropout patients end up with LOWER 12-month HbA1c than early-dropout patients on the same molecule and baseline.** 34% of a larger reduction is more durable retained benefit than 34% of a smaller one. This is consistent with published STEP-1 extension data and is now captured by `test_hba1c_trajectory_early_dropout_worse_12mo`.

---

## Backend endpoint — `GET /api/consequence/rebound-risk`

Response shape (abridged):

```json
{
  "by_cluster": [
    {
      "cluster_id": 1,
      "cluster_label": "Financial Barrier Dropout Risk",
      "n_patients": 2104,
      "avg_hba1c_at_dropout": 5.784,
      "avg_expected_hba1c_6mo": 6.108,
      "avg_expected_hba1c_12mo": 6.434,
      "avg_bmi_at_dropout": 30.97,
      "avg_expected_bmi_12mo": 32.76,
      "avg_severity_score": 0.3154,
      "p_new_t2d_12mo_mean": 0.1604,
      "p_uncontrolled_12mo_mean": 0.7212,
      "dm_status_distribution": {"normal": 0.18, "pre_dm": 0.55, "t2d": 0.18, "uncontrolled_t2d": 0.09}
    }
  ],
  "trajectory_by_cluster": [
    {
      "cluster_id": 1,
      "scenarios": [
        {"scenario": "early",  "dropout_day": 30,  "points": [{"month": 0, "avg_hba1c": ..., "avg_bmi": ...}, ...]},
        {"scenario": "median", "dropout_day": 106, "points": [...]},
        {"scenario": "late",   "dropout_day": 150, "points": [...]}
      ]
    }
  ],
  "sensitivity": [
    {
      "cluster_id": 1,
      "scenarios": [
        {"scenario": "early",  "dropout_day": 30,  "avg_severity_score": 0.186, "p_new_t2d_12mo_mean": 0.132, ...},
        {"scenario": "median", "dropout_day": 106, "avg_severity_score": 0.360, ...},
        {"scenario": "late",   "dropout_day": 150, "avg_severity_score": 0.360, ...}
      ]
    }
  ],
  "population_t2d_incidence_12mo": 0.0584,
  "n_patients_total": 7566
}
```

Mongo collections consumed: `rebound_risk`, `rebound_trajectory`, `rebound_sensitivity` (all populated by the extended migration script).

---

## Known v1 limitations (added to §10.4 of [DATA_AND_MODEL_DOCUMENTATION.md](../DATA_AND_MODEL_DOCUMENTATION.md))

| # | Limitation | Mitigation path |
|---|---|---|
| 11 | Rebound trajectory sourced from European trial populations; not calibrated to NHANES cohort. | Documented; numbers presented as projections, not measurements. |
| 12 | Linear-to-plateau shape (biology is monoexponential). | v2 upgrade behind a config flag. |
| 13 | Clinical HbA1c floor at 5.0 (trial benchmarks overshoot when applied to pre-DM baselines). | Pragmatic v1 correction; biologically defensible. |
| 14 | No patient-level random effects on rebound. | v2 could add ±0.3 SD on attained reduction. |
| 15 | Markov transitions are population-level averages (within-state HbA1c gradient ignored). | Registry has stratum-level transitions ready for v2. |
| 16 | 10-year projections are illustrative; uncertainty compounds beyond 5 years. | Lead with 5-year figures. |
| 17 | Default cost weights are Medicare FFS; commercial ESRD is ~3.3x higher. | `payer_type="commercial"` switch in script; not yet API-exposed. |
| 18 | No CV-event recurrence modeling. | Simplification; defer to Phase 5 if it materially shifts ROI. |

---

## How to reproduce

From the project root:

```bash
# 1. Generate all Consequence Model CSVs
Backend/venv/Scripts/python.exe -m Model.consequence.downstream_cost      # Phase 1
Backend/venv/Scripts/python.exe -m Model.consequence.rebound_risk         # Phase 2

# 2. Run the full test suite (50 tests)
Backend/venv/Scripts/python.exe -m pytest Model/consequence/tests -v

# 3. Push everything into Mongo
cd Backend
venv/Scripts/python.exe -m scripts.migrate_csv_to_mongo

# 4. Start the API and hit the new endpoints
venv/Scripts/python.exe -m uvicorn main:app --reload
# GET http://localhost:8000/api/consequence/downstream-cost
# GET http://localhost:8000/api/consequence/rebound-risk
```

---

## Open items still pending

Tracked in [updates/phase_0_and_1_progress.md](phase_0_and_1_progress.md); no new ones added by Phase 2:

1. Target payer type (Medicare vs commercial — the `payer_type` switch exists but is not API-exposed).
2. Default intervention cost ($500 placeholder).
3. 3-year vs 5-year primary ROI horizon for the dashboard headline.
4. Real adherence data plug-in (consequence model accepts `adherence_proba` as a drop-in input when real data arrives).

---

## What's next — Phase 3 (Week 6)

Build the Payer ROI Synthesizer: combine adherence probability, downstream cost (Phase 1), rebound risk (Phase 2), and drug cost into a per-cluster ROI with break-even adherence rate and intervention cost threshold. Specifically:

- [Model/consequence/payer_roi.py](../../Model/consequence/payer_roi.py) — implementing the ROI formula from plan §Phase 3, using registry parameters + Phase 1 & 2 outputs.
- `payer_roi.csv` with per-cluster ROI at 1/3/5-year horizons + intervention cost threshold.
- `GET /api/consequence/payer-roi` endpoint.
- Reuse the on-therapy modifier flags already in `MarkovParams` and the rebound model.

Phase 3 is one week of work; Phase 4 (dashboard, Weeks 7–8) and Phase 5 (validation + docs, Week 9) follow.
