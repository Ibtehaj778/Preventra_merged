# Consequence Model — Phase 4 / Week 7 Progress

**Plan reference:** [CONSEQUENCE_MODEL_IMPLEMENTATION_PLAN.md](../CONSEQUENCE_MODEL_IMPLEMENTATION_PLAN.md) §Phase 4
**Status:** Week 7 deliverables complete. Week 8 (Payer ROI panel + slider + polish) pending.

---

## Scope for Week 7

Per the plan, Phase 4 (Dashboard Integration) spans Weeks 7–8. Split:

- **Week 7 → foundation + Panels 1 & 2:** API wiring, screen root, Downstream Cost panel, Rebound Risk panel.
- **Week 8 → Panel 3 + polish:** Payer ROI panel, intervention slider, framing narrative, end-to-end test.

Week 7 is what is finished as of this writing.

---

## Convention alignment

The plan proposes a `screens/ConsequenceModel/` folder and a separate `api/consequenceApi.js`. The existing project uses `pages/` + a single centralised `data/api.js` (see [Frontend/src/pages/BudgetSimulator.jsx](../../Frontend/src/pages/BudgetSimulator.jsx) and [Frontend/src/data/api.js](../../Frontend/src/data/api.js)). I followed the existing convention rather than the plan's suggested layout — this keeps the new screen structurally identical to Budget Simulator so a future maintainer doesn't have to learn two patterns.

Final layout:

```
Frontend/src/
  data/api.js                                  ← extended (3 new wrappers)
  hooks/
    useDownstreamCost.js                       ← new
    useReboundRisk.js                          ← new
    usePayerROI.js                             ← new (debounced re-fetch, ready for Week 8 slider)
  pages/CostOfInaction/
    index.jsx                                  ← screen root with sub-nav
    DownstreamCostPanel.jsx                    ← Panel 1
    ReboundRiskPanel.jsx                       ← Panel 2
    PayerROIPanel.jsx                          ← placeholder (Week 8 target)
  components/charts/
    CostDriverStackedBar.jsx                   ← new
    ReboundTrajectoryChart.jsx                 ← new
  components/layout/AppShell.jsx               ← sidebar entry added
  App.jsx                                      ← /consequence route registered
```

---

## Backend addition

The `GET /api/consequence/downstream-cost` response now includes a per-cluster `cost_by_driver_5yr` breakdown that Panel 1 needs for the stacked bar. Minimal change: aggregate `cost_share_esrd_5yr × expected_downstream_cost_5yr` per cluster (and same for CV, T2D) in the router, expose as `{ESRD, CV_event, Uncontrolled_T2D}` dict on each cluster. No Mongo re-migration required — the data was already in the `progression_cost` collection; the router just wasn't projecting it before.

Backend files touched:
- [Backend/schemas/consequence.py](../../Backend/schemas/consequence.py) — added `cost_by_driver_5yr: Dict[str, float]` to `DownstreamCostCluster`
- [Backend/routers/consequence.py](../../Backend/routers/consequence.py) — aggregation logic in the same loop that already computed `sum5`, `sum_esrd`, etc.

Verified via curl against Mongo Atlas — Cluster 1 breakdown is `{ESRD: $232, CV_event: $5,428, Uncontrolled_T2D: $29,742}` per patient at 5 years. That composition is consistent with the Phase 1 sanity check (T2D-driven cluster).

---

## Panel 1 — Downstream Cost

- Horizon toggle (5-year / 10-year) drives KPI card values and per-cluster amounts.
- KPI row: population exposure at horizon, average per patient, top cost driver (population share).
- Stacked bar chart per cluster, colour-coded by driver:
  - **Uncontrolled T2D** (blue) — largest bucket, drives ~64% of population risk.
  - **CV event** (orange) — second bucket, ~36%.
  - **ESRD** (red) — small bucket in 5-year window (0.01–0.25% of patients).
- Per-cluster cards with ESRD@5yr and CV@5yr probability alongside the average dollar figure.
- Loading skeletons and error state for offline backend.

### What the panel communicates

Cluster 1 (Financial Barrier) shows the highest downstream cost at ~$55k/patient over 5 years. Cluster 0 (Low Urgency) shows the lowest at ~$40k, because their baseline HbA1c is normal — GLP-1 dropout has less consequence for a patient who was never at complication risk to begin with. This is a real, useful insight: the payer's exposure is concentrated in the moderate-to-high HbA1c clusters.

---

## Panel 2 — Metabolic Rebound Risk

- Scenario toggle (Early Day 30 / Median / Late Day 150) drives the trajectory chart and severity-gauge values.
- HbA1c line chart, one line per cluster, months 0–12, with reference lines at 6.5 (ADA T2D threshold) and 8.0 (uncontrolled). `connectNulls` handles the case where a scenario has no data.
- Custom SVG radial gauge for severity score per cluster (colour-coded green/amber/red at 0.3 and 0.6 breakpoints, exactly as the plan spec asked). Score displayed inside the ring.
- Cluster cards include p_new_t2d_12mo (for pre-DM patients in the cluster) and p_uncontrolled_12mo (for T2D patients). Both come from the sensitivity payload so they update as the scenario toggle changes.
- Bottom banner: population-level 12-month T2D incidence (weighted across pre-DM patients).

### What the panel communicates

The **scenario toggle** is where the payer insight lives. Switching from Early to Late reveals two facts at once:

1. Late-dropout patients rebound to a *lower* HbA1c at 12 months than early-dropout patients — because 34% of a larger on-therapy gain is more durable retained benefit than 34% of a smaller one. This is consistent with STEP-1 extension data and is captured by a unit test in Phase 2.
2. Cluster 2 (Strong Adherer) shows the highest severity across all scenarios. Counterintuitive at first glance, but correct: they had the most benefit to lose. This is the "if these patients stopped, you'd lose the most" framing.

---

## Sidebar + routing

- Added `AlertTriangle` icon import from `lucide-react`.
- New `NAV_ITEMS` entry: `{ to: '/consequence', icon: AlertTriangle, label: 'Cost of Inaction', primary: 'insurer' }`.
- Restructured sidebar sections: Overview (2), Analytics (2), **Financial (2 — Budget Simulator + Cost of Inaction)** with insurer badge. Previously "Financial" was commented out; it's now active.
- New route registered in [App.jsx](../../Frontend/src/App.jsx).

### Sidebar structure detail

The `NAV_ITEMS` array in [components/layout/AppShell.jsx](../../Frontend/src/components/layout/AppShell.jsx) is sliced into three sidebar sections by index range:

| Section header | Slice | Items | Section labelling |
|---|---|---|---|
| **OVERVIEW** | `NAV_ITEMS.slice(0, 2)` | Executive Summary, Patient Risk Panel | Plain label |
| **ANALYTICS** | `NAV_ITEMS.slice(2, 4)` | Segment Explorer, Survival Analysis | Plain label |
| **FINANCIAL** | `NAV_ITEMS.slice(4, 6)` | Budget Simulator, Cost of Inaction | Label + inline `Primary` badge when `isInsurer === true` |
| **SYSTEM** | (hardcoded outside NAV_ITEMS) | Settings & Data Info | Plain label |

Adding a new financial nav item = one new `NAV_ITEMS` entry + change the slice from `(4, 6)` to `(4, 7)`. Adding an item to a different section similarly shifts all subsequent slice indexes — this is fragile-by-design; the tradeoff was avoiding a full section-config refactor for two nav items.

### Role gating

Each nav item can carry `primary: 'insurer' | 'clinician' | null`. The `NavItem` component compares against `useRole().isInsurer` and applies visual state:

| Item's `primary` | Current role | Rendered state |
|---|---|---|
| `null` | any | Full opacity, no badge |
| `'insurer'` | Insurer | Full opacity, no badge |
| `'insurer'` | Clinician | **Opacity 0.5** (dimmed), badge shows `Insurer` in blue |
| `'clinician'` | Insurer | Opacity 0.5, badge shows `Clinician` in green |
| `'clinician'` | Clinician | Full opacity, no badge |

Dimmed items are still clickable (opacity change only, no `pointer-events` restriction). The "wrong role" badge appears next to the label to explain why. Both new financial items carry `primary: 'insurer'` so a clinician sees them dimmed with a blue "Insurer" badge — signalling context without blocking access.

### Route registration

`App.jsx` adds one line: `<Route path="/consequence" element={<CostOfInaction />} />`. Placed between `/budget` and `/settings` to match the sidebar visual order. React-router v7 handles the transition — no data preloading is done (the panel's own hooks fire on mount).

---

## Verified via `curl`

Backend booted on port 8765; both new endpoints return correct shapes:

```
downstream-cost → by_cluster[0].keys() includes cost_by_driver_5yr
                   Cluster 1: {ESRD: 231.58, CV_event: 5427.98, Uncontrolled_T2D: 29742.08}
                   Population 5-yr exposure: $370,537,727
                   Driver dist: Uncontrolled_T2D 64.4%, CV_event 35.6%

rebound-risk    → 4 by_cluster, 4 trajectory_by_cluster, sensitivity scenarios [early, median, late]

/api/summary    → still returns kpis, adherence_by_segment, dropout_by_window (no regression)
```

Frontend `npx vite build` clean: 776 kB / 224 kB gzipped, no errors.

---

## Screen root architecture

[pages/CostOfInaction/index.jsx](../../Frontend/src/pages/CostOfInaction/index.jsx) is a single React component that composes the three panels vertically inside a scrollable viewport. Structure top-to-bottom:

```
<CostOfInaction>
  ├── Clinician-view banner        (green, conditional on !isInsurer)
  ├── Framing banner "Cost of Inaction"   (orange gradient card)
  ├── Sticky sub-nav                (scroll-spy, negative margin to hug the container edges)
  ├── <div ref=downstream> <DownstreamCostPanel />
  ├── <div ref=rebound>    <ReboundRiskPanel />
  └── <div ref=roi>         <PayerROIPanel />
```

### Clinician-view banner (conditional)

Rendered only when `useRole().isInsurer === false`. Green (`#F0FFF4` bg, `#2E7D32` text, `#C8E6C9` border) with a stethoscope icon. Copy: *"Clinician View — This screen is designed for Insurer/Payer financial planning. All tools remain accessible."* Two shortcut links to Patient Risk Panel and Executive Summary. The wording deliberately mirrors the identical banner on Budget Simulator so the two insurer-primary screens present the same message.

### Framing banner (always visible)

Orange gradient card (`#FFF9F0 → #FFF3E0` linear-gradient background, `#FFE0B2` border). Left side: 40 px alert-triangle icon in a filled `#EF6C00` rounded square. Right side:
- Small orange uppercase eyebrow "Cost of Inaction"
- Bold display-font headline "What happens when patients drop off GLP-1 therapy?"
- Three-sentence body copy explaining the panel narrative (problem → mechanism → solution).

### Sticky sub-nav (scroll-spy)

Three-button horizontal nav pinned to `top: 0` inside the main content area (with negative x margin `-mx-6 px-6` to visually span the full page width). Uses `z-10` to layer above panel content when they scroll under.

Behavior:

| User action | Result |
|---|---|
| Click a sub-nav button | `scrollTo(id)` calls `refs.current[id].scrollIntoView({ behavior: 'smooth', block: 'start' })`. The `scroll-mt-16` Tailwind utility on each panel wrapper prevents the sticky nav from covering the panel's own header. |
| Scroll the page manually | `IntersectionObserver` fires an `intersecting` entry when a panel enters the middle 30% of the viewport (`rootMargin: '-30% 0px -60% 0px'`). The observer callback sets `active` state to the panel's `data-panel` attribute, which restyles the active button's background to `var(--color-primary)` and text to white. |
| Panel scrolls off-screen | Observer entry for that panel fires `intersecting=false`. No state change — the last intersected panel stays "active" until another one crosses the observer threshold. Prevents flicker between panels. |

The observer is created once on mount inside a `useEffect` with `[]` deps, and disconnected on unmount. Panels register their DOM node via callback ref `ref={el => refs.current.<id> = el}`.

### Scroll behavior across route transitions

React-router doesn't auto-scroll on route change. Navigating from another page to `/consequence` lands at scroll-top by default — which is the framing banner. No custom `ScrollRestoration` needed because the container is `overflow-auto` inside `<main>`, not `document.body`.

---

## Shared components used

The two new panels lean heavily on the pre-existing shared components from [Frontend/src/components/shared/index.jsx](../../Frontend/src/components/shared/index.jsx) and [Frontend/src/components/shared/LoadingSkeleton.jsx](../../Frontend/src/components/shared/LoadingSkeleton.jsx). Inventory:

| Component | Origin | Used by (Panel 1 / 2) | Purpose |
|---|---|---|---|
| `SectionHeader` | shared | Both | Title + subtitle + optional right-aligned `action` slot (holds the horizon or scenario toggle) |
| `KPICard` | shared | Panel 1 (3 cards) | Label, big value, sub-caption, icon in a rounded coloured square |
| `ChartTooltip` | shared | Both (via chart components) | Consistent tooltip styling with formatter callback |
| `SkeletonCard` | shared/LoadingSkeleton | Both | Grey animated placeholder box while data loads |
| `SkeletonChart` | shared/LoadingSkeleton | Both | Larger placeholder for chart bodies |
| `SEGMENT_COLORS`, `SEGMENT_SHORT` | data/mockData | Both | 4-element arrays keyed by cluster index — used for cluster border-tops, chart line colours, and legends |

Nothing new was added to the shared library in Week 7 — the two new panels reused what was already there. This is intentional: it keeps the visual language consistent with the rest of the dashboard (KPI cards match the Executive Summary; skeletons match the Budget Simulator).

---

## Loading + error states

Each hook (`useDownstreamCost`, `useReboundRisk`) exposes `{ data, loading, error }`. The panels handle three states:

| State | Panel 1 render | Panel 2 render |
|---|---|---|
| `loading === true && !data` | 3 × `SkeletonCard h={110}` for KPI cards, `SkeletonChart h={300}` for stacked bar, 4 × `SkeletonCard h={180}` for cluster cards | `SkeletonChart h={320}` for trajectory chart, 4 × `SkeletonCard h={200}` for severity cards |
| `error` (fetch failed) | Full-panel error card: *"Failed to load /api/consequence/downstream-cost. Check the backend is running and Mongo is populated."* red text | Same pattern with `/rebound-risk` in the message |
| `data !== null` (steady state) | Live values render; skeletons disappear | Live values render |

Once data loads once, subsequent re-renders (e.g. horizon or scenario toggle) don't show skeletons — the toggle only re-derives values client-side from data already in memory, so there's no "loading" transition. This keeps the toggle response instantaneous.

### Error UX detail

The error banner is intentionally verbose about the root cause ("Check the backend is running and Mongo is populated"). During development this catches the two most common failure modes: (a) forgot to start uvicorn, (b) never ran the migration. Production build would replace this with a generic "Data temporarily unavailable" message.

---

## Metrics reference — what every number on the screen means

This is the field-by-field dictionary. If a payer or QA reviewer asks "where did that number come from?", the answer is in the tables below.

Common terms:
- **α** = cluster adherence rate (fraction, `is_adherent` mean per cluster).
- **Off-therapy Markov** = per-patient rollout with `on_therapy=False` — no GLP-1 modifiers.
- **On-therapy Markov** = per-patient rollout with `on_therapy=True` — applies renal RR 0.64, CV RR 0.74, glycemic RR 0.15.
- **Discount** = 3% annual real discount rate (Second Panel on CE in Health & Medicine, 2016).
- **Horizon** = number of annual Markov cycles.

### Panel 1 — Downstream Cost

#### Header KPI cards (3)

| KPI | Displayed value (5-yr default) | Backend source | Calculation | How to read it |
|---|---|---|---|---|
| **Population 5-yr / 10-yr exposure** | ~$370.5M / ~$744M | `DownstreamCostResponse.population_total_5yr` / `_10yr` | Sum of `expected_downstream_cost_5yr` (or 10yr) across all 7,566 patients in `progression_cost` collection. Off-therapy Markov, 3% discount. | Ceiling on the payer's total dropout-side exposure if every patient in the cohort dropped. This is *not* what will happen — it's the "worst-case if adherence went to zero" number that anchors the other panels. |
| **Avg cost per patient** | ~$48.9k / ~$98.3k | Client-derived | `population_total_5yr / n_patients_total`. | Per-patient average downstream burden. Compare against annual GLP-1 cost (~$7.5k net) to see the "drug vs. complications" tradeoff conceptually. |
| **Top cost driver** | Uncontrolled T2D (64.4%) | `primary_cost_driver_distribution` — argmax by share. | Router counts each patient's `primary_cost_driver` (assigned in the Markov rollout as the largest of ESRD/CV/Uncontrolled_T2D cost buckets over 5 years) and normalizes. | Tells the payer which complication category dominates dropout risk in this cohort. 64% Uncontrolled T2D means most dropped patients accrue cost through worsening glycemic control + CKD, not through catastrophic CV events. |

#### Horizon toggle

| Element | Displayed value | Effect |
|---|---|---|
| **5-year button** | Highlighted primary blue when active | Uses `avg_downstream_cost_5yr` on every card + bar chart. Population exposure switches to `population_total_5yr`. |
| **10-year button** | Highlighted primary blue when active | Uses `avg_downstream_cost_10yr`. Population exposure switches to `population_total_10yr`. No new network request — data already in memory. |

**Note:** ESRD % and CV % probabilities on the cluster cards stay pinned to their 5-year values regardless of horizon toggle — that's intentional. The 5-year probability is the payer-cycle-standard number; going to 10 years compounds uncertainty (per limitation #16 in [DATA_AND_MODEL_DOCUMENTATION.md](../DATA_AND_MODEL_DOCUMENTATION.md)).

#### Stacked bar chart (per-cluster driver breakdown at 5 years)

| Series | Colour | Source | Cluster 1 value | Interpretation |
|---|---|---|---|---|
| **Uncontrolled T2D** | Blue `#1E88E5` | `cost_by_driver_5yr.Uncontrolled_T2D` per cluster. Aggregate of `cost_share_uncontrolled_t2d_5yr × expected_downstream_cost_5yr` averaged. Includes S1 + S2 (CKD) per scope decision. | ~$29,742 | Chronic-progression bucket: uncontrolled diabetes + diabetic kidney disease over 5 years. |
| **CV event** | Orange `#EF6C00` | `cost_by_driver_5yr.CV_event`. Acute CV episode cost ($53.7k per event) + follow-up ($12.4k/yr for post-event years), weighted by cumulative CV hazard probability. | ~$5,428 | Includes both the one-time hospitalization cost and elevated ongoing care cost for patients who have already had an event. |
| **ESRD** | Red `#C62828` | `cost_by_driver_5yr.ESRD`. Sum of state-occupancy probability in S3 × $93,191/yr (Medicare FFS default). | ~$232 | Small in a 5-year window because ESRD requires 3+ years of chained transitions S1→S2→S3 to develop, but heavily weighted per case ($93k/yr). |

Hover tooltip on any segment shows dollar amount + full driver label. Bar heights are population-normalized (per-patient avg), so tallness ranks clusters by average-patient burden, not by cohort size.

#### Per-cluster cards (4)

| Displayed field | Source | How to read it |
|---|---|---|
| **Cluster ID** (0-3) + **cluster label** | `by_cluster[i].cluster_label` | Cluster label comes from the K-means segmentation done in Phase 1. |
| **Avg cost per patient / horizon** | `avg_downstream_cost_5yr` or `_10yr` depending on toggle. | Dollar amount per patient over the selected horizon, discounted 3%. |
| **ESRD @ 5yr** | `esrd_probability_5yr` — state-occupancy probability in S3 at year 5. | Cluster 0 ~0.007% (near-normal HbA1c patients rarely progress), Cluster 1 ~0.25% (highest), Cluster 2 ~0.15%. |
| **CV @ 5yr** | `cv_event_probability_5yr` — cumulative CV event hazard over 5 years. | Cluster 0 ~4.5%, Cluster 1 ~7.3%, Cluster 2 ~6.0%. Higher HbA1c + BMI → higher CV hazard. |

Card border-top colour = cluster colour from `SEGMENT_COLORS` (red / orange / green / blue for clusters 0/1/2/3).

---

### Panel 2 — Metabolic Rebound Risk

#### Scenario toggle (Early / Median / Late)

| Button | Dropout day | Effect on the page |
|---|---|---|
| **Early (Day 30)** | 30 days | Re-projects patients as if they dropped at day 30 (before steady state). Trajectory line chart + all severity gauges + probability cards refresh from `sensitivity[i].scenarios[early]` and `trajectory_by_cluster[i].scenarios[early]`. |
| **Median** | Cluster-empirical median of observed dropouts, clipped to `[31, 149]`. Days: c0=78, c1=106, c2=149, c3=141. | Realistic default — matches what actually happens in the cohort. Populates from `median` scenario. |
| **Late (Day 150)** | 150 days | Steady-state exposure. Patient attained the full trial reduction, so has the largest rebound pool to lose. |

Toggling scenarios triggers zero network requests — all three scenarios are already in the initial response payload.

#### HbA1c trajectory line chart

- **x-axis:** months 0, 3, 6, 9, 12 post-dropout.
- **y-axis:** HbA1c in %, fixed domain [4.5, 8.0].
- **4 lines** — one per cluster, colours from `SEGMENT_COLORS`. Data source: `trajectory_by_cluster[i].scenarios[scenario].points`.
- **Reference line at 6.5** (orange dashed, "T2D threshold"): ADA diagnostic cutoff for type-2 diabetes.
- **Reference line at 8.0** (red dashed, "Uncontrolled"): ADA glycemic-control failure threshold; treatment intensification indicated above this.

Reading the chart:
- Month 0 point = on-therapy HbA1c at moment of dropout (baseline − attained reduction, floored at 5.0).
- Slope of the line 0–6 months = `hba1c_rebound_rate_per_month` (0.10 %/month) up to the asymptote.
- Asymptote = attained_reduction × 0.66 above the month-0 value (66% of the on-therapy gain is regained per STEP-1 extension).
- A line crossing the 6.5 reference within 12 months means that cluster's typical patient develops new-onset T2D within a year of dropout.

Under the **Median scenario**, Cluster 2 (Strong Adherer) has the steepest rebound because they had the biggest gain to lose. Under **Early**, most clusters barely rebound because they never attained the full reduction. This is the payer message the panel delivers.

#### Severity gauge cards (4, one per cluster)

Custom SVG radial-progress ring. Colour thresholds (per plan spec §Phase 4):

| Score range | Ring colour | Label | Interpretation |
|---|---|---|---|
| `< 0.3` | Green `#2E7D32` | **Low** | Small rebound pool + trajectory stays below thresholds. |
| `0.3 – 0.6` | Amber `#EF6C00` | **Moderate** | Meaningful metabolic rebound within 12 months. |
| `> 0.6` | Red `#C62828` | **High** | Large rebound pool or trajectory crosses uncontrolled threshold. |

Score composition (per Phase 2 formula):

```
severity = 0.4 × HbA1c_rebound_norm    (max at 2.0 pt regain)
         + 0.3 × BMI_rebound_norm      (max at 5.0 kg/m² regain)
         + 0.3 × threshold_crossing_prob
```

| Field | Displayed value (Median scenario) | Source | Interpretation |
|---|---|---|---|
| **Cluster label + ID** | e.g. "Cluster 1 · Financial Barrier Dropout Risk" | `by_cluster[i].cluster_label`. | Cluster identity. |
| **Severity score** | Numeric ring: c0=0.17, c1=0.36, c2=0.43, c3=0.30 | `sensitivity[i].scenarios[scenario].avg_severity_score`. | Composite metric. Cluster 2's ~0.43 dominance across all scenarios is the "if the good ones drop, you lose the most" story. |
| **Severity badge** | Low / Moderate / High pill next to the ring | Client-side thresholding of the score. | Colour-matched to the ring. |
| **"at [scenario] dropout"** | e.g. "at median dropout" | The currently-active scenario name. | Reminds the reviewer that severity is scenario-dependent. |
| **New T2D @ 12mo** | e.g. c1: 16.4%, c0: 2.5%, c2: dash (N/A) | `sensitivity[i].scenarios[scenario].p_new_t2d_12mo_mean`. Averaged only across pre-DM patients in the cluster. | Probability that a pre-DM patient in this cluster develops new-onset T2D within 12 months of dropout. Dash appears if the cluster has no pre-DM patients under this scenario. |
| **Uncontrolled @ 12mo** | e.g. c1: 78.3%, c2: 91.3%, c0: dash (no T2D patients) | `sensitivity[i].scenarios[scenario].p_uncontrolled_12mo_mean`. Averaged only across T2D patients (LBXGH ≥ 6.5 at effective on-therapy). | Probability that a T2D patient in this cluster becomes uncontrolled (HbA1c ≥ 8.0) within 12 months of dropout. High values in cluster 2 reflect the fact that Strong Adherers with large on-therapy reductions have the largest rebound-driven excursion. |

Card border-top matches cluster colour.

#### Population T2D incidence banner (bottom of Panel 2)

| Field | Displayed value | Source | Interpretation |
|---|---|---|---|
| **Expected new-onset T2D incidence @ 12mo** | ~5.8% | `population_t2d_incidence_12mo`. Weighted average of `p_new_t2d_12mo_mean` across all pre-DM patients in the population. | Aggregate 12-month T2D conversion rate among pre-DM patients who drop off GLP-1 therapy. Anchors the panel with a headline population number that the trajectory chart's per-cluster lines break down. |

The banner uses the same orange gradient + `AlertTriangle` icon as the top framing banner to link them visually as "problem statements."

---

## What to verify locally

Run these two commands in separate terminals from the project root, then step through the checks below.

```bash
# Terminal 1 — backend
cd Backend
PYTHONIOENCODING=utf-8 venv/Scripts/python.exe -m uvicorn main:app --reload

# Terminal 2 — frontend
cd Frontend
npm run dev
# Vite prints the local URL (default http://localhost:5173)
```

Open the URL, then verify:

**Sidebar / routing**
- [ ] "Financial" section appears in the sidebar with a "Primary" badge when Insurer role is selected.
- [ ] "Cost of Inaction" nav item is visible with the alert-triangle icon.
- [ ] Clicking it navigates to `/consequence` and the AppShell page title reads "Cost of Inaction".
- [ ] Switching to Clinician role dims (opacity 0.5) both financial entries but they remain clickable.

**Screen root**
- [ ] Orange framing banner ("What happens when patients drop off GLP-1 therapy?") renders at the top.
- [ ] Green Clinician-view banner appears when you toggle to Clinician role.
- [ ] Sticky sub-nav shows Downstream Cost / Metabolic Rebound / Payer ROI. Clicking any of the three smooth-scrolls to that panel.
- [ ] Scrolling manually updates which sub-nav item is highlighted (scroll-spy).

**Panel 1 — Downstream Cost**
- [ ] Three KPI cards populate with numbers: Population 5-yr exposure ≈ **$370M**, Avg cost per patient ≈ **$49k**, Top cost driver = **Uncontrolled T2D 64.4%**.
- [ ] 5-year / 10-year toggle changes all three KPI numbers and the four cluster cards.
- [ ] Stacked bar chart renders with 4 bars (one per cluster), each stacked in three colours. Cluster 1 (Financial Barrier) is visibly taller than Cluster 0. Legend at bottom.
- [ ] Hovering over a stacked segment shows a tooltip like "$29.7K" with the driver name.
- [ ] Four per-cluster cards show cluster label, average cost, and ESRD%/CV% at 5-yr.

**Panel 2 — Metabolic Rebound Risk**
- [ ] Trajectory line chart shows 4 lines (one per cluster) starting near their on-therapy HbA1c and climbing toward the reference lines.
- [ ] The 6.5 (orange) and 8.0 (red) reference lines are visible with labels on the right edge.
- [ ] Scenario toggle (Early / Median / Late) changes the chart lines and the severity gauge values in real time — no page reload.
- [ ] Severity gauges: cluster 2's ring is roughly half-filled (score ~0.43) and coloured orange (moderate). Cluster 0's ring is small and green.
- [ ] "New T2D @ 12mo" and "Uncontrolled @ 12mo" percentages appear in each cluster card; the T2D value shows a dash (`—`) for clusters where nobody is pre-DM.
- [ ] Population banner at the bottom shows "≈5.8% expected new-onset T2D incidence within 12 months".

**Regression check**
- [ ] Executive Summary (`/`) still loads with KPIs and charts.
- [ ] Patient Risk Panel (`/patients`) still lists patients.
- [ ] Segment Explorer (`/segments`), Survival Analysis (`/survival`), Budget Simulator (`/budget`) all load without console errors.
- [ ] Loading skeletons render briefly on first navigation to `/consequence` while data fetches.

**Console / network**
- [ ] Open DevTools → Network tab. First visit to `/consequence` fires exactly two requests: `downstream-cost` and `rebound-risk`. Both return `200`.
- [ ] Toggling the horizon (5/10) or scenario (Early/Median/Late) does *not* fire new network requests — that data is already in memory.
- [ ] No red errors in DevTools Console. (`404` for a favicon is fine.)

If any check fails, tell me the panel + step and I'll fix it before Week 8.

---

## What's next — Week 8

1. **Panel 3 base.** Grouped bar chart of ROI at 1/3/5-yr per cluster with a `ReferenceLine` at ROI=0. Break-even adherence prominent next to each cluster.
2. **Intervention slider.** Radix Slider (`$0`–`$3000`, step $50). `usePayerROI` already debounces at 250 ms, so the slider will just wire directly.
3. **Threshold cards.** Per-cluster "Max intervention spend before ROI turns negative" card. Population summary strip.
4. **Framing polish.** Negative-5yr-ROI narrative banner (from Phase 3 limitation #20 — "budget impact, not value"). Break-even adherence gets top billing in each cluster card.
5. **End-to-end walkthrough.** Slider drag at $0 → $500 → $2000 shows continuous ROI change. Verify all 3 panels together tell the "problem → mechanism → solution" story.
6. **Phase 4 recap.** Full [updates/phase_4_progress.md](phase_4_progress.md) consolidating Weeks 7–8.

Phase 5 (validation + documentation + demo script + briefing note, Week 9) closes the plan.
