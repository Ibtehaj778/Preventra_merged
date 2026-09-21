# CEA Engine Audit — Pre-Consequence-Model Sanity Check

**Scope:** Audit the existing cost-effectiveness and budget-impact outputs (`cost_effectiveness.csv`, `icer_by_segment.csv`, `budget_impact.csv`) before layering the new consequence model on top.

**Audited artifacts:**
- [Model/model.ipynb](../../Model/model.ipynb) — `TRIAL_BENCHMARKS`, `COMPARATORS`, budget impact block
- [Backend/data/cost_effectiveness.csv](../../Backend/data/cost_effectiveness.csv)
- [Backend/data/budget_impact.csv](../../Backend/data/budget_impact.csv)
- [Backend/data/icer_by_segment.csv](../../Backend/data/icer_by_segment.csv)
- [Backend/data/survival_checkpoints.csv](../../Backend/data/survival_checkpoints.csv)

**Verdict legend:** PASS = sourced and defensible / FLAG = directionally fine but undocumented or coarse / FAIL = will not survive payer scrutiny without rework.

---

## A. Per-cluster `avg_annual_cost` vs. published GLP-1 WAC

| Cluster | `avg_annual_cost` (current CEA) | Expected range (WAC-weighted mix) | Verdict |
|---|---|---|---|
| 0 — Low Urgency Dropout Risk | $9,457 | $9.3k–$13.0k | PASS |
| 1 — Financial Barrier Dropout Risk | $10,106 | $9.3k–$13.0k | PASS |
| 2 — Low Friction Strong Adherer | $15,938 | $13k–$16k (skews tirzepatide?) | FLAG |
| 3 — Moderate Risk Moderate Adherer | $7,800 | $7.2k–$9.5k | PASS |

**Reasoning.** `TRIAL_BENCHMARKS` in [Model/model.ipynb](../../Model/model.ipynb) (lines ~1805–1825) sets annual drug costs at $13,000 (semaglutide), $16,000 (tirzepatide), $7,800 (liraglutide), $7,200 (dulaglutide). These match published WAC list prices within ±5% (RED BOOK 2024; see `parameter_registry.csv` rows for `glp1_wac_*`).

**Issue.** The cluster-level `avg_annual_cost` is computed as a simple mean over `assigned_molecule` within each cluster. Because molecule assignment is random and seeded at Layer 1 ([Fusion/layer_1.py](../../Fusion/layer_1.py)), variation across clusters in `avg_annual_cost` is statistical noise — not clinical reality. Cluster 2's $15,938 is higher than every other cluster because that cluster happens to contain a higher share of randomly-assigned tirzepatide patients, not because higher-adherence patients are clinically prescribed tirzepatide more often.

**Why this matters for the consequence model.** When the Payer ROI Synthesizer (Phase 3) takes `avg_annual_cost` per cluster as `drug_cost_per_patient`, the resulting cluster-level ROI differences will partly reflect noise from random molecule assignment rather than real cost differences. Document this in the ROI panel and consider a sensitivity output that fixes molecule mix across clusters.

**Action:** Use the registry's per-molecule WAC values directly when constructing ROI rather than the cluster mean — or label the cluster mean as "current population mix, randomly assigned" in the dashboard tooltip.

**Status: FLAG** — values are defensible in isolation, but cluster differences are noise-driven.

---

## B. 15% dropout reduction assumption in `budget_impact.csv`

**Current state.** [Model/model.ipynb](../../Model/model.ipynb) line ~2017:

```python
INTERVENTION_COST_PER_PT = 500
DROPOUT_REDUCTION        = 0.15   # 15% relative reduction
```

Both numbers are hardcoded without a citation comment. There is no source in the data documentation. They are best-guess defaults.

**Reasoning.** Published GLP-1 adherence intervention studies report a wide range of dropout reductions:

- Pharmacy-led refill outreach (Steiner & Prochazka, J Gen Intern Med 12:6, 1997-era methodology applied to T2D): 7–12% relative reduction in dropout at 6 months.
- Telehealth-supplemented chronic care management (Ko et al., Diabetes Educ 2019): up to 22% reduction in 1-year discontinuation in adherent-by-design samples.
- Copay assistance programs (Avalere/Manatt 2022 reports on commercial payer experience): typically 10–18% adherence uplift, depending on baseline OOP.

**A 15% relative reduction is at the optimistic-middle of this range**, not implausible, but unsourced. The `$500/patient` intervention spend is also a round-number assumption with no citation.

**Why this matters for the consequence model.** The Payer ROI Synthesizer should NOT inherit either of these assumptions blindly. Phase 3 must:

1. Derive the "post-intervention adherence probability" from the model's per-patient adherence scores rather than applying a flat 15% relative reduction to every cluster.
2. Treat the intervention cost as a user-configurable slider input (the dashboard plan already proposes this in Phase 4).
3. Surface the parameter registry entries `dropout_reduction_relative_assumed = 0.15` and `intervention_program_cost_per_patient_usd = 500` with explicit "ASSUMED, NOT SOURCED" flags so reviewers can see exactly which numbers are model-derived and which are placeholders.

**Status: FAIL** — both values are unsourced assumptions baked into a payer-facing output. Acceptable as MVP placeholders, but must not propagate into the consequence model without being either sourced or made explicitly user-configurable.

---

## C. Survival `lambda` and exponential dropout timing

**Current state.** [Model/model.ipynb](../../Model/model.ipynb) line ~1614:

```
# Scale exponential so that ~dropout_rate% of patients drop by day 180
# P(T <= 180) = dropout_rate  =>  lambda = -log(1 - dropout_rate) / 180
```

For each cluster, `time_to_dropout` is sampled from `Exponential(scale = 1/lambda)` where `lambda` is calibrated so that the proportion of patients with T ≤ 180 days matches the cluster's empirical dropout rate.

**Reasoning.** Implied 180-day dropout rates per cluster (from `survival_checkpoints.csv`):

| Cluster | day_180 dropout | Implied λ (1/days) | Median time-to-dropout (days) |
|---|---|---|---|
| 0 — Low Urgency Dropout Risk | 0.7923 | 0.00873 | 79 |
| 1 — Financial Barrier Dropout Risk | 0.6915 | 0.00653 | 106 |
| 2 — Low Friction Strong Adherer | 0.1465 | 0.000881 | 786 |
| 3 — Moderate Risk Moderate Adherer | 0.5939 | 0.00500 | 138 |

**Sense-check against published persistence curves.** Real-world GLP-1 persistence studies (e.g., Weiss et al., Diabetes Obes Metab 2023; Gleason et al., Curr Med Res Opin 2022) report:

- 1-year persistence: ~30–50% for commercial-insurance GLP-1 patients.
- Median time-to-discontinuation: 100–180 days for non-persistent patients.

The synthesized cluster medians (79–138 days for dropouts) are at the **lower end** of published medians — i.e., dropouts in this synthetic dataset happen slightly earlier than typical real-world cohorts. This is consistent with the simulation being calibrated to the 6-month checkpoint dropout proportion and assuming a memoryless (exponential) hazard, which front-loads dropouts.

**Why this matters for the consequence model.** The downstream cost model uses `time_to_dropout` to determine when a patient enters the Markov chain. If `time_to_dropout` is systematically too early, the Markov rollout starts earlier and accumulates more complication years — biasing downstream cost estimates **upward**.

**Mitigation:** Phase 1 should include a sensitivity analysis that runs the Markov rollout starting at (a) the synthesized `time_to_dropout`, (b) day 180 (cluster-uniform). The gap between (a) and (b) bounds the impact of the exponential-hazard simplification.

**Status: PASS with caveat** — the λ values are mathematically defensible given the cluster dropout rates, and the documentation in §6.3 of `DATA_AND_MODEL_DOCUMENTATION.md` correctly flags `time_to_dropout` as synthetic. The caveat above must be carried into the Phase 5 limitation registry.

---

## D. `wasted_spend_per_pt` semantics

**Current state.** `cost_effectiveness.csv` reports `wasted_spend_per_pt = annual_drug_cost * (1 - adherence_rate)`, i.e., the fraction of annual GLP-1 spend "wasted" on patients who drop out.

| Cluster | wasted_spend_per_pt | annual_cost × (1 − adherence) | Match? |
|---|---|---|---|
| 0 | $7,493 | $9,457 × 0.7923 = $7,494 | ✅ |
| 1 | $6,988 | $10,106 × 0.6915 = $6,988 | ✅ |
| 2 | $2,334 | $15,938 × 0.1465 = $2,335 | ✅ |
| 3 | $4,632 | $7,800 × 0.5939 = $4,632 | ✅ |

Math is internally consistent.

**Issue with framing.** "Wasted spend" assumes the dropped-out patient stops accruing GLP-1 cost at dropout — but the existing CEA does not prorate `avg_annual_cost` by `time_to_dropout`. A patient who drops at day 30 is treated as costing a full year of drug ($9.5k–$16k) for the purpose of "wasted spend," not the prorated $0.8k–$1.3k they actually consumed.

**Why this matters for the consequence model.** The Payer ROI Synthesizer must:

1. Either redefine `wasted_spend` as prorated drug cost up to dropout, OR
2. Explicitly use it as an upper-bound illustrative figure and label it as such in dashboard tooltips.

The latter is acceptable for MVP messaging ("up to $X is at risk per dropout patient") but cannot anchor the consequence model's drug-side cost input. Use the prorated cost (`annual_drug_cost × time_to_dropout / 365`) for ROI math.

**Status: FLAG** — math is correct under stated definition but the definition is misleading for downstream ROI use.

---

## E. ICER values vs. comparators

**Current state.** `icer_by_segment.csv` reports two negative ICERs for the HbA1c outcome (clusters 0 and 1 vs. insulin glargine, cluster 3 vs. insulin glargine; cluster 0 vs. SGLT2: $166,208).

**Reasoning.** A negative ICER (incremental cost-effectiveness ratio) means either:
- GLP-1 is **dominated** (more expensive AND less effective than comparator) — bad
- GLP-1 is **dominant** (less expensive AND more effective) — good

Inspecting cluster 0 vs. insulin glargine:
- ΔCost = $9,457 − $3,500 = +$5,957
- ΔHbA1c = 0.822 − 1.5 = −0.678 (GLP-1 is LESS effective at HbA1c reduction because cluster 0 has high dropout, so `effective_hba1c_reduction` is small)
- ICER_HbA1c = $5,957 / −0.678 = −$8,786 → GLP-1 is dominated (more cost, less effect)

This is correct math but a confusing presentation. The negative sign hides the "dominated" interpretation behind a number that looks finite. Most insurers expect ICER ≥ $0 with a footnote when GLP-1 is dominated.

**Why this matters for the consequence model.** The downstream cost model will eventually re-rank these comparators by including avoided complication cost — at which point GLP-1's apparent disadvantage in HbA1c reduction (driven by dropout in low-adherence clusters) is offset by the long-horizon complication-avoidance savings. The Phase 3 ROI output should make this explicit ("GLP-1 looks dominated at 1 year, dominant at 5 years"), which is the entire point of the consequence model.

**Status: PASS** — math is correct, but the dashboard should re-label negative ICERs as "dominated" or "dominant" plainly in the consequence-model output.

---

## Audit Summary

| Item | Verdict | Action before consequence model build |
|---|---|---|
| A. `avg_annual_cost` per cluster | FLAG | Use registry per-molecule WAC + cluster mix in ROI; surface mix as "randomly assigned" |
| B. 15% dropout reduction + $500 intervention | **FAIL** | Do not propagate. Replace with model-derived uplift + user-configurable slider |
| C. Exponential `time_to_dropout` λ | PASS w/ caveat | Add Phase-1 sensitivity comparing `time_to_dropout` vs. day-180 entry |
| D. `wasted_spend_per_pt` semantics | FLAG | Use prorated drug cost in ROI; relabel current metric in dashboard tooltip |
| E. Negative ICERs | PASS | Relabel as "dominated"/"dominant" in consequence-model UI |

**One blocking issue (Item B).** The 15% dropout reduction and $500 intervention cost are unsourced placeholders that should not be carried forward into the consequence model. Phase 3 of the plan already specifies model-derived adherence uplift and a user-configurable slider — the audit confirms this is necessary, not optional.

All other items are addressable through (a) documentation in dashboard tooltips, (b) sensitivity analyses already scoped into Phase 1–2, or (c) limitation entries in the Phase 5 documentation update.

**Audit verdict: Proceed to Phase 1.** No structural rework of existing CEA pipeline is required, but the audit flags above must be reflected in the consequence-model implementation choices.
