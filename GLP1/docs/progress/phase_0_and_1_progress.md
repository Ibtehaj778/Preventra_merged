# Consequence Model — Phase 0 & Phase 1 Progress

**Plan reference:** [CONSEQUENCE_MODEL_IMPLEMENTATION_PLAN.md](../CONSEQUENCE_MODEL_IMPLEMENTATION_PLAN.md)
**Status:** Weeks 1–3 of the 9-week plan complete. Ready to start Phase 2 (Metabolic Rebound Risk Engine).

---

## Phase 0 — Foundation & Evidence Audit (Week 1)

All three Phase 0 deliverables produced in [evidence/](../evidence/).

### 0.1 — Parameter Registry

**File:** [evidence/parameter_registry.csv](../evidence/parameter_registry.csv) (34 rows)

Single source of truth for every hardcoded clinical and economic value the consequence model will consume. Each row carries `parameter_name`, `value`, `unit`, `source`, `source_url`, `year`, and `notes`.

Coverage:

| Category | Parameters | Headline sources |
|---|---|---|
| State-cost weights | controlled T2D, uncontrolled T2D, CKD3, CKD4/5, ESRD (Medicare + commercial), CV acute, CV follow-up | ADA Economic Standards 2024; USRDS 2023 ADR; HCCI 2022; AHRQ MEPS |
| Markov transitions | S0→S1 (3 strata), S1→S2, S2→S3, S3→Death, baseline death, CV hazards per state | UKPDS Outcomes Model v2; DPP 10-yr follow-up; Framingham/Emerging Risk Factors; USRDS |
| GLP-1 rebound (Phase 2 inputs) | HbA1c monthly rebound rate + plateau %, BMI monthly rebound + plateau %, T2D incidence by HbA1c stratum | SUSTAIN-1 / STEP-1 extensions; SURMOUNT-4; DPP |
| GLP-1 efficacy on-therapy | residual CV RR (0.74), residual renal RR (0.64) | SUSTAIN-6, LEADER, FLOW (semaglutide) |
| Drug WAC (per molecule) | semaglutide, tirzepatide, liraglutide, dulaglutide annual list price | RED BOOK 2024 |
| Conventions | 3% discount rate, annual cycle, default 5-yr horizon | Second Panel on CE in Health and Medicine 2016 |
| **Flagged "ASSUMED, NOT SOURCED"** | $500/patient intervention cost; 15% dropout reduction | Existing budget_impact.csv placeholders — must not propagate into ROI |

### 0.2 — CEA Audit

**File:** [evidence/cea_audit.md](../evidence/cea_audit.md)

Pass/flag/fail audit of the existing CEA outputs ([Backend/data/cost_effectiveness.csv](../../Backend/data/cost_effectiveness.csv), [Backend/data/budget_impact.csv](../../Backend/data/budget_impact.csv), [Backend/data/icer_by_segment.csv](../../Backend/data/icer_by_segment.csv)):

| Item | Verdict | Action carried into later phases |
|---|---|---|
| A. `avg_annual_cost` per cluster | FLAG | Use per-molecule WAC + cluster mix in ROI; label cluster mean as "random molecule assignment" in dashboard |
| B. 15% dropout reduction + $500 intervention | **FAIL** | Replace with model-derived adherence uplift + user-configurable slider in Phase 3 |
| C. Exponential `time_to_dropout` λ | PASS w/ caveat | Add Phase 1 sensitivity comparing `time_to_dropout` vs. day-180 entry |
| D. `wasted_spend_per_pt` semantics | FLAG | Use prorated drug cost in ROI; relabel existing metric in dashboard tooltip |
| E. Negative ICERs | PASS | Relabel as "dominated"/"dominant" in consequence-model UI |

Verdict: proceed to Phase 1 — no structural rework of existing CEA pipeline required.

### 0.3 — Markov Scope Decision

**File:** [evidence/markov_scope_decision.md](../evidence/markov_scope_decision.md)

**Adopted: 6-state v1** (not the plan's literal 2-state Option A or 5-state Option B).

Rationale: the Phase 4 dashboard's "primary cost driver" stacked bar requires CV and ESRD as separate state categories, which a 2-state model cannot deliver. Going to the full 5-stage CKD ladder requires sourcing four separate transition probabilities defensibly — over-scope for one week. The compromise:

```
S0      Controlled glycemia (HbA1c < 7 OR on therapy)
S1      Uncontrolled T2D
S2      CKD / nephropathy (CKD3–5 collapsed)
S3      ESRD / dialysis
S4      CV event (modeled as independent stream, not a Markov state)
Death   Absorbing
```

CKD-stage granularity is gated behind a `MARKOV_GRANULARITY = "v1" | "v2"` flag — the registry already has both `ckd_stage3_annual_cost_usd` and `ckd_stage4_5_annual_cost_usd` so v2 is a config switch, not a rework.

---

## Phase 1 — Downstream Cost Model (Weeks 2–3)

### Code added

| File | Purpose |
|---|---|
| [Model/consequence/markov.py](../../Model/consequence/markov.py) | Pure Markov logic. `MarkovParams` dataclass, `build_transition_matrix`, `run_markov`, `primary_cost_driver`. No I/O — re-usable for the Phase 3 on-therapy projection. |
| [Model/consequence/downstream_cost.py](../../Model/consequence/downstream_cost.py) | Script entry point. Loads parameter registry + [Backend/data/GLP1_FINAL_WITH_SURVIVAL.csv](../../Backend/data/GLP1_FINAL_WITH_SURVIVAL.csv), runs the 5- and 10-year rollout per patient, writes [Backend/data/progression_cost.csv](../../Backend/data/progression_cost.csv). Supports `payer_type="medicare"|"commercial"`. |
| [Model/consequence/tests/test_markov.py](../../Model/consequence/tests/test_markov.py) | **20 unit tests, all passing.** |
| [Backend/routers/consequence.py](../../Backend/routers/consequence.py) | `GET /api/consequence/downstream-cost` — aggregates per-cluster from Mongo `progression_cost` collection. |
| [Backend/schemas/consequence.py](../../Backend/schemas/consequence.py) | Pydantic response schemas. |
| [Backend/main.py](../../Backend/main.py) | Router registered. |
| [Backend/scripts/migrate_csv_to_mongo.py](../../Backend/scripts/migrate_csv_to_mongo.py) | Extended with `migrate_progression_cost()` step + `cluster` and `patient_idx` indexes. |

### Markov model summary

- **States:** 5 clinical states (S0 Controlled, S1 Uncontrolled, S2 CKD, S3 ESRD, Death) + CV events as an independent layered stream.
- **Cycle length:** 1 year. **Default horizon:** 5 years. **Sensitivity:** 10 years.
- **Cost accrual rule:** state-weighted annual cost + CV acute cost in entry year + CV follow-up cost in all subsequent years weighted by cumulative CV survivor probability.
- **Discounting:** 3% annual, applied per-cycle.
- **HbA1c entry stratification:**
  - `LBXGH < 5.7`  → enter S0, S0→S1 rate = 0.005/yr (normal glycemia)
  - `5.7 ≤ LBXGH < 6.5`  → enter S0, S0→S1 rate = 0.06/yr (pre-DM, DPP-derived)
  - `LBXGH ≥ 6.5`  → enter S1 (uncontrolled T2D at dropout)

### Output: [progression_cost.csv](../../Backend/data/progression_cost.csv) (7,566 rows)

Columns: `patient_idx`, `cluster`, `segment_short`, `lbxgh_baseline`, `bmxbmi_baseline`, `time_to_dropout_days`, `event_occurred`, `entry_state`, `entry_state_name`, `expected_downstream_cost_5yr`, `expected_downstream_cost_10yr`, `esrd_probability_5yr`, `death_probability_5yr`, `cv_event_probability_5yr`, `primary_cost_driver`, `cost_share_esrd_5yr`, `cost_share_cv_5yr`, `cost_share_uncontrolled_t2d_5yr`.

### Backend endpoint

`GET /api/consequence/downstream-cost` → response shape:

```json
{
  "by_cluster": [
    {
      "cluster_id": 1,
      "cluster_label": "Financial Barrier Dropout Risk",
      "n_patients": 2104,
      "avg_downstream_cost_5yr": 54929.46,
      "avg_downstream_cost_10yr": 111329.41,
      "esrd_probability_5yr": 0.00253,
      "cv_event_probability_5yr": 0.07253,
      "total_population_cost_5yr": 115571599.92
    }
  ],
  "population_total_5yr": 370490800,
  "population_total_10yr": 743710000,
  "primary_cost_driver_distribution": {
    "Uncontrolled_T2D": 0.6443,
    "CV_event": 0.3557
  },
  "n_patients_total": 7566
}
```

### Sanity check (per plan §Phase 1)

| Cluster | Mean HbA1c | n | avg 5-yr cost | 5-yr ESRD prob | 5-yr CV prob |
|---|---|---|---|---|---|
| 1 — Financial Barrier Dropout Risk | 6.77 | 2,104 | **$54,929** ✓ highest | 0.25% | 7.3% |
| 3 — Moderate Risk Moderate Adherer | 6.55 | 1,177 | $53,304 | 0.22% | 6.9% |
| 2 — Low Friction Strong Adherer | 6.20 | 2,383 | $48,544 | 0.15% | 6.0% |
| 0 — Low Urgency Dropout Risk | 5.35 | 1,902 | $40,246 | 0.01% | 4.5% |

- ✅ Financial Barrier cluster ranks highest on downstream burden — matches the directional expectation in the plan.
- ✅ Cluster ordering follows mean HbA1c severity.
- ✅ Population 5-yr exposure $370.5M ≈ $9.8k/patient/yr — below the $13k/yr ADA average because many patients enter and stay in S0.
- ✅ No cluster exceeds ROI > 10× at 5 years (not yet computable, but cost magnitudes are in the plausible band).

### Unit tests — all 20 passing

```
Model/consequence/tests/test_markov.py
  test_entry_state_t2d_threshold                          PASSED
  test_s0_to_s1_rate_stratification                       PASSED
  test_transition_matrix_rows_sum_to_one                  PASSED
  test_transition_matrix_non_negative                     PASSED
  test_death_is_absorbing                                 PASSED
  test_esrd_only_exits_to_death                           PASSED
  test_on_therapy_renal_rr_reduces_progression            PASSED
  test_state_vector_stays_a_probability                   PASSED
  test_state_vector_starts_one_hot                        PASSED
  test_death_probability_monotone                         PASSED
  test_horizon_1_no_discount_no_followup                  PASSED
  test_higher_hba1c_entry_costs_more                      PASSED
  test_discount_reduces_late_year_cost                    PASSED
  test_zero_discount_matches_undiscounted                 PASSED
  test_on_therapy_costs_less_than_off_therapy             PASSED
  test_cv_cumulative_prob_monotone                        PASSED
  test_cv_hazard_zero_for_death_state                     PASSED
  test_primary_cost_driver_picks_largest                  PASSED
  test_primary_cost_driver_folds_ckd_into_t2d             PASSED
  test_primary_cost_driver_handles_zero                   PASSED
```

### Known v1 limitations (to log in Phase 5 documentation)

1. **No intra-S1 HbA1c gradient.** Two patients in S1 with LBXGH 6.8 vs. 8.9 produce identical projections because `p_s1_to_s2 = 0.026` is a single population-average rate. The registry has `trans_s0_to_s1_per_year_mid_hba1c` and `..._high_hba1c` available to add an HbA1c-stratified multiplier in v2.
2. **`time_to_dropout` not yet used to shift Markov entry timing.** The 5-year horizon currently starts at year 0 of the rollout regardless of when the patient drops out. A patient dropping at day 30 vs. day 150 currently produces the same downstream projection. Phase 2's sensitivity analysis (early/median/late dropout) will surface whether this materially shifts the numbers.
3. **CKD collapsed into one state.** Per the scope decision. v2 switchable via `MARKOV_GRANULARITY`.
4. **Medicare cost defaults.** ESRD weight uses USRDS Medicare FFS ($93k/yr). For commercial-payer demos, set `payer_type="commercial"` to swap in the HCCI figure ($309k/yr).
5. **CV recurrence not modeled.** First CV event applies acute + follow-up cost; subsequent CV events in years 2–5 are not modeled.

---

## How to reproduce

From the project root:

```bash
# 1. Generate progression_cost.csv (uses Backend venv since it has the right deps)
Backend/venv/Scripts/python.exe -m Model.consequence.downstream_cost

# 2. Run the unit tests
Backend/venv/Scripts/python.exe -m pytest Model/consequence/tests -v

# 3. Push progression_cost.csv into Mongo (requires .env with MONGODB_URI)
cd Backend
venv/Scripts/python.exe -m scripts.migrate_csv_to_mongo

# 4. Start the API and hit the new endpoint
venv/Scripts/python.exe -m uvicorn main:app --reload
# GET http://localhost:8000/api/consequence/downstream-cost
```

---

## Open items / decisions still pending

These were flagged in Phase 0 and remain open before Phase 3 (Payer ROI Synthesizer):

1. **Target payer type.** Medicare vs. commercial ESRD cost differs ~3.3x ($93k vs $309k/yr). Default is Medicare; commercial switch is plumbed but not exposed in the API yet.
2. **Default intervention cost.** $500/patient is currently the assumed-not-sourced placeholder. Phase 3 will expose this as a slider; the default value still needs to be picked.
3. **3-year budget horizon billing.** Open Question #1 in the plan — should the dashboard lead with 5-year ROI (current) or a 3-year horizon to match payer budget cycles?
4. **Real adherence data plug-in.** When real prescription fill data arrives, the consequence model accepts adherence probabilities as an input — no rework needed. Just swap `adherence_proba` from the synthetic source.

---

## Next up — Phase 2 (Weeks 4–5)

Build [Model/consequence/rebound_risk.py](../../Model/consequence/rebound_risk.py):

- Per-patient HbA1c rebound trajectory using `hba1c_rebound_rate_per_month` from the registry (0.18 HbA1c %/month, first 6 mo) and `hba1c_rebound_plateau_pct_of_loss` (0.66).
- BMI rebound trajectory using `bmi_rebound_rate_per_month` (0.42 kg/m² per month) and `bmi_rebound_plateau_pct_of_loss` (0.67).
- `p_new_t2d_12mo` for pre-DM patients using `t2d_incidence_pre_dm_low/high_per_year`.
- Sensitivity analysis: early (day 30) / median (cluster-specific) / late (day 150) dropout timing.
- New endpoint: `GET /api/consequence/rebound-risk`.
- New CSV: `rebound_risk.csv`.

The Phase 2 limitation — rebound trajectories sourced from European trial populations, not calibrated to the NHANES-seeded synthetic cohort — must be added to [DATA_AND_MODEL_DOCUMENTATION.md](../DATA_AND_MODEL_DOCUMENTATION.md) as Section 10 entry when Phase 5 runs.
