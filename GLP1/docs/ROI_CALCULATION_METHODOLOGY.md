# Payer ROI Calculation â€” Methodology

> **Audience:** Analytics team, health-economics reviewers, and internal engineering
> **Purpose:** Document how the Net Return on Investment metric shown in the Payer ROI dashboard is computed, term by term, with a worked example.

---

## 1. What we are calculating

The metric displayed as the hero number on the Payer ROI dashboard is **Net Program ROI** â€” the payer's expected return per dollar spent on an adherence program, over a chosen time horizon.

In plain language it answers:

> *"If we spend $1 on this adherence program, how many dollars of net financial value do we get back?"*

"Net" is important here â€” it takes into account the fact that keeping more patients on therapy also increases drug spend, and subtracts that cost from the medical savings.

A value of **`2.00Ã—`** means every $1 invested in the program returns $2 in avoided cost. A value of **`âˆ’0.50Ã—`** means every $1 invested loses $0.50.

---

## 2. The formula

For a given patient cluster at horizon `H` years:

```
                Î”Î± Â· (C_d âˆ’ C_a)  âˆ’  Î”Î± Â· D Â· (A(H) âˆ’ t_drop/365)  âˆ’  I
Net ROI(H)  =  â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                                       I
```

Every term in the numerator is expressed as **cost or savings per average patient in the cluster** over the horizon.

The population-level ROI shown at the top of the dashboard is a patient-count-weighted aggregation of the per-cluster values.

---

## 3. What each term means

| Symbol | Meaning | Where it comes from |
|---|---|---|
| **Î”Î±** | Adherence uplift the program is assumed to deliver â€” the extra fraction of patients who become adherent because of the intervention | User slider (default `0.15` = +15 percentage points) |
| **C_d** | Total downstream medical cost per patient over `H` years **if they drop out** â€” accumulates ESRD, cardiovascular events, uncontrolled T2D complications | Markov projection stored in `payer_roi` collection |
| **C_a** | Total downstream medical cost per patient over `H` years **if they stay adherent** â€” the same complication trajectory but with therapy protection | Markov projection stored in `payer_roi` collection |
| **D** | Average annual drug cost per patient (net of rebates/discounts, in USD) | `payer_roi.avg_annual_drug_cost` â€” varies by pricing scenario |
| **A(H)** | Discounted annuity factor â€” the present value of $1 paid every year for `H` years | Computed as `Î£ 1/(1+r)^i for i = 0..Hâˆ’1`, with r = 3% |
| **t_drop** | Average number of days until a dropout patient stops therapy | `payer_roi.avg_time_to_dropout_days` |
| **I** | Program cost per patient (USD) | User slider (default `$500`) |
| **r** | Annual discount rate | Constant `0.03` (3%) â€” standard health-economics convention |

### 3.1 The three parts of the numerator, unpacked

**Part 1 â€” Medical savings from higher adherence**

```
Î”Î± Â· (C_d âˆ’ C_a)
```

This is the extra medical cost we *avoid* by moving fraction `Î”Î±` of the cluster from the "dropout" trajectory to the "adherent" trajectory. Positive when adherence is genuinely protective â€” which it is for GLP-1 given complication avoidance in T2D, CV disease, and CKD.

**Part 2 â€” Extra drug spend from higher adherence**

```
Î”Î± Â· D Â· ( A(H) âˆ’ t_drop/365 )
```

This is the *additional* drug cost the payer incurs because the same fraction `Î”Î±` now stays on drug for the full horizon instead of quitting after `t_drop` days.

- `A(H)` = discounted years an adherent patient is on drug
- `t_drop/365` = fraction of a year a dropout patient was on drug before quitting
- Their difference is the extra time â€” in discounted years â€” the additional cohort is on therapy

**Part 3 â€” Program cost**

```
I
```

The per-patient investment the payer makes in the adherence program itself (outreach, coaching, digital tooling, etc.).

**Denominator:** the same `I`, so the result is expressed as a multiple of program spend.

---

## 4. The discount rate and annuity factor

We use a **3% annual discount rate**, applied to both medical savings and drug spend that occur in future years. This reflects the time value of money â€” a dollar of savings in year 10 is worth less than a dollar of savings today.

Concretely:

```
A(H)  =  1  +  1/1.03  +  1/1.03Â²  +  ...  +  1/1.03^(Hâˆ’1)
```

| Horizon `H` | Annuity factor `A(H)` |
|---|---|
| 1 year | 1.000 |
| 3 years | 2.913 |
| 5 years | 4.717 |
| 10 years | 8.786 |

Medical costs `C_d` and `C_a` are already stored as discounted cumulative values in the underlying data, so the annuity factor only appears in the extra-drug-cost term.

---

## 5. Worked example

Let us walk through the 5-year ROI for one cluster using realistic-shaped numbers. All values are per average patient in the cluster.

### 5.1 Inputs

| Variable | Value | Note |
|---|---:|---|
| Adherence uplift `Î”Î±` | 0.15 | +15 percentage points added by the program |
| Downstream cost if dropout `C_d` | $50,000 | 5-year discounted complication cost |
| Downstream cost if adherent `C_a` | $30,000 | 5-year discounted complication cost |
| Annual drug cost `D` | $1,200 | Net of rebates, for the chosen pricing scenario |
| Time-to-dropout `t_drop` | 90 days | Average across dropout patients in the cluster |
| Horizon `H` | 5 years | |
| Program cost `I` | $500 | Slider default |
| Discount rate `r` | 3% | Standard assumption |

### 5.2 Step-by-step

**Step 1 â€” Compute the annuity factor for 5 years**

```
A(5) = 1 + 1/1.03 + 1/1.03Â² + 1/1.03Â³ + 1/1.03â´
     = 1.000 + 0.971 + 0.943 + 0.915 + 0.889
     = 4.717
```

**Step 2 â€” Medical savings from higher adherence**

```
Medical savings  =  Î”Î± Â· (C_d âˆ’ C_a)
                 =  0.15 Â· ($50,000 âˆ’ $30,000)
                 =  0.15 Â· $20,000
                 =  $3,000  per average patient
```

**Step 3 â€” Extra drug spend from higher adherence**

```
Extra time on drug  =  A(5) âˆ’ t_drop/365
                    =  4.717 âˆ’ 90/365
                    =  4.717 âˆ’ 0.247
                    =  4.470  discounted years

Extra drug cost  =  Î”Î± Â· D Â· 4.470
                 =  0.15 Â· $1,200 Â· 4.470
                 =  $804  per average patient
```

**Step 4 â€” Program cost**

```
Program cost  =  I  =  $500  per patient
```

**Step 5 â€” Net ROI**

```
Numerator  =  $3,000 âˆ’ $804 âˆ’ $500
           =  $1,696

Net ROI    =  $1,696 / $500
           =  3.39Ã—
```

**Interpretation:** Every $1 invested in the adherence program returns $3.39 in net financial value to the payer over 5 years, once the extra drug spend from higher adherence is netted out of the avoided complication cost.

---

## 6. How each input moves the number

Understanding sensitivity helps interpret what a client sees when they move the sliders:

| Change | Effect on Net ROI | Why |
|---|---|---|
| **â†‘ program cost `I`** | â†“ ROI (roughly hyperbolically) | Same net dollar savings spread over a larger investment base |
| **â†‘ adherence uplift `Î”Î±`** | â†‘ ROI, but with diminishing returns | Both the savings and the extra drug cost scale with `Î”Î±`, so the *ratio* improves only if medical savings exceed drug cost per unit uplift |
| **â†‘ drug cost `D`** | â†“ ROI | Every extra adherent patient costs more in drug spend, eroding the numerator |
| **â†‘ complication gap `C_d âˆ’ C_a`** | â†‘ ROI | More medical cost to avoid per converted patient |
| **â†‘ horizon `H`** | Usually â†‘ ROI | Complication savings compound over time faster than drug spend accumulates, once the complication-avoidance mechanism kicks in |
| **â†“ time-to-dropout `t_drop`** | Modestly â†‘ ROI | Dropouts quit sooner, so the "extra time on drug" gap widens â€” but this also means the drug cost term grows |

---

## 7. Assumptions worth flagging

- **Adherent vs dropout is a binary state.** In reality, adherence is continuous. The model treats `Î”Î±` as the fraction of the cluster fully converted from dropout to adherent.
- **The Markov projection behind `C_d` and `C_a`** assumes complication risks (ESRD, CV events, uncontrolled T2D) follow published transition rates conditional on adherence status. These rates are documented in `evidence/parameter_registry.csv`.
- **Program cost `I` is treated as a single per-patient investment** â€” the formula does not apply the annuity factor to it. Interpret it as either a one-time onboarding cost or an already-annualized figure.
- **Rebates and discounts** are baked into `D` before it enters the calculation. The published WAC is not used directly.
- **Drug cost `D` varies by pricing scenario** â€” the same underlying model produces different Net ROI numbers under different assumed drug pricing environments.
- **Discount rate is fixed at 3%.** This is a modelling choice; some payers use 5%.

---

## 8. Cross-reference

| Concept | Where in code |
|---|---|
| Formula implementation | [`Backend/routers/consequence.py`](../Backend/routers/consequence.py) â€” see `get_payer_roi` handler, variable `iroi_net` |
| Annuity factor | Same file â€” `_annuity_factor()` |
| Discount rate constant | Same file â€” `_DISCOUNT_RATE = 0.03` |
| Data source | MongoDB collection `payer_roi` (populated from `Backend/data/payer_roi.csv`) |
| Frontend display | [`Frontend/src/pages/CostOfInaction/PayerROIPanel.jsx`](../Frontend/src/pages/CostOfInaction/PayerROIPanel.jsx) â€” uses `intervention_roi_net` field |
| API endpoint | `GET /api/consequence/payer-roi` |

---

*Document prepared 2026-07-29.*
