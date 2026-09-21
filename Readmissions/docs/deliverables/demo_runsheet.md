# Dashboard Demo Run-Sheet

Sequence, click paths and prepared lines for the live client walkthrough.

**~13 min · 6 acts · batch 2026-09-08 · 4,000 patients scored**

Every number below is from the current batch. If the batch changes, the numbers change.

---

## Before the meeting

Four things. The first one will embarrass you if you skip it.

### 1. Ship the Manual Entry change — the live site still has it

Manual entry is disabled locally, but the deployed backend still answers `200` on
`POST /api/patients/predict`, and "Manual Entry" is still in the live Vercel bundle.
Merge to `main` — that is the branch both platforms deploy from:

```bash
git add -A && git commit -m "Disable manual entry" && git push origin Latest && git checkout main && git merge Latest && git push origin main && git checkout Latest
```

No new environment variable needed — the flag defaults to off on both sides.
Wait for both deploys to go green before presenting.

### 2. Open every page once, 10 minutes before

Railway is always-on so there is no cold start, but load the dashboard, a patient and
Analytics anyway. It warms the model in memory and proves Atlas is reachable from wherever
you are sitting.

### 3. Check the Railway trial counter

The banner reads "30 days or $4.99 left". The clock expires first, around **14 October**.
If the demo is after that, upgrade to Hobby ($5/mo) beforehand.

### 4. Decide local or live, and stick to it

Live is more convincing and the latency is fine — 1.1 s for the dashboard. Only fall back
to `localhost` if the venue's network is unreliable.

---

## The walkthrough

Six acts. The third is the one they will remember — do not rush to it and do not skip it.

### Act 1 — Open on the whole population · 1 min

Land on the dashboard and let the header sit on screen before saying anything.

**Do:** open the dashboard root. Do not touch any filter yet.

> **Say:** "Every patient discharged from this hospital, scored before they leave. Four
> thousand of them. Six hundred and sixty are high risk — that's who this screen is for."

**On screen:** 4,000 scored · 660 High · 582 Medium · 2,758 Low.

---

### Act 2 — The worklist is ranked, not alphabetical · 2 min

Scroll the first few rows slowly. Point at the columns rather than reading them out.

**Do:** point at Current Risk → Since Discharge → Trend → Risk Band → Diagnoses → Key Risk Driver.

> **Say:** "This is a coordinator's morning queue. Highest risk at the top, and every row
> already says *why* — they don't have to open anything to triage."

**Top row:** `MIMIC-12892273` at 96.0%, worsening.

---

### Act 3 — The diagnosis catch · 3 min  ← your strongest moment

Stay on that top row. Its principal diagnosis is **"Hypotension, unspecified"**.
But the row says **Monitored as: Heart failure**.

**Do:** click `+3 more diagnoses` on the top row.

The list opens. **Chronic systolic heart failure** is there as a *secondary* diagnosis,
tagged Heart failure. Also present: acute myeloid leukemia, other primary cardiomyopathies.

> **Say:** "If we'd only read the principal diagnosis, this patient would be filed under low
> blood pressure and nobody would be watching his heart. The heart failure is the third code
> down. That's why we monitor on every diagnosis, not just the headline one."

⚠️ Have the number ready: **4 of 11** coded diagnoses are carried into the extract. If they
ask why not all eleven — that's a deliberate cap, and it's documented.

---

### Act 4 — The trend · 3 min  ← this is the actual product

Open that same patient and go to the risk trend.

**Do:** click the patient row → open the weekly trend view.

| Week | Score | What it means |
|---|---|---|
| At discharge | 64.3% | High, but so are 659 others |
| Week 1 | 66.7% | Barely moved |
| Week 2 | 74.8% | Now it's a direction |
| Week 3 | 85.3% | Escalating |
| Week 4 | **96.0%** | **+31.7 since discharge** |

The card reads **Deterioration**, with the action: *"Alert the assigned care coordinator,
increase check-in frequency, and review the discharge plan."*

Week 4's top two drivers: **weight +2.8 kg** and **medication adherence 47%**.

> **Say:** "The discharge score said 'high risk, keep an eye on him.' The trend says 'act this
> week.' And it names the two things to act on — he's holding nearly three kilos of fluid and
> he's taking less than half his medication. Both are fixable with a phone call."

---

### Act 5 — Slice it the way a real team is organised · 2 min

Back to the worklist. Open the condition filter.

**Do:** Condition filter → select `Heart failure` → then add `Diabetes` to show multi-select.

| Group | Patients | Group | Patients |
|---|---|---|---|
| Surgery or injury | 664 | Heart failure | 413 |
| Heart disease | 547 | Cancer | 395 |
| Chronic lung disease | 383 | Mental health | 374 |
| Diabetes | 302 | Stroke / neuro | 269 |

> **Say:** "Eleven condition groups. A heart failure nurse opens this and sees her 413
> patients, not four thousand. And because patients carry several conditions, you can ask for
> anyone who is *both* — that's where the hard cases live."

---

### Act 6 — Close on the numbers · 2 min

Go to Analytics. Do not read the whole table — land on two figures.

**Do:** Analytics → Model Performance Benchmarks.

| Metric | Value | Say it like this |
|---|---|---|
| AUC-ROC | 0.723 | "Show it one patient who came back and one who didn't — it ranks them correctly 72% of the time." |
| Recall | 0.601 | "It catches six in ten of the patients who do come back." |
| Precision | 0.342 | "One in three flagged actually returns — against a base rate of one in five." |

Then the **Top Drivers** table: *Gap before this admission* appears in 82% of the high-risk
cohort, *prior admissions* in 53%.

> **Say:** "It isn't a black box. Across the whole high-risk group, the single most common
> reason is that they were discharged and came straight back — which is exactly what a
> clinician would tell you to look for."

---

## Do not click these

- **The Alerts bell** — the collection is empty (0 alerts). It opens onto a blank panel and
  costs you the momentum.
- **AI Insights, without talking over it** — it works, but takes 6.5 s live. Click it and keep
  talking; do not click and wait in silence.

---

## If they ask

| Question | Answer |
|---|---|
| Is this real patient data? | Yes — MIMIC-IV, the de-identified critical care database from Beth Israel Deaconess. Trained on 296,760 hospital stays from 148,669 patients. |
| How accurate is it? | AUC-ROC 0.723, and the probabilities are calibrated — a score of 60% means roughly 60%. Patients were split so no one appears in both training and test. |
| Where do the weekly numbers come from? | The weekly series is modelled. MIMIC-IV doesn't carry post-discharge observations at a weekly cadence — its outpatient table is opportunistic, a median of 22 days to a first reading. What you're seeing is the monitoring design and the exact API a real device or pharmacy feed would populate. |
| Can we add our own patients? | Manual entry is turned off on this deployment. The intended path is a batch feed from the discharge system, not typing. |
| Can you show it was right? | Not from this screen yet — the serving database holds predictions, not outcomes. The outcome exists in the training data (19.7% readmission rate) and can be joined in. Offer it as the next step. |
| What does a coordinator actually do with it? | Open the queue, work top-down, use the driver line to decide the call. The trend view tells them who has changed since last week. |

---

## Leave-behind

Send the data dictionary — every column in the five cohort tables and the weekly collection,
with ranges, missingness and the caveats an analyst needs. It answers most follow-up questions
without another meeting.
