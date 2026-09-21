# GLP-1 Analytics Dashboard — Full Frontend Plan
## Product Specification for React Application

**Project:** GLP-1 Adherence & Cost Intelligence Platform
**Client:** NeuroShield / Denovonet
**Frontend Stack:** React + Recharts + TailwindCSS
**Backend:** FastAPI (Python) — model serving + data layer
**Primary Users:** Insurers / Payers, Hospital Case Managers, Clinical Staff
**Date:** May 2026

---

## 1. User Roles & What They Need

Before designing any screen, the two user types need different primary lenses on the same underlying data. The dashboard must serve both without forcing either to dig through irrelevant information.

### Role A — Insurer / Payer
**Job:** Manage a GLP-1 drug benefit across a covered population. Justify spend to leadership. Decide which interventions to fund.

**Questions they arrive with:**
- How much of our GLP-1 spend is being wasted on patients who quit?
- Which patient segments give us the best return per dollar?
- If we invest in adherence interventions, what does the math look like?
- How does our actual dropout rate compare to published benchmarks?

**Data they need front and center:** Budget impact, cost-effectiveness ratios, population-level dropout rates, segment ROI comparison, what-if simulation, ICER vs alternatives.

**Data they do not need:** Individual patient names, clinical chart details, per-patient SHAP breakdowns.

---

### Role B — Hospital Case Manager / Clinical Staff
**Job:** Manage a panel of patients on GLP-1 therapy. Identify who needs a call, a copay coupon, or a side effect check-in. Prioritize their day.

**Questions they arrive with:**
- Which of my patients are most likely to quit in the next 30 days?
- Why is this specific patient flagged — what's driving their risk?
- What segment does this patient belong to and what does that mean for how I help them?
- How is the overall panel doing on adherence?

**Data they need front and center:** Individual patient risk scores, SHAP driver explanations in plain language, patient segment assignment, dropout probability, intervention triggers.

**Data they do not need:** ICER calculations, budget impact simulations, population-level cost analysis.

---

### Role Switching
The application implements a **role toggle** in the top navigation. Switching role does not reload data — it changes which panels are visible/prominent and which are secondary. Both roles can access all screens but the default view and emphasis shift.

---

## 2. Application Architecture

```
GLP-1 Dashboard
├── Auth Layer (login + role selection)
├── Navigation Shell (persistent sidebar)
│
├── Screen 1:  Executive Summary         [Both roles — different emphasis]
├── Screen 2:  Patient Risk Panel        [Primary: Case Manager]
├── Screen 3:  Patient Detail            [Primary: Case Manager]
├── Screen 4:  Segment Explorer          [Both roles]
├── Screen 5:  Survival Analysis         [Both roles]
├── Screen 6:  Cost-Effectiveness Studio [Primary: Insurer]
├── Screen 7:  Budget Impact Simulator   [Primary: Insurer]
└── Screen 8:  Settings / Data Info      [Both roles]
```

**Total screens: 8**
**Total distinct React page components: 8**
**Shared component library: ~24 reusable components**

---

## 3. Screen-by-Screen Specification

---

### Screen 1 — Executive Summary

**Route:** `/dashboard`
**Default landing screen for both roles**
**Purpose:** Give a 60-second read on the state of the entire GLP-1 population

---

#### Layout
Full-width. Three horizontal zones stacked vertically.

**Zone A — KPI Strip (top)**
Five stat cards in a row. Each card shows the metric name, current value, and a small trend indicator (up/down arrow with percentage vs benchmark).

| Card | Metric | Source |
|---|---|---|
| Total Patients | 7,566 | GLP1_FINAL_WITH_SURVIVAL.csv row count |
| Overall Adherence | 47.0% | mean(is_adherent) |
| Population Dropout Rate | 53.0% | 1 − adherence |
| Avg Annual Drug Cost | $10,603 | mean(annual_drug_cost) |
| Est. Wasted Spend (Annual) | $40.0M | sum(wasted_spend_per_pt) |

**Zone B — Middle Row (two panels side by side)**

Left panel: **Adherence Donut Chart**
- Outer ring: Adherent vs Dropout split
- Inner ring: Breakdown by segment (4 colors for 4 clusters)
- Center label: "47% Adherent"
- Clicking a segment slice navigates to Segment Explorer with that segment pre-selected
- Data: GLP1_SEGMENTED.csv grouped by cluster + is_adherent

Right panel: **Dropout Rate by Segment Bar Chart**
- Horizontal bars, one per segment, sorted worst to best
- Color coded: red (Clusters 0 and 1), blue (Cluster 3), green (Cluster 2)
- Benchmark line at 53% (published real-world average)
- Data: adherence_by_cluster from GLP1_SEGMENTED.csv

**Zone C — Bottom Row (two panels side by side)**

Left panel: **High Risk Patient Count by Dropout Window**
- Grouped bar chart showing how many patients are estimated to drop out at 30 / 60 / 90 / 180 days
- One bar group per segment
- Data: survival_checkpoints.csv × segment population sizes

Right panel: **Top 3 Population Dropout Drivers (Global SHAP)**
- Horizontal ranked bar chart
- Feature name (human-readable label, not raw column name)
- Mean absolute SHAP impact
- Color gradient from high impact (dark) to low (light)
- Data: shap_values_test.npy mean absolute values, mapped through FEATURE_LABELS

---

#### Role Emphasis Difference
- **Insurer view:** Zone C right panel replaced with "Total Wasted Spend by Segment" bar chart
- **Case Manager view:** Zone C right panel stays as SHAP drivers; an alert banner appears above Zone A if any patient has dropout_prob > 0.85 ("X high-risk patients need immediate attention")

---

#### Components Used
`KPICard`, `DonutChart`, `HorizontalBarChart`, `GroupedBarChart`, `SHAPDriverBar`, `RoleBanner`

---

### Screen 2 — Patient Risk Panel

**Route:** `/patients`
**Primary user:** Case Manager
**Purpose:** Prioritized list of all patients ranked by dropout probability. The daily worklist.

---

#### Layout
Left sidebar (30%) + Main table area (70%)

**Left sidebar — Filters**
- Dropdown: Filter by Segment (All / Cluster 0–3)
- Dropdown: Filter by Molecule (All / Semaglutide / Tirzepatide / Liraglutide / Dulaglutide)
- Slider: Dropout probability threshold (show patients above X%)
- Toggle: Show only "Dropout Risk" predictions vs All
- Toggle: Show only patients whose driver_1 is Financial (to identify copay assist candidates)
- Reset filters button

**Main area — Patient Table**
Sortable columns:

| Column | Contents | Notes |
|---|---|---|
| Risk Score | Dropout probability % with color-coded badge | Red >75%, Orange 50–75%, Yellow 25–50%, Green <25% |
| Prediction | "Dropout Risk" or "Likely Adherent" pill badge | |
| Segment | Short segment label | Color dot matching segment color |
| Top Driver | driver_1 (plain language) | Truncated to 40 chars |
| Driver Direction | "↑ increasing risk" or "↓ reducing risk" | Icon + text |
| Driver 2 | driver_2 label | |
| Drug | assigned_molecule | |
| OOP Cost | avg_oop_cost | Formatted as $XX |
| Action | "View Patient" button | Routes to Screen 3 |

Default sort: dropout_prob descending (highest risk first)
Pagination: 25 patients per page
Search: by patient_idx or any text match in driver labels

**Above the table — Summary Strip**
Three inline stats: "Showing X patients | Y flagged high risk (>75%) | Z financial barrier cases"

---

#### Components Used
`FilterSidebar`, `RiskBadge`, `PredictionPill`, `SegmentDot`, `SortableTable`, `SearchBar`, `PaginationControls`, `SummaryStrip`

---

### Screen 3 — Patient Detail

**Route:** `/patients/:id`
**Primary user:** Case Manager
**Purpose:** Deep-dive on a single patient — explain exactly why they are flagged and what to do

---

#### Layout
Three columns on desktop, stacked on tablet.

**Column 1 — Patient Profile Card**
- Patient index / ID
- Assigned molecule (with drug generation badge)
- Segment assignment (with full segment label)
- Key clinical values: Age, BMI, HbA1c, Comorbidity Score
- Key financial values: OOP Cost, Income Cost Pressure
- Bio Friction score with plain-language interpretation:
  - < 0.30: "Low side effect risk"
  - 0.30–0.45: "Moderate side effect risk"
  - > 0.45: "High side effect risk — monitor for GI complaints"

**Column 2 — Risk Explanation**
This is the SHAP waterfall panel — the most clinically important element.

- Large dropout probability gauge (semicircle, 0–100%)
- Prediction label below gauge
- Three driver cards stacked vertically, one per SHAP driver:
  - Driver name (full plain-language label from FEATURE_LABELS)
  - Direction badge: "Increasing dropout risk" (red) or "Reducing dropout risk" (green)
  - SHAP value magnitude bar (width proportional to abs value)
  - One-sentence plain English interpretation auto-generated per driver type:
    - income_cost_pressure → "This patient's out-of-pocket costs are high relative to their income, creating financial pressure that often leads to discontinuation."
    - bio_friction → "Side effect intensity for this patient's medication is elevated — GI issues are the leading cause of early dropout."
    - LBXGH → "HbA1c level suggests [controlled/borderline/poor] glucose control — [higher/lower] clinical motivation to continue therapy."
    - system_refill_score → "Provider refill reliability is [strong/limited] — [low/high] risk of supply disruption."

**Column 3 — Survival & Segment Context**
- Mini Kaplan-Meier showing this patient's segment curve highlighted, other segments greyed out
- Dropout checkpoint table for this patient's segment (30/60/90/180 day rates)
- "Patients like this" summary: "In this segment, X% dropout by day 90"
- Recommended action card (rules-based, driven by top driver):
  - If driver_1 = income_cost_pressure: "Recommended: Connect patient to copay assistance program. Average financial barrier in this segment: $XX/month."
  - If driver_1 = bio_friction: "Recommended: Schedule side effect check-in call. Consider dose titration review."
  - If driver_1 = system_refill_score: "Recommended: Verify prior authorization status and pharmacy refill continuity."
  - If driver_1 = LBXGH (high HbA1c, reducing risk): "Patient has strong clinical motivation — standard monitoring sufficient."

**Back button** returns to Patient Risk Panel preserving filter/sort state.

---

#### Components Used
`PatientProfileCard`, `RiskGauge`, `SHAPDriverCard`, `DriverInterpretationText`, `MiniKaplanMeier`, `CheckpointTable`, `RecommendedActionCard`

---

### Screen 4 — Segment Explorer

**Route:** `/segments`
**Both roles — different emphasis panels visible**
**Purpose:** Understand each of the 4 patient segments in depth. Compare clinical profiles, cost patterns, and adherence behavior.

---

#### Layout
Tab row at top selecting active segment + comparison view below.

**Segment Tab Row**
Four tabs, one per cluster. Each tab shows:
- Segment short label
- Patient count
- Adherence rate
- Color indicator (matching KM curve colors from analysis)

**Below tabs — three-panel row (when single segment selected)**

Panel 1 — **Segment Profile Radar Chart**
Radar/spider chart with 6 axes: Age (normalized), BMI, HbA1c, Cost Pressure, Bio Friction, Comorbidity Score. Filled polygon for selected segment, ghost polygon for population average. Immediately shows whether the segment is above or below average on each clinical dimension.

Panel 2 — **Key Metrics Grid**
2×4 grid of metric tiles:
- Adherence Rate
- Median Survival Time
- Avg OOP Cost
- Cost per HbA1c Point
- Dropout by Day 30
- Dropout by Day 90
- Wasted Spend per Patient
- Most Common Drug (molecule)

Panel 3 — **Clinical Distribution Charts**
Mini histograms for BMI, Age, HbA1c distributions within the segment. Overlaid with population distribution in grey. Shows where the segment sits relative to the full population.

**Below — Comparison Mode**
Toggle button: "Compare All Segments"
When active, collapses the tab panels and shows a full side-by-side comparison table: all 4 segments as columns, all key metrics as rows. Color coded: best value in green, worst in red, per row.

**Insurer-specific panel (visible when Insurer role active)**
Additional panel below comparison table: **Segment ROI Card**
For each segment: dropdown showing "What if dropout reduced by X%?" → shows net saving for that segment. Pre-filled from budget_impact.csv, interactive slider recalculates.

---

#### Components Used
`SegmentTabRow`, `RadarChart`, `MetricGrid`, `MiniHistogram`, `ComparisonTable`, `SegmentROICard`

---

### Screen 5 — Survival Analysis

**Route:** `/survival`
**Both roles**
**Purpose:** Show the full Kaplan-Meier curves and dropout timing data in an explorable format

---

#### Layout
Single main chart taking 60% of vertical space, controls and data below.

**Main Chart — Kaplan-Meier Curves**
Full interactive KM plot:
- All 4 segment curves rendered simultaneously
- Confidence interval bands (toggle on/off)
- Hover tooltip on any point: shows exact day, survival probability, 95% CI bounds, segment name
- Vertical reference lines at 30/60/90/180 days
- Cursor crosshair follows mouse across chart
- Legend with segment names and adherence rates
- Colors match throughout the entire application

**Controls Bar (below chart)**
- Checkbox group: toggle individual segment curves on/off
- Toggle: Show/hide confidence intervals
- Toggle: Show/hide reference day lines
- Dropdown: "Highlight segment" (dims all others, makes selected bold)

**Checkpoint Data Table (below controls)**
Full survival_checkpoints.csv rendered as table with conditional formatting:
- Dropout rate cells colored on gradient: green (low) → red (high)
- Segment rows colored with segment color accent on left border
- Sortable by any checkpoint column

**Median Survival Summary Cards**
Four cards in a row, one per segment, showing:
- Segment name
- "50% of patients remain on therapy through day X"
- Mini spark line of that segment's survival curve

**Interpretation Panel**
Collapsible text panel: plain language reading of the curves for a clinical audience:
"Cluster 2 (Low Friction Strong Adherers) show minimal dropout through the full 180-day window, with only 14.6% having discontinued by day 180. Cluster 0 (Low Urgency Dropout Risk) shows the fastest attrition — nearly 1 in 5 patients have quit by day 30, and the majority (79.2%) have discontinued by day 180..."

---

#### Components Used
`KaplanMeierChart`, `CurveToggleControls`, `CheckpointTable`, `MedianSurvivalCard`, `InterpretationPanel`

---

### Screen 6 — Cost-Effectiveness Studio

**Route:** `/cost-effectiveness`
**Primary user: Insurer** (visible to Case Manager in read-only simplified view)
**Purpose:** Full economic analysis — CEA ratios, ICER vs alternatives, segment value ranking

---

#### Layout
Two columns: Analysis controls left (35%), Charts right (65%)

**Left — Analysis Controls**
- Segment selector (multi-select checkboxes — compare any combination)
- Outcome metric toggle: "Weight Loss" vs "HbA1c Reduction" (changes all charts)
- Comparator toggle: "vs Insulin Glargine" / "vs SGLT2 Inhibitor" / "vs Both"
- Data source note: "Clinical benchmarks from STEP 1–4 and SURMOUNT-1 trials"

**Right — Three chart panels**

Top chart: **Cost-Effectiveness Scatter Plot**
- X axis: Effective clinical outcome (weight loss % or HbA1c reduction)
- Y axis: Average annual drug cost
- One bubble per segment, bubble size = population size (n)
- Color = segment color
- Quadrant lines: vertical at population avg outcome, horizontal at population avg cost
- Labels on each bubble
- Ideal position = bottom right (high outcome, low cost)
- Hovering bubble shows full CEA breakdown tooltip

Middle chart: **ICER Waterfall Chart**
- Shows incremental cost per unit of benefit for each segment vs selected comparator
- Horizontal waterfall bars from zero
- Published cost-effectiveness threshold line at $50,000 (standard QALY threshold reference)
- Segments above threshold flagged in red, below in green

Bottom: **Cost-Efficiency Ranking Table**
| Rank | Segment | Cost/HbA1c Pt | Cost/Weight% | vs Insulin ICER | vs SGLT2 ICER |
All formatted as currency. Best value highlighted green. Worst red.

---

#### Components Used
`ScatterBubbleChart`, `ICERWaterfallChart`, `CostRankingTable`, `AnalysisControlPanel`, `ComparatorToggle`

---

### Screen 7 — Budget Impact Simulator

**Route:** `/budget-impact`
**Primary user: Insurer**
**Purpose:** Real-time what-if modeling — adjust dropout reduction assumption and intervention cost, see net saving update live

---

#### Layout
Top controls → Results below. Full width.

**Control Zone (top)**
Three sliders in a row:

Slider 1: **Dropout Reduction Assumption**
- Range: 5% to 50%, step 5%
- Default: 15%
- Label: "Assumed dropout reduction from intervention program"

Slider 2: **Intervention Cost per Patient**
- Range: $100 to $2,000, step $100
- Default: $500
- Label: "Annual cost of intervention per patient"

Slider 3: **Population Scope**
- Range: 10% to 100%, step 10%
- Default: 100%
- Label: "% of population included in intervention program"
- (Scales down patient counts proportionally)

**Results Zone (below sliders)**

Top: **Total Net Saving Banner**
Large centered number: "Estimated Annual Net Saving: $X,XXX,XXX"
Color coded: green (positive), red (negative)
Sub-line: "Across X,XXX patients at $XXX intervention cost with XX% dropout reduction"

Middle: **Per-Segment Results Cards (4 cards in a row)**
Each card shows:
- Segment name + color
- Patient count (in scope)
- Current dropout rate → projected dropout rate
- Waste recovered: $X
- Intervention cost: $X
- Net saving: $X (color coded)
- ROI badge: "✅ Positive ROI" or "⚠️ Negative ROI"

Cards update in real time as sliders move. Negative ROI cards dim slightly to signal "don't intervene here."

Bottom: **Cumulative Impact Chart**
Area chart showing cumulative net saving over 12 months under:
- Current scenario (solid line)
- No intervention baseline (dashed line)
- Break-even point marked with vertical line + label "Break-even at month X"

**Export Button**
"Export Scenario as PDF" — generates a one-page summary of current slider values and results. Useful for presenting to leadership.

---

#### Components Used
`ScenarioSlider`, `TotalSavingBanner`, `SegmentImpactCard`, `CumulativeImpactChart`, `ExportButton`

---

### Screen 8 — Settings & Data Info

**Route:** `/settings`
**Both roles**
**Purpose:** Transparency about what the model is doing, data sources, model performance, and platform configuration

---

#### Sections

**Model Performance Card**
- Model: Gradient Boosting Classifier v2 (max_features=sqrt)
- Accuracy: 79.1% | Precision: 87.6% | Recall: 64.6% | F1: 74.4% | AUC-ROC: 87.9%
- Decision threshold: [value from pkl]
- Training set: X,XXX patients | Test set: X,XXX patients
- Last retrained: [date]

**Data Sources Panel**
Table listing all 5 source datasets with name, creator, records used, and date of extraction:
- CMS Medicare Part D 2023 — 351,240 GLP-1 records
- NHANES 2017–2018 + 2021–2023 — 5,000+ patients
- MEPS — 2,933 GLP-1 prescription fills
- FAERS — Post-market adverse event reports
- ClinicalTrials.gov — 19 STEP/SUSTAIN/SURMOUNT trials

**Known Limitations Panel**
Collapsible section listing the 5 documented limitations from the Week 2 documentation:
- Synthetic survival times
- system_refill_score direction anomaly
- has_hypertension dead column
- Soft cluster boundaries
- Class imbalance correction via upsampling

**Role & Preferences**
- Current role toggle (Insurer / Case Manager) — persistent across sessions
- Color theme toggle (Light / Dark)
- Notification preferences (placeholder for Phase 2)

---

#### Components Used
`ModelPerformanceCard`, `DataSourceTable`, `LimitationsPanel`, `RoleToggle`, `ThemeToggle`

---

## 4. Shared Component Library

These components are used across multiple screens and must be built first before any screen work begins.

| Component | Description | Used On |
|---|---|---|
| `AppShell` | Persistent sidebar + topnav + role indicator | All screens |
| `Sidebar` | Navigation links with active state indicators | All screens |
| `RoleBanner` | Colored banner showing active role | All screens |
| `KPICard` | Stat card with metric, value, trend indicator | Screen 1 |
| `RiskBadge` | Color-coded dropout probability badge | Screens 2, 3 |
| `PredictionPill` | "Dropout Risk" or "Likely Adherent" pill | Screens 2, 3 |
| `SegmentDot` | Colored dot with segment label | Screens 1, 2, 3, 4 |
| `SHAPDriverCard` | Single SHAP driver with label, direction, bar | Screens 1, 3 |
| `DonutChart` | Recharts PieChart wrapper with two rings | Screen 1 |
| `HorizontalBarChart` | Recharts BarChart horizontal wrapper | Screens 1, 4, 6 |
| `SortableTable` | Sortable, paginated data table | Screen 2 |
| `FilterSidebar` | Left panel with dropdowns, sliders, toggles | Screen 2 |
| `RiskGauge` | Semicircle gauge for dropout probability | Screen 3 |
| `MiniKaplanMeier` | Small non-interactive KM curve | Screen 3 |
| `RadarChart` | Recharts RadarChart wrapper | Screen 4 |
| `MetricGrid` | 2×4 grid of labeled metric tiles | Screen 4 |
| `ComparisonTable` | Multi-column comparison with conditional formatting | Screen 4 |
| `KaplanMeierChart` | Full interactive KM chart with tooltips | Screen 5 |
| `ScatterBubbleChart` | Recharts ScatterChart with bubble sizing | Screen 6 |
| `ICERWaterfallChart` | Custom waterfall bar chart for ICER | Screen 6 |
| `ScenarioSlider` | Labeled range slider with live value display | Screen 7 |
| `SegmentImpactCard` | Budget impact result card per segment | Screen 7 |
| `CumulativeImpactChart` | Recharts AreaChart with break-even marker | Screen 7 |
| `ModelPerformanceCard` | Metric grid for model stats | Screen 8 |
| `LimitationsPanel` | Collapsible text sections | Screen 8 |

**Total shared components: 24**

---

## 5. Design System

### Color Palette

```css
/* Primary brand */
--color-primary:        #1B4F8A;   /* Deep medical blue */
--color-primary-light:  #2E6DB4;
--color-primary-dark:   #0F2D4F;

/* Segment colors — consistent across all charts */
--segment-0:            #EF5350;   /* Cluster 0 — Low Urgency Dropout — red */
--segment-1:            #FF7043;   /* Cluster 1 — Financial Barrier Dropout — orange */
--segment-2:            #43A047;   /* Cluster 2 — Low Friction Strong Adherer — green */
--segment-3:            #1E88E5;   /* Cluster 3 — Moderate Risk Moderate Adherer — blue */

/* Risk levels */
--risk-critical:        #C62828;   /* dropout_prob > 75% */
--risk-high:            #EF6C00;   /* dropout_prob 50–75% */
--risk-medium:          #F9A825;   /* dropout_prob 25–50% */
--risk-low:             #2E7D32;   /* dropout_prob < 25% */

/* Neutral */
--color-bg:             #F4F6F9;
--color-surface:        #FFFFFF;
--color-border:         #E2E8F0;
--color-text-primary:   #1A202C;
--color-text-secondary: #718096;

/* Semantic */
--color-positive:       #2E7D32;   /* Positive ROI, good outcome */
--color-negative:       #C62828;   /* Negative ROI, bad outcome */
--color-warning:        #E65100;
```

### Typography

```css
/* Display font — for KPI numbers and screen titles */
font-family: 'DM Serif Display', Georgia, serif;

/* Body font — for labels, tables, UI text */
font-family: 'IBM Plex Sans', system-ui, sans-serif;

/* Monospace — for patient IDs, numeric data in tables */
font-family: 'IBM Plex Mono', monospace;
```

### Spacing & Layout
- Sidebar width: 240px (collapsed: 64px)
- Content max-width: 1440px
- Card padding: 24px
- Chart margins: top 20, right 30, bottom 40, left 60
- Grid gap: 16px (standard), 24px (between major sections)

---

## 6. Backend API Endpoints

The React frontend consumes these FastAPI endpoints. Each maps to a specific data file or model operation.

| Endpoint | Method | Returns | Source |
|---|---|---|---|
| `/api/summary` | GET | KPI strip data | GLP1_FINAL_WITH_SURVIVAL.csv aggregated |
| `/api/patients` | GET | Paginated patient table | shap_patient_drivers.csv + GLP1_SEGMENTED.csv |
| `/api/patients/:id` | GET | Single patient detail + SHAP drivers | shap_patient_drivers.csv + GLP1_FINAL |
| `/api/segments` | GET | All 4 segment profiles | segment_profiles.csv |
| `/api/segments/:id` | GET | Single segment deep profile | segment_profiles.csv filtered |
| `/api/survival` | GET | KM curve data points + checkpoints | survival_checkpoints.csv + KM fitted values |
| `/api/cost-effectiveness` | GET | CEA + ICER by segment | cost_effectiveness.csv + icer_by_segment.csv |
| `/api/budget-impact` | POST | Recalculated budget impact | Calculated in real time from request params |
| `/api/shap/global` | GET | Global SHAP mean absolute values | shap_values_test.npy summarized |
| `/api/model/info` | GET | Model performance metrics | Hardcoded from pkl metadata |

**`/api/budget-impact` POST body:**
```json
{
  "dropout_reduction_pct": 15,
  "intervention_cost_per_patient": 500,
  "population_scope_pct": 100
}
```

**Response:** Per-segment and total net saving, recalculated server-side from cea_df base values.

---

## 7. Build Order

Build in this sequence to avoid blocking dependencies:

### Phase 1 — Foundation (Days 1–2)
1. Project scaffold: Vite + React + TailwindCSS + Recharts + React Router
2. Design system: CSS variables, typography imports, color tokens
3. `AppShell` — sidebar + topnav + role toggle (static, no data)
4. All 8 routes registered with placeholder page components
5. Mock data layer: JSON files mirroring API response shapes so frontend can build without backend ready

### Phase 2 — Core Shared Components (Days 2–3)
6. `KPICard`, `RiskBadge`, `PredictionPill`, `SegmentDot`
7. `SHAPDriverCard` with bar and direction indicator
8. `SortableTable` with pagination and search
9. `RiskGauge` semicircle component
10. All chart wrappers: DonutChart, HorizontalBarChart, RadarChart stubs

### Phase 3 — Screen Build (Days 3–7, one screen per day)
11. Screen 1: Executive Summary — wire all Zone A/B/C panels
12. Screen 2: Patient Risk Panel — table + filter sidebar
13. Screen 3: Patient Detail — three-column layout with SHAP cards
14. Screen 4: Segment Explorer — tabs + radar + comparison table
15. Screen 5: Survival Analysis — KM chart with interactivity
16. Screen 6: Cost-Effectiveness Studio — scatter + ICER + controls
17. Screen 7: Budget Impact Simulator — sliders + live update cards

### Phase 4 — Backend Integration (Days 7–9)
18. FastAPI project scaffold
19. Data loading layer (CSV → pandas → JSON serialization)
20. All endpoints implemented and tested
21. Replace mock data in frontend with real API calls
22. Error states and loading skeletons added to all screens

### Phase 5 — Polish (Days 9–10)
23. Screen 8: Settings page
24. Role toggle logic — conditional panel visibility
25. Mobile responsive pass (tablet breakpoints minimum)
26. Loading states, empty states, error boundaries
27. Cross-browser QA

---

## 8. Key Design Decisions

**Why React + Recharts over a BI tool (Tableau, Power BI)?**
The budget impact simulator requires real-time server-side recalculation from the trained model. BI tools cannot call a Python model endpoint dynamically. The SHAP driver text requires rule-based interpretation logic that lives in application code. A custom React application gives full control over both.

**Why role toggle instead of two separate apps?**
The underlying data is identical — only the emphasis differs. Maintaining one codebase with conditional rendering is far cheaper than two applications diverging over time. The toggle also allows a single user (e.g., a hospital finance director who is both an insurer and a clinical stakeholder) to switch contexts without logging out.

**Why Recharts over D3 directly?**
Recharts wraps D3 in React-friendly components, which dramatically reduces development time for standard chart types (bar, line, scatter, area). D3 is used directly only for the custom KM curve rendering and the ICER waterfall chart, which have non-standard layouts that Recharts cannot produce cleanly.

**Segment colors are locked throughout**
Red/Orange/Green/Blue for Clusters 0/1/2/3 appear in every chart, table badge, and card across all 8 screens. This is a deliberate cognitive design choice — a case manager who learns that "green = safe, red = urgent" in the KM curves will instantly recognize the same encoding in the patient table risk badges without reading labels.

---

*This document is the complete frontend specification. Once reviewed and approved, build begins with Phase 1 scaffolding.*