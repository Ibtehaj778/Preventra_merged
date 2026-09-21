# Consequence Model — Phase 4 Progress (Weeks 7–8 Complete)

**Plan reference:** [CONSEQUENCE_MODEL_IMPLEMENTATION_PLAN.md](../CONSEQUENCE_MODEL_IMPLEMENTATION_PLAN.md) §Phase 4
**Status:** Phase 4 complete. Weeks 1–8 of the 9-week plan delivered. Ready for Phase 5 (Validation & Documentation, Week 9).

This document consolidates Weeks 7–8. Week 7 detail lives in [phase_4_week_7_progress.md](phase_4_week_7_progress.md) for reference; this is the canonical Phase 4 recap.

---

## Scope

Build the "Cost of Inaction" React screen: one route, three panels — Downstream Cost, Metabolic Rebound, Payer ROI — fully wired to the Consequence Model endpoints delivered in Phases 1–3. All numbers are live from Mongo Atlas; no hardcoded mocks in the new components.

---

## Convention alignment

The plan proposes a `screens/ConsequenceModel/` folder and a separate `api/consequenceApi.js`. Existing project uses `pages/` + a single centralised `data/api.js` (see [Frontend/src/pages/BudgetSimulator.jsx](../../Frontend/src/pages/BudgetSimulator.jsx)). Followed the existing convention rather than the plan's suggested layout — keeps the new screen structurally identical to Budget Simulator, so a future maintainer doesn't have to learn two patterns.

---

## Files added (initial Week 7–8 pass + follow-up extensions)

```
evidence/                                       ← NEW (Extension B — payer-type toggle)
  overrides/
    README.md                                   ← pattern documentation
    medicare_2028.csv                           ← Medicare-negotiated pricing (5 rows)
    post_generic.csv                            ← post-2032 biosimilar pricing (5 rows)

Model/consequence/
  registry.py                                   ← NEW — shared layered loader with load_registry(payer_type)
  payer_roi.py                                  ← extended: iterates all payer_types, yearly 1..10 horizons

Frontend/src/
  data/api.js                                   ← +4 wrappers (getPayerScenarios added, getPayerROI takes payerType)
  hooks/
    useDownstreamCost.js                        ← new
    useReboundRisk.js                           ← new
    usePayerROI.js                              ← new (debounced 250 ms on (interventionCost, payerType))
  pages/CostOfInaction/
    index.jsx                                   ← screen root + sticky sub-nav + scroll-spy
    DownstreamCostPanel.jsx                     ← Panel 1
    ReboundRiskPanel.jsx                        ← Panel 2
    PayerROIPanel.jsx                           ← Panel 3 (+segmented control, +trajectory chart, +coverage bar)
  components/charts/
    CostDriverStackedBar.jsx                    ← new
    ReboundTrajectoryChart.jsx                  ← new
    ROIBarChart.jsx                             ← new (extended to 4 horizons with 10-year)
    ROITrajectoryChart.jsx                      ← NEW (Extension A — 10-year trajectory line chart)
  components/layout/AppShell.jsx                ← +sidebar entry, restructured section slicing
  App.jsx                                       ← +route /consequence

Backend/
  schemas/consequence.py                        ← +cost_by_driver_5yr field
                                                ← +PayerROIYearlyPoint (10-yr trajectory series)
                                                ← +yearly_roi_series list on PayerROICluster
                                                ← +population_roi_10yr
  routers/consequence.py                        ← aggregate driver breakdown per cluster
                                                ← +GET /payer-scenarios discovery endpoint
                                                ← +payer_type query param on /payer-roi with fallback
                                                ← _PRIMARY_HORIZONS extended to (1, 3, 5, 10)
                                                ← _YEARLY_HORIZONS = (1..10) for trajectory
  scripts/migrate_csv_to_mongo.py               ← compound unique index (payer_type, cluster)
                                                ← compound unique index (payer_type, cluster, horizon_years)
```

---

## Backend addition (Week 7)

The `GET /api/consequence/downstream-cost` response now includes a per-cluster `cost_by_driver_5yr` breakdown that Panel 1's stacked bar needs. Minimal change: aggregate `cost_share_esrd_5yr × expected_downstream_cost_5yr` per cluster (and same for CV, T2D) in the router. No Mongo re-migration — the data was already in `progression_cost`, the router just wasn't projecting it before.

---

## Screen structure

```
CostOfInaction/index.jsx
├── Clinician view banner              (green, appears only when role=clinician)
├── Framing banner "Cost of Inaction"  (orange)
├── Sticky sub-nav                     (scroll-spy: Downstream Cost / Rebound / ROI)
├── DownstreamCostPanel                (Panel 1)
├── ReboundRiskPanel                   (Panel 2)
└── PayerROIPanel                      (Panel 3)
```

Sub-nav uses `IntersectionObserver` to update the active tab as the user scrolls; clicking a sub-nav item smooth-scrolls to that panel. No react-router sub-routes — all three panels are on one page for the narrative flow.

Sidebar restructured: previously `Overview (2)` + `Analytics (3, including Budget)`. Now `Overview (2)` + `Analytics (2)` + **`Financial (2 — Budget Simulator + Cost of Inaction)`** with the insurer "Primary" badge that was previously commented out.

---

## Panel 1 — Downstream Cost (Week 7)

- Header row: 3 KPI cards (Population exposure, Avg cost per patient, Top cost driver) driven by `population_total_5yr` / `_10yr` and `primary_cost_driver_distribution`.
- 5-year / 10-year horizon toggle switches all card values (no re-fetch — both horizons in the same payload).
- Stacked bar chart via `CostDriverStackedBar.jsx`, one bar per cluster, three coloured segments (Uncontrolled T2D blue, CV event orange, ESRD red). Legend at bottom. Hover tooltip shows dollar amount + driver label.
- Four per-cluster cards below the chart with avg cost, ESRD@5yr%, CV@5yr%. Border-top colour matches cluster.

**What it communicates:** Cluster 1 (Financial Barrier) has the highest downstream cost at ~$55k/5yr. Cluster 0 (Low Urgency) is lowest at ~$40k — normal-baseline patients accrue less complication cost. Top cost driver population-wide is Uncontrolled T2D (64%), CV event second (36%), ESRD negligible over 5 years (chained transitions take longer than the horizon).

---

## Panel 2 — Metabolic Rebound Risk (Week 7)

- Header includes scenario toggle (Early Day 30 / Median / Late Day 150). Toggle affects the entire panel — chart + gauges + probability cards — with zero network requests (all scenarios already in initial payload).
- `ReboundTrajectoryChart.jsx`: one line per cluster over months 0–12; reference lines at 6.5 (ADA T2D threshold, orange) and 8.0 (uncontrolled, red).
- Four severity gauge cards with a custom SVG radial ring. Colour thresholds per plan spec: green <0.3, amber 0.3–0.6, red >0.6. Score displayed inside the ring; "Low/Moderate/High" badge next to it.
- Each card shows `p_new_t2d_12mo` (pre-DM patients) and `p_uncontrolled_12mo` (T2D patients) from the currently-selected scenario. Fields show `—` when the cluster has no patients in that DM stratum.
- Bottom banner shows population-level 12-month T2D incidence (~5.8%).

**What it communicates:** The scenario toggle is the payload. Under **Median**, Cluster 2 (Strong Adherer) has the highest severity — counterintuitive but correct: they had the most benefit to lose. Under **Early**, all clusters have low severity because dropouts before day-30 barely attained the trial reduction. That's the dashboard's "the first 90 days matter most" story, quantified.

---

## Panel 3 — Payer ROI (Week 8, initial pass)

> **Note:** this section describes the initial Week-8 Panel 3. Two follow-up extensions landed after — a **10-year horizon + trajectory line chart** and a **payer-type toggle** with layered override registry. See [Extensions delivered after the initial recap](#extensions-delivered-after-the-initial-recap) and the [Metrics reference — Panel 3](#metrics-reference--panel-3) below for the current state of the panel. This section is preserved for context on the initial design intent.

- Panel opens with a blue "Read this first" framing banner — negative 5-yr ROI is expected on pure cost-avoidance math; the useful signals are break-even adherence and intervention headroom, not the raw ROI number. Direct references limitation #20 in [DATA_AND_MODEL_DOCUMENTATION.md](../DATA_AND_MODEL_DOCUMENTATION.md).
- **Intervention cost slider** (Radix Slider) — $0 → $3,000, step $50. Slider value drives `usePayerROI(interventionCost)`; the hook re-fetches `/api/consequence/payer-roi?intervention_cost=<x>` with a 250 ms debounce. Verified round-trip via curl at 4 slider positions ($0/$500/$1,500/$3,000): Cluster 1's 5-yr ROI moves −0.72 → −0.76 → −0.84 → −0.95, monotonically.
- **Population summary strip** — 4 KPI cards: 1/3/5-year population ROI (weighted across clusters, colour-coded green/red by sign) + current intervention slider value. *(Extension A later replaced the 3-yr card with a 10-yr card.)*
- `ROIBarChart.jsx`: grouped bar per cluster showing ROI at 1/3/5-year horizons in light → medium → dark blue. Green dashed `ReferenceLine` at ROI=0. *(Extension A added a 4th (10-yr) bar.)*
- **Per-cluster cards** — each shows:
  - ROI badge (green/red pill) with 5-year ROI value *(Extension A added a 10-yr badge)*
  - **Break-even adherence block** (grey card) — either "0.65" with the current adherence gap ("Current: 0.31 · Gap: +34.6%"), OR "Unreachable" with the "cost avoidance is the wrong ROI lens" copy for clusters where on-therapy savings never cover drug cost (Cluster 2 in this cohort).
  - Intervention headroom (color-coded green if positive, red if negative)
  - Annual drug cost + 5-yr expected drug spend

**What it communicates:** Break-even α is the actionable number. Cluster 1 needs +34.6 points of adherence to break even at 5 years — that's the payer intervention story. Cluster 3 needs +19 points. Cluster 2's break-even is unreachable — "for these patients GLP-1 pays off in QALY, not claims." Cluster 0 also unreachable — "wrong drug for these patients."

---

## Sanity check — endpoint round-trip (via curl, backend booted on port 8765)

**Initial Week-8 slider round-trip** (payer_type='current'):

```
intervention=$0     → pop_roi_5yr=-0.8238  · cluster1 roi_5yr=-0.7214
intervention=$500   → pop_roi_5yr=-0.8473  · cluster1 roi_5yr=-0.7603
intervention=$1500  → pop_roi_5yr=-0.8944  · cluster1 roi_5yr=-0.8381
intervention=$3000  → pop_roi_5yr=-0.9651  · cluster1 roi_5yr=-0.9548

intervention_cost_threshold_5yr for cluster1 stays -$9,271 across all values — correct;
threshold is "max spend headroom" independent of current spend.
```

**Post-extension payer-type round-trip** (intervention=$500):

```
current        → pop_roi_5yr=-0.847  pop_roi_10yr=-0.758  all clusters "never" cross
medicare_2028  → pop_roi_5yr=-0.717  pop_roi_10yr=-0.550  all clusters "never" (c3 gets to -0.17)
post_generic   → pop_roi_5yr=-0.068  pop_roi_10yr=+0.479  c3 crosses at 2.5yr, c1 at 3.1yr, c2 at 6.8yr
```

**Regression check** (unchanged pre + post extensions):

```
/api/summary                       OK
/api/consequence/downstream-cost   OK
/api/consequence/rebound-risk      OK
/api/consequence/payer-scenarios   OK (new discovery endpoint)
/api/consequence/payer-roi         OK (with payer_type + intervention_cost params)
```

Frontend `npx vite build` clean at both milestones: 776 kB / 224 kB gzipped, no errors, no runtime warnings.

---

## What to verify locally

Run these two commands in separate terminals from the project root:

```bash
# Terminal 1 — backend
cd Backend
PYTHONIOENCODING=utf-8 venv/Scripts/python.exe -m uvicorn main:app --reload

# Terminal 2 — frontend
cd Frontend
npm run dev
# Vite prints the local URL (default http://localhost:5173)
```

Panels 1 and 2 checklist is in [phase_4_week_7_progress.md](phase_4_week_7_progress.md). New Week-8 verifications for Panel 3:

**Framing banner (top of Panel 3)**
- [ ] Blue "Read this first" banner renders with the "5-year ROI is expected to be negative" copy.

**Intervention slider**
- [ ] Slider defaults to $500; the value badge next to the label reads "$500".
- [ ] Dragging the thumb visibly updates the badge in real time.
- [ ] 250 ms after you stop dragging, all KPI cards, the bar chart, and per-cluster cards refresh.
- [ ] DevTools Network tab: dragging fires exactly one request 250 ms after you release (not one per pixel).
- [ ] `$0` and `$3000` are reachable (min/max bounds).

**Population summary strip**
- [ ] 4 KPI cards: 1-yr, 3-yr, 5-yr population ROI + current intervention slider value.
- [ ] All three ROI values are negative and coloured red at $500. At $3000 they get more negative.

**Grouped bar chart**
- [ ] 4 clusters × 3 bars each. Colour is light blue → medium blue → dark blue as horizon grows.
- [ ] Green dashed `ROI = 0` reference line spans the chart width with a "Break-even" label on the right.
- [ ] All bars are below the reference line (negative ROI). Longer horizons are less negative (bars closer to zero).
- [ ] Hover any bar → tooltip shows the ROI value with 2 decimals.

**Per-cluster cards**
- [ ] Each card has a coloured border-top matching the cluster.
- [ ] ROI pill in the top-right — red for all 4 clusters at default $500 intervention.
- [ ] Break-even block:
  - Cluster 1 (Financial Barrier) shows "67.6%" with "Current: 30.8% · Gap: +36.9%".
  - Cluster 2 (Strong Adherer) shows "Unreachable" copy.
  - Cluster 0 (Low Urgency) shows "Unreachable" copy (break-even α > 1).
  - Cluster 3 (Moderate) shows "62.8%" with "Current: 40.6% · Gap: +22.2%".
- [ ] Intervention headroom values are negative and coloured red (drug spend exceeds gross benefit).

**Extension A checks (10-yr horizon + trajectory chart)**
- [ ] Grouped bar chart has **4 bars** per cluster (not 3) — a very-dark-blue 10-yr bar sits to the right of the 5-yr bar.
- [ ] Population strip's third KPI card is labeled "**Population 10-yr ROI**" (previously 3-yr).
- [ ] A **10-year ROI trajectory** line chart appears below the bar chart, with 4 lines and a green ROI=0 reference line.
- [ ] Per-cluster cards show TWO ROI badges (5yr + 10yr).
- [ ] Per-cluster cards have a **10-yr cost-coverage bar** with a percentage label. Under `current` scenario: Cluster 3 shows 47%, Cluster 0 shows 6%.

**Extension B checks (payer-type toggle)**
- [ ] Panel 3 header has a **Pricing scenario** segmented control with 3 buttons (Current 2025 / Medicare 2028 / Post-generic 2032+).
- [ ] Clicking a scenario updates all the numbers within ~250 ms and changes the framing-banner copy at the top.
- [ ] Under **Post-generic 2032+**:
  - Population 10-yr ROI KPI turns green (+0.48).
  - Cluster 1, 2, and 3 ROI badges show mixed green/amber values (crossed positive at some horizons).
  - The trajectory chart shows Cluster 3's line crossing above the ROI=0 line around year 2–3.
  - The framing banner copy mentions "three of four clusters flip positive within 3–7 years."
- [ ] DevTools Network tab: each scenario click fires exactly one request to `/api/consequence/payer-roi?payer_type=<id>&intervention_cost=<usd>`.

**Regression**
- [ ] Executive Summary, Patients, Segments, Survival, Budget Simulator all still load.
- [ ] No red errors in DevTools Console.

If anything looks off, flag it and I'll fix before Phase 5.

---

## Combined chart component inventory

| Component | Used by | Notes |
|---|---|---|
| `CostDriverStackedBar` | Panel 1 | 4 clusters × 3 stacked drivers |
| `ReboundTrajectoryChart` | Panel 2 | 4 clusters × 5 months, 2 reference lines |
| `ROIBarChart` | Panel 3 | 4 clusters × **4 horizons** (1/3/5/10-yr), 1 reference line |
| `ROITrajectoryChart` | Panel 3 | 4 clusters × 10 years, 1 reference line (Extension A) |

All three follow the same conventions: `ChartTooltip` from `components/shared`, colours from `SEGMENT_COLORS`, small (11 px) axis text, `ResponsiveContainer` sizing. They can be imported by any future page that wants the same visual.

---

## Framing summary — what the whole screen tells a payer

The three panels form a top-to-bottom narrative:

1. **Panel 1 — Problem.** "If everyone dropped, you'd absorb $370M in downstream cost over 5 years."
2. **Panel 2 — Mechanism.** "The rebound risk depends on how long they stayed. Strong adherers have the largest rebound if they stop."
3. **Panel 3 — Constraint (and how it lifts over time).**
   - Under today's commercial pricing, cost avoidance alone doesn't cover the drug within a payer-cycle horizon. The 10-year cost-coverage bars quantify how close each cluster gets: Cluster 3 (best trajectory) recovers **47%** of its drug spend through avoided complications by year 10.
   - Under **Medicare 2028** negotiated pricing (~65% discount), Cluster 3 approaches break-even at year 10 (−0.17). The trajectory line chart shows the shape of that climb.
   - Under **Post-generic 2032+** pricing, three of four clusters cross positive between years 2 and 7. Cluster 3 crosses at year 2.5.

The negative-5yr-ROI story under `current` is the honest version. Prior GLP-1 dashboards often either (a) show optimistic net-present-value numbers by extending to 15 years without acknowledging uncertainty, or (b) hide the raw ROI behind QALY math. This screen does neither. It shows the payer exactly what the money looks like at three defensible pricing environments, on a 10-year trajectory, so the question shifts from "does GLP-1 pay off?" (a binary that ignores time) to "**when does it pay off, and how does that shift with pricing?**" — a much stronger payer conversation.

---

## Phase 4 accomplishments — running scorecard

- 3 new hooks with parameter-driven refetch semantics (usePayerROI is the interesting one — debounced 250 ms).
- 3 reusable chart components in `components/charts/` (this folder was previously empty).
- 3 panels (~800 total lines JSX) + 1 screen root with sticky sub-nav.
- 1 new backend field (`cost_by_driver_5yr`) added surgically without Mongo re-migration.
- 0 changes to existing pages/hooks — no regression risk to Phases 1–3 work.
- Frontend build stays at 224 kB gzipped (up from ~210 kB) — no bloat from new dependencies (Radix Slider was already installed).

---

## Extensions delivered after the initial recap

Two follow-up extensions landed on Panel 3 after the initial Week-8 pass, driven by the user question "why is ROI always negative and how do we make it positive?":

### Extension A — 10-year horizon + trajectory line chart

- **`payer_roi.py`** `YEARLY_HORIZONS` extended from `(1..5)` to `(1..10)`. `PRIMARY_HORIZONS` (used by the bar chart and per-cluster reporting) extended from `(1, 3, 5)` to `(1, 3, 5, 10)`.
- **Backend**: `PayerROICluster` schema now carries a `yearly_roi_series: List[PayerROIYearlyPoint]` (10 points, year 1..10) alongside the primary horizons list. `population_roi_10yr` added. `time_to_positive_roi_years` now interpolates across all 10 years (previously 5).
- **Frontend**: new [ROITrajectoryChart.jsx](../../Frontend/src/components/charts/ROITrajectoryChart.jsx) — line chart, 1 line per cluster, x = year 1..10, y = ROI, green dashed reference at ROI=0. Renders below the grouped bar chart on Panel 3.
- **Per-cluster cards** grew a **10-year cost-coverage bar** — visual progress bar showing what fraction of cumulative drug cost is offset by avoided complications at year 10. Colour-graded red (<50%) → amber (50–99%) → green (≥100%). This is the honest "how close to break-even" signal that doesn't depend on the mathematically-brittle break-even-α approximation.
- The `ROI` badge on each per-cluster card became a pair — showing 5-yr AND 10-yr side by side.

**Coverage values under the `current` scenario** — the "why negative" evidence:

| Cluster | Δ (avoided cost, 10yr) | Drug spend (10yr) | Coverage | ROI 10yr |
|---|---|---|---|---|
| 0 — Low Urgency | $4,515 | $14,547 | **6%** | −0.97 |
| 1 — Financial Barrier | $29,889 | $22,359 | **41%** | −0.61 |
| 2 — Strong Adherer | $19,980 | $79,419 | **21%** | −0.79 |
| 3 — Moderate | $25,722 | $22,243 | **47%** | −0.55 |

Cluster 3's 47% is the "closest to payoff" number under today's economics. To flip Cluster 3 positive at 10 years, the ratio needs to double.

### Extension B — Payer-type toggle (layered registry)

**Motivation:** the negative-ROI story is real under today's commercial pricing but flips under Medicare 2028 negotiated prices and again under post-2032 generics. Making that dimension user-controllable turns "does GLP-1 pay off?" into "when does it pay off?" — much stronger for a payer conversation.

**Design pattern chosen:** layered override registry, not hardcoded conditionals. Extensibility matters because real-payer contract data will land here later, and every new payer contract should be adding a CSV, not writing code.

- **New directory `evidence/overrides/`**:
  - [`medicare_2028.csv`](../evidence/overrides/medicare_2028.csv) — projected CMS-negotiated GLP-1 prices (~65% off WAC, based on the observed discount in the 2026 negotiation results). Sets `glp1_payer_net_rebate_fraction=0` to avoid double-discounting.
  - [`post_generic.csv`](../evidence/overrides/post_generic.csv) — projected biosimilar pricing (2032+ post-patent expiry). Semaglutide $1,500/yr, tirzepatide $1,750/yr, older molecules ~$900/yr.
  - [`README.md`](../evidence/overrides/README.md) — pattern documentation.
- **[Model/consequence/registry.py](../../Model/consequence/registry.py)** (new) — shared `load_registry(payer_type)` loader that reads the base then merges any override with matching parameter names. Both `downstream_cost.py` and `payer_roi.py` now import from here — single source of truth for registry loading.
- **`payer_roi.py`** refactored: `main()` iterates all scenarios discovered by `available_payer_types()` and writes tagged CSVs (`payer_roi.csv` = 12 rows × payer_type-tagged, `payer_roi_yearly.csv` = 120 rows). Cost of a new scenario = one CSV; no code path change.
- **Migration** — compound unique indexes on `(payer_type, cluster)` and `(payer_type, cluster, horizon_years)`.
- **Backend**:
  - `GET /api/consequence/payer-scenarios` — discovery endpoint. Returns `{scenarios: [...], default: 'current'}` so the frontend doesn't hardcode the list.
  - `GET /api/consequence/payer-roi?payer_type=<id>&intervention_cost=<usd>` — filter added, unknown types fall back to `current`.
- **Frontend**:
  - [`usePayerROI(interventionCost, payerType)`](../../Frontend/src/hooks/usePayerROI.js) — hook now debounces on either input.
  - Panel 3 gained a **Pricing scenario** segmented control in the section header (Radix-style, 3 buttons).
  - Framing banner copy is scenario-specific (`current` → "negative, here's why"; `medicare_2028` → "approaching zero"; `post_generic` → "3 of 4 clusters flip positive by year 3–7").

**Endpoint verification** (curl against Atlas, `intervention_cost=$500`):

| Scenario | Pop 5-yr ROI | Pop 10-yr ROI | Cluster crossings (time-to-positive) |
|---|---|---|---|
| `current` | −0.847 | −0.758 | all "never" |
| `medicare_2028` | −0.717 | −0.550 | all "never" (c3 gets to −0.17) |
| **`post_generic`** | **−0.068** | **+0.479** | **c3: 2.5yr · c1: 3.1yr · c2: 6.8yr · c0: never** |

The `post_generic` numbers under Cluster 3 (crosses positive at year 2.5, ROI = +1.91 at year 10) are the ones that turn Panel 3 from a "why doesn't it work?" screen into a "when does it work?" screen.

**Adding a future scenario** is now a 4-file workflow (0 code changes required):
1. `cp evidence/overrides/medicare_2028.csv evidence/overrides/my_new_scenario.csv` and edit values
2. `python -m Model.consequence.payer_roi` (regenerate all scenarios)
3. `python -m scripts.migrate_csv_to_mongo` (push tagged docs)
4. Add `{id:'my_new_scenario', label:'...', sub:'...'}` to `PAYER_SCENARIOS` in `PayerROIPanel.jsx`

---

## Metrics reference — Panel 3

Same structure as the Panels 1 & 2 reference in [phase_4_week_7_progress.md](phase_4_week_7_progress.md). Every visible element with its backend source, current values under the three scenarios, and interpretation.

Common terms:
- **α** = cluster adherence probability, from `is_adherent.mean()` per cluster in the source data. Values: c0=0.208, c1=0.308, c2=0.854, c3=0.406.
- **D** = per-patient net annual GLP-1 drug cost. Molecule-mix weighted per cluster.
- **Δ** = `downstream_dropout − downstream_adherent`, the per-patient complication cost avoided by staying on therapy.
- **annuity(t, r)** = `Σ_{i=0..t-1} 1/(1+r)^i`, discount-weighted annuity factor. r = 3%.
- **All ROI values below are under intervention_cost = $500 (the slider default).**

### Framing banner (top of Panel 3)

| Element | Source | What it shows |
|---|---|---|
| Blue framing card with "Read this first" | Client-side, scenario-conditional | Copy that changes with `payerType` state — one paragraph per scenario explaining what the current numbers mean and where the story lives. Under `current`, points at the coverage ratio and break-even gap; under `post_generic`, calls out the crossover years directly. |

### Pricing scenario segmented control

| Button | ID | Sub-label | Data source |
|---|---|---|---|
| **Current (2025)** | `current` | Commercial WAC × (1 − 0.35 rebate) | Base registry `evidence/parameter_registry.csv` |
| **Medicare 2028** | `medicare_2028` | Projected CMS negotiation (~65% discount) | Override `evidence/overrides/medicare_2028.csv` (5 rows) |
| **Post-generic 2032+** | `post_generic` | Biosimilar entry (~$1,500/yr net) | Override `evidence/overrides/post_generic.csv` (5 rows) |

Clicking a button updates local `payerType` state; the `usePayerROI` hook debounces 250 ms then re-fetches `/api/consequence/payer-roi?payer_type=<id>&intervention_cost=<slider>`. Server-side, the endpoint filters by `payer_type` in the `payer_roi` Mongo collection (compound unique index on `(payer_type, cluster)`).

### Intervention cost slider

| Element | Source | Range / behavior |
|---|---|---|
| Slider (Radix Slider) | Local state `interventionCost` | `$0 – $3000`, step `$50`, default `$500`. Debounced 250 ms into `usePayerROI`. |
| Displayed value badge | Slider state, `fmtMoney` | Updated instantly on drag (no wait for API response). |

### Population summary KPI strip (4 cards)

| KPI | Displayed value example (`current` scenario) | Source | Calculation | Interpretation |
|---|---|---|---|---|
| **Population 1-yr ROI** | −0.995 | `PayerROIResponse.population_roi_1yr` | Server-side `_population_roi_from_docs(docs, 1, intervention_cost)`: `(Σ n × (gross_1yr − drug_1yr − intervention)) / (Σ n × drug_1yr)` weighted by cluster patient count. | Near −1 because year-1 barely accumulates any avoided complications while ~1 year of drug cost is fully accrued. |
| **Population 5-yr ROI** | −0.847 | `population_roi_5yr` | Same formula, horizon=5 | The plan's primary payer-cycle horizon. |
| **Population 10-yr ROI** | −0.758 | `population_roi_10yr` | Same formula, horizon=10 | Sensitivity horizon. Under `post_generic` this flips to **+0.479** — the headline "GLP-1 pays off long-term" number. |
| **Intervention** | $500 | Slider state | — | Current spend level driving the ROI calculation. |

Colour rules: green when ROI ≥ 0, red under `current`, amber if between −0.3 and 0 (near break-even). Icons: AlertCircle / Target / TrendingUp / DollarSign.

Values under `post_generic`: 1-yr = **−1.28**, 5-yr = **−0.07**, 10-yr = **+0.48** — the sign flip at 10 years is the payoff story.

### ROI grouped bar chart

Component: [ROIBarChart.jsx](../../Frontend/src/components/charts/ROIBarChart.jsx). 4 clusters on the x-axis, 4 grouped bars per cluster.

| Series | Colour | Data source |
|---|---|---|
| 1-yr | `#BFDBFE` (very light blue) | `horizons[?horizon_years==1].roi` per cluster |
| 3-yr | `#60A5FA` (light blue) | same, horizon 3 |
| 5-yr | `#2563EB` (medium blue) | same, horizon 5 |
| **10-yr** | `#1E3A8A` (dark blue) | same, horizon 10 — visually the darkest and largest under `post_generic` |
| Reference line | Green dashed `#2E7D32` at y=0 | Static — "Break-even (ROI = 0)" label |

Reading the chart:
- Under `current`, all 16 bars are below the reference line.
- Under `medicare_2028`, the 10-yr bar for Cluster 3 gets close to zero (−0.17).
- Under `post_generic`, the 5-yr AND 10-yr bars for Clusters 1 and 3 rise above zero. Cluster 3's 10-yr bar hits **+1.91**.

### ROI trajectory line chart

Component: [ROITrajectoryChart.jsx](../../Frontend/src/components/charts/ROITrajectoryChart.jsx). 4 lines (one per cluster), x = year 1..10, y = ROI.

| Element | Source | Interpretation |
|---|---|---|
| 4 lines per cluster | `yearly_roi_series` per cluster in the API response (10 points each) | Reveals the *shape* of the ROI curve — is a cluster asymptoting or still climbing at year 10? |
| Green dashed reference at y=0 | Static | Same "Break-even" line as the bar chart. |
| Line colours | `SEGMENT_COLORS` (red/orange/green/blue for clusters 0/1/2/3) | Consistent with the rest of the dashboard. |

Reading the chart:
- **Under `current`:** all four lines climb monotonically but stay below zero. Cluster 0 is nearly flat (never gets meaningfully better). Cluster 3 climbs fastest.
- **Under `medicare_2028`:** the same shapes but shifted up; Clusters 1 and 3 approach zero by year 10.
- **Under `post_generic`:** dramatic difference. Cluster 3 crosses zero between years 2 and 3. Cluster 1 crosses between years 3 and 4. Cluster 2 crosses around year 7. Cluster 0 remains below zero throughout — GLP-1 economics never work for this cluster because they're not at complication risk.

### Per-cluster cards (4)

Border-top matches `SEGMENT_COLORS[cluster_id]`. Each card contains:

| Element | Source | Current values (Cluster 1 shown) | Interpretation |
|---|---|---|---|
| Cluster ID + label | `cluster_id`, `cluster_label` | "Cluster 1 · Financial Barrier Dropout Risk" | Cluster identity. |
| **5yr ROI badge** | `horizons[?horizon_years==5].roi` | −0.76 (red pill) | ROI at primary payer horizon. |
| **10yr ROI badge** | `horizons[?horizon_years==10].roi` | −0.61 (amber pill — negative but "warming") | Adds a second colour dimension: red = deeply negative, amber = near break-even, green = positive. |
| **Break-even adherence block** | `break_even_adherence_rate` | "67.6%" with "Current: 30.8% · Gap: +36.9%" | The α at which annual drug cost = per-patient avoided cost (1-year approximation). For clusters where break-even > 1, replaced with "Unreachable" copy explaining that cost avoidance is the wrong lens (Cluster 2 example). |
| **10-yr cost-coverage bar** | `horizons[?horizon_years==10].gross_benefit / .expected_drug_cost` | 41% (amber bar) | The honest "how close to break-even" signal. 100% = break-even at 10 yr. Values under all scenarios (Cluster 3, the best): current 47%, medicare_2028 62%, post_generic 145%. |
| Coverage note | Client-computed | "$9,220 avoided vs. $22,359 spent" | Direct dollar framing under the bar. |
| **5-yr headroom** | `intervention_cost_threshold_5yr` (client-recomputed as `gross_5 − drug_5`) | −$9,271 | Max additional spend at current adherence keeping ROI at its trajectory. Negative means already below break-even; positive would mean room to add intervention spend. |
| **Annual drug cost** | `avg_annual_drug_cost` | $7,575 | Per-molecule WAC × (1 − rebate) averaged across the cluster's molecule mix. Under `medicare_2028` this drops to ~$4,830; under `post_generic` to ~$1,500. |

### Per-cluster deep dive under `post_generic`

The story-flip scenario. Numbers straight from the endpoint:

| Cluster | Adherence α | Annual drug (net) | 5yr ROI | 10yr ROI | Time-to-positive |
|---|---|---|---|---|---|
| 0 — Low Urgency | 0.21 | $1,650 | −1.15 | −0.81 | never |
| 1 — Financial Barrier | 0.31 | $1,738 | **+0.48** | **+1.41** | **3.10 yr** |
| 2 — Strong Adherer | 0.85 | $1,732 | −0.16 | +0.25 | **6.81 yr** |
| 3 — Moderate | 0.41 | $1,326 | **+0.79** | **+1.91** | **2.52 yr** |

Read this table with the trajectory chart open: Cluster 3 is the payer's best-value target — it crosses to positive ROI in under 3 years post-generic even though its current adherence is only 41%.

---

## What's next — Phase 5 (Week 9)

The final phase closes the plan with validation and documentation, not new build work:

1. **End-to-end sanity checks** across the entire pipeline — from `GLP1_FINAL_WITH_SURVIVAL.csv` through `progression_cost.csv` → `rebound_risk.csv` → `payer_roi.csv`. Verify cluster orderings match the plan's directional expectations.
2. **Documentation freeze** — audit [DATA_AND_MODEL_DOCUMENTATION.md](../DATA_AND_MODEL_DOCUMENTATION.md) §10, confirm all parameters are traced back to `parameter_registry.csv`, resolve any TODOs.
3. **Demo script v2** — updated Insurer walkthrough that routes through the new Cost of Inaction screen. Suggested talking points already outlined in the plan §Phase 5.
4. **Stakeholder briefing note** — one-page internal memo covering what was built, headline numbers, and the next data milestone (real prescription-fill data replacing synthetic labels).

Phase 5 is 3–5 days of writing and validation. No new code beyond potentially a small sanity-check script.
