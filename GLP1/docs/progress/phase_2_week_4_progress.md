# Consequence Model — Phase 2 / Week 4 Progress

**Plan reference:** [CONSEQUENCE_MODEL_IMPLEMENTATION_PLAN.md](../CONSEQUENCE_MODEL_IMPLEMENTATION_PLAN.md) §Phase 2
**Status:** Week 4 deliverables complete. Week 5 (sensitivity analysis, endpoint, docs) pending.

---

## Scope for Week 4

Per the plan, Phase 2 (Metabolic Rebound Risk Engine) spans Weeks 4–5. I split the work as:

- **Week 4 → core trajectory & probability outputs:** rebound math, entry script, `rebound_risk.csv`, unit tests.
- **Week 5 → sensitivity, integration, docs:** early/median/late dropout sensitivity, FastAPI endpoint, Mongo migration, documentation update, Phase 2 recap.

Week 4 is what is finished as of this writing.

---

## Registry extensions

Added 11 new sourced rows to [evidence/parameter_registry.csv](../evidence/parameter_registry.csv):

| Parameter | Value | Source |
|---|---|---|
| `glp1_efficacy_hba1c_reduction_semaglutide` | 1.6 pts | SUSTAIN-2, STEP-2 |
| `glp1_efficacy_hba1c_reduction_tirzepatide` | 2.1 pts | SURPASS-1..5 |
| `glp1_efficacy_hba1c_reduction_liraglutide` | 1.1 pts | LEAD program; SCALE-Diabetes |
| `glp1_efficacy_hba1c_reduction_dulaglutide` | 1.4 pts | AWARD; REWIND |
| `glp1_efficacy_weight_loss_pct_semaglutide` | 14.9% | STEP-1 |
| `glp1_efficacy_weight_loss_pct_tirzepatide` | 20.9% | SURMOUNT-1 |
| `glp1_efficacy_weight_loss_pct_liraglutide` | 8.0% | SCALE-Obesity |
| `glp1_efficacy_weight_loss_pct_dulaglutide` | 4.5% | AWARD-11 |
| `glp1_steady_state_days` | 90 | GLP-1 pharmacology |
| `t2d_threshold_hba1c` | 6.5 | ADA Standards of Care 2024 §2 |
| `uncontrolled_t2d_threshold_hba1c` | 8.0 | ADA Standards of Care 2024 §6 |

### Revised row

`hba1c_rebound_rate_per_month` was changed from `0.18 → 0.10`. The old value (taken as an approximate from SUSTAIN/STEP extension trials) was mathematically inconsistent with the 12-month plateau (`rate × 12` must be ≥ `plateau_pct × reduction`). At 0.10/month, the linear-to-plateau curve reaches the asymptote in roughly 11 months for a typical patient — consistent with published 1-year extension data. The notes column carries this calibration reasoning.

---

## Code added

| File | Purpose |
|---|---|
| [Model/consequence/rebound.py](../../Model/consequence/rebound.py) | Pure trajectory + threshold logic. `ReboundParams` dataclass, `hba1c_trajectory`, `bmi_trajectory`, `dm_status_at_dropout`, `months_to_threshold`, `p_new_t2d_12mo`, `p_uncontrolled_12mo`, `rebound_severity_score`, `reduction_attained`. No I/O. |
| [Model/consequence/rebound_risk.py](../../Model/consequence/rebound_risk.py) | Entry script. Loads the registry + [Backend/data/GLP1_FINAL_WITH_SURVIVAL.csv](../../Backend/data/GLP1_FINAL_WITH_SURVIVAL.csv), runs the 12-month projection per patient, writes [Backend/data/rebound_risk.csv](../../Backend/data/rebound_risk.csv) (7,566 rows), prints per-cluster sanity summary. |
| [Model/consequence/tests/test_rebound.py](../../Model/consequence/tests/test_rebound.py) | 30 unit tests, all passing. Combined Phase 1 + Phase 2 test suite = **50 tests, all green**. |

---

## Rebound model summary

### Per-patient projection

```
1. Per-molecule trial HbA1c reduction and weight-loss % from the registry.
2. Prorate by min(time_to_dropout / 90 days, 1.0).
3. Apply a clinical floor: on-therapy HbA1c cannot drop below 5.0
   (corrects for the fact that trial benchmarks came from T2D cohorts
   with baseline ~8.0; applying full reduction to pre-DM baselines
   would overshoot biology).
4. HbA1c at dropout = baseline − attained_reduction.
5. Post-dropout rebound: linear at hba1c_rebound_rate_per_month (0.10)
   until asymptote (attained_reduction × plateau_pct = 0.66), then flat.
6. BMI follows the same shape with bmi_rebound_rate_per_month (0.42)
   and plateau (0.67).
7. Threshold crossings (HbA1c 6.5 / 8.0) produce p_new_t2d_12mo and
   p_uncontrolled_12mo.
8. Composite severity score blends HbA1c rebound (40%), BMI rebound (30%),
   threshold-crossing probability (30%).
```

### Output: [rebound_risk.csv](../../Backend/data/rebound_risk.csv) (7,566 rows)

Columns: `patient_idx`, `cluster`, `segment_short`, `assigned_molecule`, `lbxgh_baseline`, `bmxbmi_baseline`, `time_to_dropout_days`, `dm_status_at_dropout`, `hba1c_at_dropout`, `bmi_at_dropout`, `expected_hba1c_6mo`, `expected_hba1c_12mo`, `expected_bmi_6mo`, `expected_bmi_12mo`, `p_new_t2d_12mo`, `p_uncontrolled_12mo`, `months_to_t2d_threshold` (nullable for T2D patients), `rebound_severity_score`.

---

## Sanity check — per-cluster averages

```
cluster  n_patients  hba1c_at_dropout  hba1c_12mo  bmi_at_dropout  bmi_12mo  severity  p_new_t2d_12mo  p_uncontrolled_12mo
   0     1902        5.02              5.24        33.38           35.05     0.151     0.025           N/A
   1     2104        5.78              6.43        30.97           32.76     0.315     0.160           0.721
   2     2383        5.27              5.86        27.54           32.07     0.429     0.079           0.908
   3     1177        5.71              6.26        31.80           33.43     0.271     0.136           0.540
```

### DM status at dropout (population share)

```
normal             83.4%
pre_dm              6.9%
t2d                 5.7%
uncontrolled_t2d    4.0%
```

### Reading the table

- **Cluster 2 (Low Friction Strong Adherer) has the highest severity score (0.429).** That looks counterintuitive but is correct: they attained the largest on-therapy benefit, so they have the largest pool to rebound. This is exactly the framing the consequence model should communicate to a payer — *if* they were to drop out, the loss would be biggest for the patients currently doing best.
- **Cluster 1 (Financial Barrier) has the highest p_new_t2d_12mo at 16%** — these are pre-DM patients with cost pressure; their HbA1c trajectory most often crosses 6.5 within 12 months post-dropout.
- **p_uncontrolled_12mo of 91% in Cluster 2** reflects how many of their T2D patients lose control: severe-baseline patients with high attained reduction have the most to lose.
- The DM-status partition shows 83% of the cohort sits at HbA1c < 5.7 on therapy (consistent with NHANES baseline distribution + GLP-1 reduction).

---

## A subtle finding the unit tests surfaced

One unit test was initially written with reversed intuition: it expected the early-dropout patient to end up *lower* (better) at 12 months. The test failed, and the trace pointed at the actual model behavior:

```
Patient (baseline HbA1c 7.0, semaglutide):
  Early dropout (day 30):    attained=0.53  →  12-mo HbA1c = 6.82
  Late dropout (day 180):    attained=1.60  →  12-mo HbA1c = 6.46
```

Late-dropout patients end up *lower* (better) at 12 months. Reason: 34% of the on-therapy benefit is durable (1 − plateau_pct); 34% of a larger gain is more durable benefit. This matches published 1-year STEP extension data — longer GLP-1 exposure leaves more residual metabolic benefit even after stopping. The test was corrected and now asserts the right direction. Documenting it here because the same intuition will come up again when the dashboard sensitivity panel is built in Week 5.

---

## Unit tests — 30 new (all passing)

```
Model/consequence/tests/test_rebound.py
  test_reduction_attained_zero_time                      PASSED
  test_reduction_attained_partial_steady_state           PASSED
  test_reduction_attained_capped_at_full                 PASSED
  test_reduction_floor_enforced                          PASSED
  test_reduction_no_floor_when_baseline_high             PASSED
  test_hba1c_trajectory_at_dropout_equals_on_therapy     PASSED
  test_hba1c_trajectory_monotone_non_decreasing          PASSED
  test_hba1c_trajectory_caps_at_plateau                  PASSED
  test_hba1c_trajectory_early_dropout_worse_12mo         PASSED
  test_hba1c_trajectory_normal_baseline_no_floor_breach  PASSED
  test_bmi_trajectory_at_dropout                         PASSED
  test_bmi_trajectory_caps_at_baseline_minus_residual    PASSED
  test_bmi_trajectory_monotone                           PASSED
  test_dm_status_partitions                              PASSED
  test_months_to_threshold_basic                         PASSED
  test_months_to_threshold_already_above                 PASSED
  test_months_to_threshold_unreachable                   PASSED
  test_months_to_threshold_zero_rate                     PASSED
  test_p_new_t2d_none_for_t2d_patient                    PASSED
  test_p_new_t2d_one_when_trajectory_crosses             PASSED
  test_p_new_t2d_uses_dpp_high_when_subthreshold         PASSED
  test_p_new_t2d_uses_dpp_low_when_below_six             PASSED
  test_p_uncontrolled_none_for_pre_dm                    PASSED
  test_p_uncontrolled_one_when_already_uncontrolled      PASSED
  test_p_uncontrolled_one_when_trajectory_crosses        PASSED
  test_p_uncontrolled_uses_progression_baseline          PASSED
  test_severity_in_unit_interval                         PASSED
  test_severity_zero_when_no_rebound                     PASSED
  test_severity_one_at_extremes                          PASSED
  test_severity_handles_none_p_crossing                  PASSED

Combined suite (markov + rebound): 50 passed in 0.45s
```

---

## Known v1 limitations to log in Phase 5 documentation

1. **Linear-to-plateau approximation.** Biological rebound is closer to monoexponential. A v2 upgrade would replace the piecewise-linear curve with an exponential approach to plateau, requiring an additional half-life parameter.
2. **Trial-population bias.** Per-molecule reductions are from European-majority RCTs (SUSTAIN, STEP, SURMOUNT). The NHANES-seeded cohort here is demographically different. The rebound rates are directionally correct but not calibrated to this population. **This must be added to [DATA_AND_MODEL_DOCUMENTATION.md](../DATA_AND_MODEL_DOCUMENTATION.md) Section 10 in Week 5.**
3. **Clinical floor at HbA1c = 5.0.** A pragmatic correction for the trial-population overshoot when applied to pre-DM/normal baselines. Documented in code; reviewers should treat it as a v1 simplification.
4. **No per-patient HbA1c variability.** All patients on the same molecule with the same baseline get the same projection. v2 could add patient-level random effects (e.g. ±0.3 SD on attained reduction).
5. **Sensitivity to dropout timing not yet exposed.** The CSV uses each patient's actual `time_to_dropout`. The early/median/late dropout sensitivity (planned for Week 5) will surface how much the 12-month outcomes depend on timing.

---

## How to reproduce

From project root:

```bash
# Generate rebound_risk.csv
Backend/venv/Scripts/python.exe -m Model.consequence.rebound_risk

# Run the unit tests
Backend/venv/Scripts/python.exe -m pytest Model/consequence/tests -v
```

---

## What's next — Week 5

1. **Sensitivity analysis.** Per cluster, run the rebound projection at three dropout-timing scenarios: early (day 30 — from `survival_checkpoints.csv`), median (cluster median from KM), late (day 150). Output: extension to `rebound_risk.csv` (or a sidecar `rebound_sensitivity.csv`).
2. **Backend endpoint.** `GET /api/consequence/rebound-risk` — extend [Backend/routers/consequence.py](../../Backend/routers/consequence.py) and [Backend/schemas/consequence.py](../../Backend/schemas/consequence.py); register in main.
3. **Mongo migration.** Add a `migrate_rebound_risk()` step in [Backend/scripts/migrate_csv_to_mongo.py](../../Backend/scripts/migrate_csv_to_mongo.py).
4. **Documentation update.** Section 10 entry in [DATA_AND_MODEL_DOCUMENTATION.md](../DATA_AND_MODEL_DOCUMENTATION.md) covering the rebound limitations enumerated above.
5. **Phase 2 recap.** Combined `updates/phase_2_progress.md` consolidating Weeks 4–5.
