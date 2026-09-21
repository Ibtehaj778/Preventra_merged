# Markov Scope Decision — Downstream Cost Model

**Decision needed before Phase 1 starts:** how many states should the per-patient Markov chain track?

The plan (Phase 0.3) presents two options:

- **Option A (simple):** Two-state model — Controlled vs. Uncontrolled T2D.
- **Option B (full):** Five-state chain — Pre-DM → T2D → CKD3 → CKD4/5 → ESRD, with CV-event and death as additional / absorbing states.

This memo records the choice and the rationale.

---

## Decision

**Adopt Option A-extended (six states) as v1, with Option B as a configurable upgrade exposed via a config flag in [Model/consequence/downstream_cost.py](../../Model/consequence/downstream_cost.py).**

The plan's literal Option A (two states) is too coarse for the dashboard's primary visual — the "primary cost driver" stacked bar in Phase 4 needs to distinguish ESRD, CV event, and uncontrolled-T2D costs. A pure two-state model collapses all three into one. So v1 will be:

```
S0  Controlled glycemia       (HbA1c < 7 OR on-therapy)
S1  Uncontrolled T2D          (HbA1c ≥ 7, off therapy)
S2  CKD / nephropathy         (collapsed stages 3–5 pre-dialysis)
S3  ESRD / dialysis           (absorbing for cost calc; transitions to death)
S4  CV event                  (one-time hit + elevated follow-up cost)
S_absorb  Death / out of model
```

This is fewer states than Option B (CKD3 and CKD4/5 are collapsed into S2; pre-DM is folded into S0 with HbA1c-stratified S0→S1 transitions), but more than the plan's literal Option A — enough to drive the dashboard's intended cost-driver decomposition without requiring CKD-stage-specific transition data we don't have well-sourced.

**Option B upgrade path:** A boolean flag `MARKOV_GRANULARITY = "v1" | "v2"` in the script. v2 splits S2 into S2a (CKD3) and S2b (CKD4/5) using the additional transition probabilities in the parameter registry. The cost weights for both states are already in `parameter_registry.csv` (`ckd_stage3_annual_cost_usd`, `ckd_stage4_5_annual_cost_usd`).

---

## Rationale

### Why not literal Option A (two states)

Two states (Controlled vs Uncontrolled) cannot answer the central question the dashboard asks: *what is the patient most likely to die or get hospitalized from?* The "primary cost driver" distribution in the Phase 1 API response — ESRD vs CV event vs uncontrolled T2D — requires CV and ESRD as separate states, full stop. A two-state model produces a single dollar number per patient with no clinically meaningful breakdown.

The plan's recommendation of Option A "for Phase 1 delivery" appears to anticipate this and offers Option B as a parallel build. In practice the dashboard's Panel 1 design (stacked bar by cost driver) already pre-commits to at least three cost categories, so the minimum viable v1 is six states, not two.

### Why not literal Option B (five-state CKD ladder)

Two reasons:

1. **Transition-probability sourcing risk.** CKD stage 3 → stage 4 and stage 4 → stage 5 annual transition probabilities are reported in published Markov models (e.g., Ettehad et al., Lancet 2016; Hoerger et al., Diabetes Care 2010), but the values vary by 2-3x across studies depending on baseline HbA1c, age, and BP control. Sourcing four separate stage-transitions defensibly is a Phase 0 deliverable in its own right and the time budget is one week. Collapsing CKD into a single state lets us source one transition with high confidence (`trans_s1_to_s2_per_year` = 0.026, UKPDS 64) rather than three with low confidence.

2. **Resolution vs. signal.** The dashboard does not surface CKD-stage breakdown. Going from "CKD" to "CKD3/CKD4/CKD5" adds states without adding any user-visible distinction. The only place the finer staging matters is in the cost weight — and the registry already differentiates `ckd_stage3_annual_cost_usd` ($23,500) from `ckd_stage4_5_annual_cost_usd` ($34,200). In v1 we apply a weighted average (~$28k/yr) to the single S2 state; in v2 we split.

### Why the six-state v1 is the right size

- **CV event as a separate state** is necessary because it has a one-time acute cost (~$54k/episode) plus elevated follow-up annual cost (~$12k/yr) — neither of which fits cleanly into a chronic-state cost weight. A separate state lets the cost model apply the episode cost on the transition year and the follow-up cost in subsequent years.

- **Death as absorbing** is required to prevent infinite-horizon cost accrual. Dialysis mortality alone is ~18% per year, and excluding death would overcount ESRD years by a factor of 2–3 over a 5-year horizon.

- **Pre-DM is implicit in S0**, not a separate state. The HbA1c-stratified S0→S1 transition probability (registry rows `trans_s0_to_s1_per_year_low/mid/high_hba1c`) captures the same information without the state overhead. This is the key simplification vs. Option B.

---

## Transition matrix structure (v1)

Annual cycle. Probabilities sourced from `parameter_registry.csv`. Each row sums to 1 (residual stays in current state).

```
              →S0     →S1     →S2     →S3     →S4     →Death
S0 (Control)  resid   p_HbA1c 0       0       0.009   0.012
S1 (Uncont)   0       resid   0.026   0       0.022   0.012
S2 (CKD)      0       0       resid   0.029   0.038   0.012
S3 (ESRD)     0       0       0       resid   *       0.18
S4 (CV)       0       0       0       0       resid   0.012
Death         0       0       0       0       0       1.0
```

Where:
- `p_HbA1c` = `trans_s0_to_s1_per_year_low/mid/high_hba1c` depending on patient's baseline LBXGH stratum.
- `*` cell (S3 → S4): treated as folded into S3 baseline cost; dialysis patients with a CV event continue to be costed at the ESRD rate.
- `resid` = 1 − (sum of outgoing transitions).

### On-therapy modifier (used by Payer ROI Synthesizer in Phase 3)

For patients in the "adherent" branch of the ROI calculation, transition probabilities into worse states are multiplied by:
- `glp1_efficacy_residual_complication_rr` = 0.74 for `→S4` (CV events)
- `glp1_efficacy_residual_renal_rr` = 0.64 for `→S2` and `→S3` (renal transitions)

These are sourced from SUSTAIN-6 / LEADER / FLOW trials (registry rows). They are NOT applied to the dropped-out cohort.

---

## What this commits us to in Phase 1

1. The script [Model/consequence/downstream_cost.py](../../Model/consequence/downstream_cost.py) (to be created in Phase 1) will:
   - Build the 6×6 transition matrix from registry rows.
   - Stratify the S0→S1 probability per patient by baseline LBXGH (using the same thresholds as the plan: <5.7 / 5.7–6.4 / ≥6.5).
   - Roll the chain forward for `markov_default_horizon_years` (5) cycles, with a 10-year sensitivity output.
   - Weight state occupancy by the annual cost from registry, applying CV-event acute cost in the transition year only.
   - Discount future-year costs at 3% (registry `discount_rate_annual`).

2. The `progression_cost.csv` output columns specified in Phase 1 (`primary_cost_driver` ∈ {ESRD, CV, Uncontrolled_T2D}) are achievable from this state structure.

3. Switching to Option B (v2) requires only the additional CKD3↔CKD4/5 transition row and is gated by `MARKOV_GRANULARITY="v2"`.

---

## Risks / open questions

- **Death-state stratification.** v1 uses a single annual death probability (0.012) for non-ESRD states. A higher-fidelity v2 should stratify mortality by state (e.g., S2 mortality ≈ 0.04/yr, S4 follow-up mortality ≈ 0.05/yr). Defer to Phase 5 calibration.

- **CV-event recurrence.** v1 treats S4 as transient — patient enters S4 for one cycle then returns to the prior state with elevated follow-up cost. A more realistic model would allow recurrent CV events. Defer to v2 if needed for sensitivity.

- **Commercial vs. Medicare cost.** The cost weights in the registry default to Medicare FFS (USRDS). For commercial-payer demos, swap in `esrd_annual_cost_commercial_usd` ($309k). Implement as a `PAYER_TYPE = "medicare" | "commercial"` switch in the script. This is Open Question #2 in the implementation plan.

---

**Decision finalized.** Proceed with the six-state v1 described above. v2 (full CKD staging) is on the roadmap as a configurable upgrade, not a blocker for Phase 1.
