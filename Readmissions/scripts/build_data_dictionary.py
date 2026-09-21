#!/usr/bin/env python3
"""
Generate the MIMIC-IV cohort data dictionary.

Every statistic in the output is computed from the parquet files at run time -
row counts, null rates, minima, maxima, category values. Nothing is typed in by
hand, so the document cannot drift from the data it describes. Re-run it after
any change to the extract and republish.

Column meanings, lab reference ranges and Charlson labels are read from
models/mimic_drivers.py, which is the same source the dashboard uses to explain
a score to a clinician. A range shown here is therefore the range the product
applies, not one chosen for the document.

    python scripts/build_data_dictionary.py   # writes data_dictionary.html and .md

Both formats are rendered from one pass over the data and one set of column
descriptions, so they cannot disagree. The HTML is the reading copy - it has the
filter box and the sidebar. The Markdown is for anything that has to diff,
review or ingest the dictionary as text: a pull request, a repo browser, a
client who wants it in their own docs.
"""
from __future__ import annotations

import html
import json
import re
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
RESULTS = os.path.join(ROOT, "data", "mimic", "model", "results")
OUT = os.path.join(ROOT, "docs", "mimic", "data_dictionary.html")
MD_OUT = os.path.join(ROOT, "docs", "mimic", "data_dictionary.md")

from models.mimic_drivers import (_CHARLSON_LABELS, _LAB_CONCEPTS,  # noqa: E402
                                  _LAB_STATS)

TABLES = ["phase1_matrix", "phase1_timeline", "phase1_labs",
          "phase1_meds", "phase1_diagnoses"]

# What each table is called in the document. The parquet files keep their
# phase1_ prefix on disk because api/mimic_scoring.py resolves them by path;
# the prefix is a build artefact and means nothing to a reader, so the filename
# is stated once in the section note and the short name is used everywhere else.
DISPLAY = {"phase1_matrix": "matrix", "phase1_timeline": "timeline",
           "phase1_labs": "labs", "phase1_meds": "meds",
           "phase1_diagnoses": "diagnoses"}

# ---------------------------------------------------------------------------
# Column meanings
# ---------------------------------------------------------------------------
# Written once here rather than inferred from the name, because a name like
# `anchor_age` or `days_since_prev` carries a caveat that the name itself hides.

DESC = {
 "subject_id": ("De-identified patient identifier, stable across every admission that "
                "patient ever had. Not a medical record number and not reversible to one. "
                "Group by this, never by hadm_id, when you split data for modelling - the "
                "same patient appearing in both train and test leaks the outcome."),
 "hadm_id":    ("De-identified hospital admission identifier. One row per hadm_id in every "
                "table here, so it is the join key throughout."),
 "readmit_30d":("<strong>The outcome being predicted.</strong> 1 if the same patient was admitted "
                "again within 30 days of this discharge, 0 otherwise. Derived by ordering each "
                "patient's admissions by time, so it reflects readmission anywhere in the MIMIC "
                "source hospital - a readmission elsewhere is invisible and counts as 0."),
 "admission_type": ("How the stay began, as recorded by admissions. The emergency categories "
                    "(EW EMER., DIRECT EMER., URGENT) behave very differently from ELECTIVE and "
                    "SURGICAL SAME DAY ADMISSION and should not be collapsed casually."),
 "insurance":  "Primary payer recorded for the stay.",
 "marital_status": "Marital status recorded at admission. UNKNOWN is a real and common value, not missing data.",
 "race":       ("Race/ethnicity as recorded in the source system. Heavily imbalanced - WHITE is "
                "roughly two thirds of the cohort. Treat any subgroup finding on the smaller "
                "categories as underpowered."),
 "gender":     "Recorded sex, M or F. MIMIC-IV carries no other values.",
 "anchor_age": ("Patient age at their anchor year. <strong>Capped for de-identification:</strong> every "
                "patient over 89 is recorded as 91, which is why the maximum is 91 and why the "
                "top of the age distribution is a spike rather than a tail. Do not read 91 as a "
                "real age and do not fit a smooth curve through it."),
 "n_prior_adm":("Count of this patient's earlier admissions in the dataset, before this one. "
                "0 for a patient's first appearance."),
 "days_since_prev": ("Days between the previous discharge and this admission. Missing for a "
                     "patient's first admission, which is why it is 42% null - that is structural, "
                     "not a data fault. A small number of negative values indicate overlapping "
                     "admission records in the source."),
 "prior_adm_flag": "1 if n_prior_adm > 0. A convenience flag over the same information.",
 "readmit_history": "1 if the patient has any previous admission that was itself a readmission.",
 "charlson_score": ("Charlson Comorbidity Index, summed from the 17 weighted condition flags "
                    "below using the Quan et al. (2005) crosswalk applied across both ICD-9 and "
                    "ICD-10 codes. Higher means a heavier chronic disease burden. 0 is common "
                    "and means no qualifying condition was coded, not that the patient was well."),
 "n_diagnoses":"Total diagnosis codes recorded for the stay - the full count, not the four carried in the diagnoses table.",
 "n_procedures":"Count of procedure codes recorded for the stay.",
 "drg_severity": ("APR-DRG severity of illness, graded 1 (minor) to 4 (extreme). Assigned by the "
                  "grouper at coding time. Null where no APR-DRG was assigned."),
 "drg_mortality":("APR-DRG risk of mortality, graded 1 to 4 on the same scale. Null where no "
                  "APR-DRG was assigned."),
 "n_drug_orders": "Total medication orders placed during the stay. A volume proxy for intensity of care.",
 "n_distinct_drugs": "Count of distinct medications ordered. Correlates with polypharmacy.",
 "los_days":   ("Length of stay in days, discharge minus admission. A handful of negative values "
                "come from source records where the discharge timestamp precedes the admission."),
 "ed_visit":   "1 if the stay involved an emergency department registration.",
 "ed_hours":   ("Hours spent in the emergency department before admission. Null when the stay did "
                "not begin in the ED, which is why it is 42% null."),
 "is_emergency": "1 if admission_type is one of the emergency categories.",
 "disch_home": "1 if discharged to home or home with services.",
 "disch_snf":  "1 if discharged to a skilled nursing facility or similar institutional care.",
 "disch_ama":  "1 if the patient left against medical advice.",
 # timeline
 "admittime":  ("Admission timestamp <strong>as published by MIMIC-IV</strong> - shifted into the future "
                "for de-identification, which is why the years read 2105-2214. Never present these "
                "dates to anyone; use admit_real."),
 "dischtime":  "Discharge timestamp, shifted on the same offset as admittime.",
 "anchor_year":"The shifted year MIMIC anchors this patient's timeline to.",
 "anchor_year_group": ("The three-year real-world window MIMIC publishes for the patient, e.g. "
                       "'2014 - 2016'. This is the only real calendar information the source "
                       "releases, and it is what makes de-shifting possible at all."),
 "real_anchor_year": "Midpoint year of anchor_year_group, used as the de-shifting target.",
 "shift_years":"Years subtracted from the published dates to recover the real ones. Differs per patient by design.",
 "admit_real": ("Admission timestamp after de-shifting - the usable calendar date, spanning "
                "2006 to 2024. Accurate to roughly the three-year anchor window, not to the day."),
 "disch_real": "Discharge timestamp after de-shifting. Use this for any time-based analysis.",
 "date_deshifted": "Audit flag confirming the de-shift was applied to the row. True for every row.",
 # diagnoses
 "primary_diagnosis": "Long-form text of the principal diagnosis - what the stay was coded as being for.",
 "primary_icd_code":  "ICD code for the principal diagnosis, without punctuation.",
 "primary_icd_version": ("9 or 10. The cohort spans the US transition, so both appear and a code "
                         "string alone is ambiguous without this column."),
 "secondary_diagnoses": ("Text of the secondary diagnoses. <strong>Capped at three per stay</strong> "
                         "against a median of 11 coded, so this is a deliberate sample of the "
                         "comorbidity picture, not the whole of it. For full comorbidity use the "
                         "Charlson flags and n_diagnoses instead."),
 "n_diagnoses_coded": ("How many diagnoses were actually coded for the stay. Compare against the "
                       "length of secondary_diagnoses to see how much the cap dropped."),
}

QUALITY = [
 ("Lab aggregates carry no physiological bounds",
  "lab_glucose_max reaches 1,276,103 mg/dL and lab_wbc_max reaches 12,500 K/uL. These are "
  "unit or entry errors in the source that the aggregation passed straight through. They are "
  "rare - 1,814 rows (0.61%) and 243 rows (0.08%) respectively - and harmless to a tree model, "
  "which only cares about ordering. They will wreck any mean, standard deviation, correlation "
  "or linear model, and any chart on an unclipped axis. <strong>Clip before you compute.</strong>", "high"),
 ("Ages above 89 are all recorded as 91",
  "A de-identification requirement, not an error. The oldest 4% of the cohort is compressed "
  "into a single value, so age effects flatten at the top end and any age-stratified analysis "
  "should treat 91 as a censored bucket.", "med"),
 ("Secondary diagnoses are capped at three",
  "The median stay has 11 coded diagnoses. The diagnoses table carries the principal plus at most "
  "three others. Comorbidity analysis should use the 17 Charlson flags and n_diagnoses, which "
  "are computed from the complete code list.", "med"),
 ("Published dates are shifted by 89 to 194 years",
  "admittime and dischtime are not real dates. Use admit_real and disch_real, which are "
  "de-shifted using each patient's anchor_year_group and are accurate to a three-year window "
  "rather than to the day. Seasonality analysis is therefore unreliable.", "med"),
 ("A few timestamps run backwards",
  "9 stays have a negative los_days, 26 have a negative days_since_prev, and one has negative "
  "ed_hours - source records where discharge precedes admission or admissions overlap. Well "
  "under 0.01% of rows, but they will appear as impossible values in any summary.", "low"),
 ("Missingness is structural, not random",
  "days_since_prev is null for every patient's first admission (42%) and ed_hours for every "
  "stay that did not start in the ED (42%). lab_hba1c is null 91% of the time because the test "
  "is ordered for a minority of stays. Imputing these with a population mean invents a fact; "
  "the model treats missing as its own signal instead.", "high"),
]

GROUPS = [
 ("Identifiers and outcome", ["subject_id", "hadm_id", "readmit_30d"]),
 ("Demographics", ["admission_type", "insurance", "marital_status", "race", "gender", "anchor_age"]),
 ("Prior utilisation", ["n_prior_adm", "days_since_prev", "prior_adm_flag", "readmit_history"]),
 ("Charlson comorbidities", list(_CHARLSON_LABELS) + ["charlson_score"]),
 ("Coding and severity", ["n_diagnoses", "n_procedures", "drg_severity", "drg_mortality"]),
 ("Medications", ["n_drug_orders", "n_distinct_drugs", "med_insulin", "med_anticoagulant",
                  "med_opioid", "med_diuretic", "med_antipsychotic"]),
 ("Laboratory results", None),          # filled programmatically - 48 columns
 ("Stay characteristics", ["los_days", "ed_visit", "ed_hours", "is_emergency"]),
 ("Discharge disposition", ["disch_home", "disch_snf", "disch_ama"]),
]


# ---------------------------------------------------------------------------
# Profiling
# ---------------------------------------------------------------------------

def profile(df: pd.DataFrame) -> dict:
    """Measured facts per column. Everything shown in the document comes from here."""
    cols = {}
    for c in df.columns:
        s = df[c]
        d = {"dtype": str(s.dtype), "null_pct": float(s.isna().mean() * 100)}
        sample = s.dropna().iloc[0] if s.notna().any() else None

        if isinstance(sample, (np.ndarray, list)):
            lens = s.dropna().map(len)
            d.update(kind="array", rng=f"{int(lens.min())} to {int(lens.max())} items, median {lens.median():g}")
        elif pd.api.types.is_datetime64_any_dtype(s):
            nn = s.dropna()
            d.update(kind="datetime", rng=f"{nn.min():%Y-%m-%d} to {nn.max():%Y-%m-%d}")
        elif pd.api.types.is_bool_dtype(s):
            d.update(kind="bool", rng=f"{s.mean()*100:.0f}% true")
        elif pd.api.types.is_numeric_dtype(s):
            nn = s.dropna()
            u = nn.unique()
            if set(np.unique(u)) <= {0, 1}:
                d.update(kind="flag", rng=f"{nn.mean()*100:.1f}% are 1")
            elif len(u) <= 6:
                d.update(kind="ordinal", rng="one of " + ", ".join(f"{x:g}" for x in sorted(u)))
            else:
                # %g turns identifiers into 1e+07, which tells a reader nothing.
                # Integers print as integers; only genuine decimals keep places.
                whole = float(nn.min()).is_integer() and float(nn.max()).is_integer()
                fmt = (lambda v: f"{v:,.0f}") if whole else (lambda v: f"{v:,.2f}".rstrip("0").rstrip("."))
                d.update(kind="number",
                         rng=f"{fmt(nn.min())} to {fmt(nn.max())}, median {fmt(nn.median())}")
        else:
            nn = s.dropna()
            u = nn.unique()
            d["kind"] = "category"
            d["rng"] = (", ".join(sorted(str(x) for x in u)) if len(u) <= 8
                        else f"{len(u):,} distinct; most common {nn.value_counts().index[0]}")
        cols[c] = d
    return cols


def lab_columns() -> list:
    """The 48 lab features, in the order the extract writes them."""
    stats = list(_LAB_STATS) + ["n_abn"]
    return [f"lab_{concept}_{stat}" for stat in stats for concept in _LAB_CONCEPTS]


def lab_description(col: str) -> str:
    _, concept, stat = col.split("_", 2)
    name, _, _, lo, hi, unit = _LAB_CONCEPTS[concept]
    unit = unit.strip()
    band = f"{lo}–{hi}{(' ' + unit) if unit else ''}"
    if stat == "n_abn":
        return (f"How many {name.lower()} results during the stay fell outside {band}. "
                f"A count, not a measurement - 0 means every result was normal.")
    phrase = _LAB_STATS[stat]
    return f"{name}, {phrase}. Reference range {band}."


CSS = """
:root{
  --bg:#f6f8f9; --surface:#fff; --surface-2:#eef2f5; --ink:#141e27; --ink-2:#3d4d5a;
  --muted:#697a88; --line:#dbe3e9; --line-2:#c6d2db;
  --accent:#0d6b78; --accent-soft:#e2f0f2;
  --hi:#a32a37; --hi-bg:#fbeaec; --med:#8a5a09; --med-bg:#fbf1de; --low:#3f6b46; --low-bg:#e9f2ea;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --bg:#0f161c; --surface:#151e25; --surface-2:#1b262f; --ink:#e6ecf1; --ink-2:#c2ced8;
    --muted:#8ca0af; --line:#25313b; --line-2:#33424e;
    --accent:#54b6c2; --accent-soft:#123037;
    --hi:#f08a95; --hi-bg:#3a1b20; --med:#e0b264; --med-bg:#362a14; --low:#8fc79a; --low-bg:#1b2e20;
  }
}
:root[data-theme="dark"]{
  --bg:#0f161c; --surface:#151e25; --surface-2:#1b262f; --ink:#e6ecf1; --ink-2:#c2ced8;
  --muted:#8ca0af; --line:#25313b; --line-2:#33424e;
  --accent:#54b6c2; --accent-soft:#123037;
  --hi:#f08a95; --hi-bg:#3a1b20; --med:#e0b264; --med-bg:#362a14; --low:#8fc79a; --low-bg:#1b2e20;
}
*{box-sizing:border-box}
body{
  margin:0; background:var(--bg); color:var(--ink);
  font-family:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
  font-size:15px; line-height:1.6; -webkit-font-smoothing:antialiased;
}
code,.mono{font-family:"IBM Plex Mono",ui-monospace,"SFMono-Regular",Menlo,monospace}
h1,h2,h3{font-family:"Source Serif 4",Georgia,serif; font-weight:600; text-wrap:balance; margin:0}
a{color:var(--accent)}

.wrap{display:grid; grid-template-columns:230px minmax(0,1fr); gap:40px;
      max-width:1280px; margin:0 auto; padding:0 28px}
nav{position:sticky; top:0; align-self:start; max-height:100vh; overflow-y:auto;
    padding:38px 0 40px; border-right:1px solid var(--line)}
nav .eyebrow{font-size:10.5px; letter-spacing:.13em; text-transform:uppercase;
             color:var(--muted); margin:22px 0 9px; font-weight:600}
nav a{display:block; padding:4px 12px 4px 0; color:var(--ink-2); text-decoration:none;
      font-size:13.5px; border-left:2px solid transparent; padding-left:11px; margin-left:-1px}
nav a:hover{color:var(--accent); border-left-color:var(--accent)}
main{padding:38px 0 90px; min-width:0}

header.top{border-bottom:1px solid var(--line); padding-bottom:26px; margin-bottom:30px}
header.top h1{font-size:2.35rem; line-height:1.15; letter-spacing:-.015em}
header.top .sub{color:var(--muted); margin-top:9px; max-width:64ch}

.facts{display:grid; grid-template-columns:repeat(auto-fit,minmax(126px,1fr)); gap:1px;
       background:var(--line); border:1px solid var(--line); border-radius:9px;
       overflow:hidden; margin:26px 0 8px}
.fact{background:var(--surface); padding:14px 16px}
.fact .n{font-family:"Source Serif 4",Georgia,serif; font-size:1.5rem; font-weight:600;
         font-variant-numeric:tabular-nums; letter-spacing:-.01em; display:block}
.fact .k{font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:.07em; margin-top:2px}

section{margin:52px 0 0; scroll-margin-top:20px}
section > h2{font-size:1.5rem; letter-spacing:-.01em}
section > .note{color:var(--muted); font-size:14px; margin:7px 0 0; max-width:74ch}
.file{font-family:"IBM Plex Mono",monospace; font-size:11px; color:var(--muted);
      background:var(--surface-2); border:1px solid var(--line); border-radius:4px;
      padding:1px 6px; white-space:nowrap}
h3.grp{font-size:12px; text-transform:uppercase; letter-spacing:.1em; color:var(--accent);
       font-family:"IBM Plex Sans",sans-serif; font-weight:600; margin:30px 0 9px}

.scroll{overflow-x:auto; border:1px solid var(--line); border-radius:9px; background:var(--surface)}
table{border-collapse:collapse; width:100%; min-width:620px; font-size:13.5px}
th{position:sticky; top:0; background:var(--surface-2); text-align:left; font-weight:600;
   font-size:10.5px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted);
   padding:9px 13px; border-bottom:1px solid var(--line-2); white-space:nowrap; z-index:1}
td{padding:11px 13px; border-top:1px solid var(--line); vertical-align:top}
tr:first-child td{border-top:none}
td.name code{font-size:12.5px; font-weight:500; color:var(--ink)}
td.type{white-space:nowrap; font-size:11.5px; color:var(--muted); font-family:"IBM Plex Mono",monospace}
td.rng{font-family:"IBM Plex Mono",monospace; font-size:11.5px; color:var(--ink-2);
       font-variant-numeric:tabular-nums; width:20%; min-width:130px}
td.desc{color:var(--ink-2); width:46%}
td.name{width:17%} td.type{width:9%}
.miss{font-variant-numeric:tabular-nums; font-family:"IBM Plex Mono",monospace; font-size:11.5px;
      white-space:nowrap; text-align:right}
.miss.warn{color:var(--med); font-weight:600}
.miss.zero{color:var(--muted); opacity:.5}

.flags{display:grid; gap:11px; margin-top:18px}
.flag{border:1px solid var(--line); border-left:3px solid var(--line-2);
      border-radius:7px; background:var(--surface); padding:14px 17px}
.flag.high{border-left-color:var(--hi)} .flag.med{border-left-color:var(--med)}
.flag.low{border-left-color:var(--low)}
.flag h4{margin:0 0 4px; font-size:14.5px; font-family:"IBM Plex Sans",sans-serif; font-weight:600}
.flag p{margin:0; font-size:13.5px; color:var(--ink-2)}
.sev{float:right; font-size:9.5px; letter-spacing:.1em; text-transform:uppercase; font-weight:700;
     padding:2px 7px; border-radius:20px; margin-left:10px}
.sev.high{background:var(--hi-bg); color:var(--hi)} .sev.med{background:var(--med-bg); color:var(--med)}
.sev.low{background:var(--low-bg); color:var(--low)}

.filter{position:sticky; top:0; z-index:3; background:var(--bg); padding:13px 0 11px;
        border-bottom:1px solid var(--line); margin-bottom:4px}
.filter input{width:100%; padding:9px 13px; font:inherit; font-size:14px; color:var(--ink);
              background:var(--surface); border:1px solid var(--line-2); border-radius:7px}
.filter input:focus{outline:2px solid var(--accent); outline-offset:1px; border-color:transparent}
.filter .count{font-size:12px; color:var(--muted); margin-top:6px; font-variant-numeric:tabular-nums}
tr.hide{display:none}

@media (max-width:1060px){
  .wrap{grid-template-columns:1fr; gap:0; padding:0 18px}
  nav{position:static; max-height:none; border-right:none; border-bottom:1px solid var(--line);
      padding:20px 0; columns:2}
  main{padding-top:22px}
}
"""

JS = """
const box=document.getElementById('q'), rows=[...document.querySelectorAll('tbody tr')],
      cnt=document.getElementById('cnt'), total=rows.length;
function apply(){
  const q=box.value.trim().toLowerCase();
  let n=0;
  for(const r of rows){
    const hit=!q||r.dataset.s.includes(q);
    r.classList.toggle('hide',!hit); if(hit)n++;
  }
  cnt.textContent = q ? `${n} of ${total} fields match` : `${total} fields across 5 tables and 1 collection`;
  for(const s of document.querySelectorAll('section[data-tbl]')){
    const any=[...s.querySelectorAll('tbody tr')].some(r=>!r.classList.contains('hide'));
    s.style.display=any?'':'none';
  }
  for(const h of document.querySelectorAll('h3.grp')){
    const t=h.nextElementSibling;
    if(t&&t.classList.contains('scroll')){
      const any=[...t.querySelectorAll('tbody tr')].some(r=>!r.classList.contains('hide'));
      h.style.display=any?'':'none'; t.style.display=any?'':'none';
    }
  }
}
box.addEventListener('input',apply); apply();
"""


TABLE_NOTES = {
 "phase1_matrix": ("The modelling table. One row per hospital stay, carrying the outcome and all "
                   "94 predictors. Everything in the other four tables is either folded into this "
                   "one or is supporting detail for it. If you only read one table, read this."),
 "phase1_timeline": ("Admission and discharge timing, and the de-identification bookkeeping needed "
                     "to recover real calendar dates. Join on hadm_id when you need to place a stay "
                     "in time."),
 "phase1_labs": ("The 48 laboratory features on their own, for stays that had at least one result. "
                 "25,684 stays (8.7%) are absent entirely because no qualifying test was run. These "
                 "same columns already appear in the matrix table."),
 "phase1_meds": ("Medication counts and drug-class exposure flags. 2,195 stays (0.7%) have no "
                 "medication record. These columns also appear in the matrix table."),
 "phase1_diagnoses": ("Diagnosis text and codes per stay. This is the only table with human-readable "
                      "clinical text, and the only one where the three-secondary cap applies."),
}


# ---------------------------------------------------------------------------
# Weekly monitoring  (MongoDB, not parquet)
# ---------------------------------------------------------------------------
# A different kind of data from everything above. MIMIC-IV does hold some
# post-discharge observations - the `omr` table carries Weight, BP, BMI and
# Height from outpatient visits - but scripts/mimic_feasibility.py measured the
# cadence and found it opportunistic rather than scheduled: median 22 days to a
# patient's first reading, and only 16.9% of discharges with readings in two
# distinct weeks of the 30-day window, against a 25% viability line. None of the
# signals this product tracks weekly (adherence, refill, SpO2, symptoms) exist
# there at all. The weekly series is therefore produced by
# models/monitoring_rules.py, which is what `source` and `trajectory` record.

WEEKLY_DESC = {
 "patient_id": "Dashboard patient identifier, matching patient_worklist. Prefixed MIMIC- and derived from subject_id.",
 "week_number": ("<strong>Week 0 is the discharge baseline</strong> and carries no monitoring "
                 "sub-document; weeks 1 to 4 are the post-discharge series, and that is every row "
                 "but two. A patient logging their own week can extend their series past week 4, "
                 "which is the only reason any row reads 5 or 6."),
 "days_after_discharge": "Days since discharge, 0 at week 0 then 7 per week.",
 "week_date": "Calendar date the week's observations belong to.",
 "risk_score": ("Readmission risk for that week, 0 to 100. At week 0 this is the model's calibrated "
                "discharge probability. From week 1 it is that baseline plus the rule layer's "
                "adjustment plus a carry term from the previous week."),
 "risk_band": "Low below 20, Medium 20 to under 40, High 40 and above. Fixed product bands, not quantiles.",
 "rule_adjustment": "Points the rule layer added or removed this week, before the carry term. Present only on patient-logged weeks.",
 "scored_by": ("<code>model</code> at week 0, <code>monitoring_rules</code> from week 1. This is the "
               "cleanest way to tell a model score from a rule-adjusted one."),
 "source": ("Origin of the row. <code>patient_reported</code> is a week a patient logged through "
            "the portal; <code>scheduled</code> is a week produced by the monitoring schedule."),
 "trajectory": ("The recovery arc assigned to this patient, <code>recovering</code> or "
                "<code>deteriorating</code>. Sets the direction their weekly signals move."),
 "observed": "Whether observations exist for the week. False means the week was not reported.",
 "driver_1": "Top contributing signal for the week, as a sentence with its value and why it matters.",
 "driver_2": "Second contributing signal, same format.",
 "driver_3": "Third contributing signal, same format.",
 "model_version": "Identifier of the model that produced the week 0 baseline.",
 "clinical_group": ("Monitoring group the patient was routed to, from their diagnoses. Decides which "
                    "disease-specific signals appear in the monitoring sub-document."),
 "group_label": "Human-readable name of clinical_group, as shown in the dashboard.",
 "group_evidence": "Which diagnosis placed the patient in the group, e.g. matched on a secondary diagnosis.",
 "group_confidence": ("<code>high</code> matched an ICD code, <code>moderate</code> matched diagnosis text "
                      "only, <code>default</code> nothing matched and the patient fell back to general monitoring."),
 "monitoring": "Sub-document of the week's observations. Absent at week 0. Fields are listed below.",
 "discharge_baseline": "Sub-document of the patient's discharge reference values. Present only at week 0.",
 "note": "Free-text note from a patient-logged week.",
 "logged_at": "Timestamp of a patient-logged week.",
 "logged_by": "Account that logged the week. Only present on patient-reported rows.",
 "reported_fields": "Which fields the patient actually supplied on a self-logged week.",
}

WEEKLY_SIGNALS = {
 "weight_change_kg": ("Weight change since discharge, in kg. A gain over 2 kg in a week is the classic "
                      "fluid-retention signal in heart failure.", "universal"),
 "adherence_pct": ("Percentage of prescribed doses covered this week.", "universal"),
 "refill_status": ("Whether the prescription due this week was collected.", "universal"),
 "followup_status": ("Whether the scheduled follow-up appointment was attended.", "universal"),
 "sbp": ("Systolic blood pressure, mmHg.", "universal"),
 "heart_rate": ("Resting heart rate, beats per minute.", "universal"),
 "spo2": ("Oxygen saturation, percent.", "universal"),
 "walk_distance_pct": ("Walking distance as a percentage of the patient's usual distance at discharge.", "mobility"),
 "temperature_c": ("Body temperature in Celsius. Collected where infection is a concern.", "infection"),
 "orthopnoea_pillows": ("Pillows needed to sleep without breathlessness. Heart failure.", "heart failure"),
 "ankle_swelling": ("Ankle oedema. Heart failure.", "heart failure"),
 "wound_status": ("Surgical wound appearance. Surgical and injury patients.", "surgical"),
 "pain_trend": ("Direction of pain since last week. Surgical and injury patients.", "surgical"),
 "rescue_inhaler_uses": ("Rescue inhaler actuations this week. Respiratory patients.", "respiratory"),
 "sputum_change": ("Change in sputum volume or character. Respiratory patients.", "respiratory"),
 "antibiotic_course": ("Progress through a prescribed antibiotic course. Sepsis and infection.", "infection"),
 "new_confusion": ("New-onset confusion, a red flag for sepsis in older patients.", "infection"),
}

WEEKLY_BASELINE = {
 "dry_weight_kg": "Weight at discharge, the reference weight_change_kg is measured against.",
 "baseline_spo2": "Oxygen saturation at discharge.",
 "baseline_sbp": "Systolic blood pressure at discharge.",
 "baseline_hr": "Resting heart rate at discharge.",
 "usual_walk_metres": "Usual walking distance at discharge, the reference walk_distance_pct is measured against.",
 "baseline_pain": "Pain score at discharge, 0 to 10.",
 "source": "How the baseline was produced.",
 "group": "Clinical group the baseline was derived for.",
}


_HEAVY_SAMPLE: dict = {}


# Raw min/max misleads where a handful of rows sit far outside the bulk. The
# span shown for these fields is the one that describes 99.99% of the data,
# with the tail stated rather than silently widening the range.
RANGE_OVERRIDE = {
    "week_number": "0 to 4 for 20,000 rows; 2 logged rows reach 5 and 6. Median 2",
}


def profile_weekly():
    """Profile the weekly collection. Returns None if MongoDB is unreachable."""
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(ROOT, ".env"))
        from api.db_utils import get_mongo_client
        db = get_mongo_client(os.environ["MONGO_URI"])["neuroshield"]
        # driver_1..3 are long sentences and dominate the transfer. The profile
        # only needs their presence and type, so a short slice supplies those and
        # the rest of the scan runs without them.
        heavy = ["driver_1", "driver_2", "driver_3", "group_evidence", "note"]
        docs = list(db["weekly_monitoring"].find(
            {}, {"_id": 0, **{h: 0 for h in heavy}}))
        for probe in db["weekly_monitoring"].find({}, {"_id": 0, **{h: 1 for h in heavy}}).limit(400):
            for k, v in probe.items():
                _HEAVY_SAMPLE.setdefault(k, []).append(v)
    except Exception as exc:                       # noqa: BLE001
        print(f"  ! weekly section skipped, MongoDB unreachable: {exc}")
        return None

    n = len(docs)
    flat, signals, baseline = {}, {}, {}
    for d in docs:
        for k, v in d.items():
            flat.setdefault(k, []).append(v)
        for k, v in (d.get("monitoring") or {}).items():
            signals.setdefault(k, []).append(v)
        for k, v in (d.get("discharge_baseline") or {}).items():
            baseline.setdefault(k, []).append(v)

    def summarise(store, total):
        out = {}
        for k, vals in store.items():
            nums = [v for v in vals if isinstance(v, (int, float)) and not isinstance(v, bool)]
            if nums and len(set(nums)) > 6:
                nums_s = sorted(nums)
                rng = f"{min(nums):,g} to {max(nums):,g}, median {nums_s[len(nums_s)//2]:,g}"
            else:
                uniq = sorted({str(v) for v in vals})
                rng = ", ".join(uniq[:8]) if len(uniq) <= 8 else f"{len(uniq):,} distinct"
            out[k] = {"present": len(vals) / total * 100,
                      "dtype": type(vals[0]).__name__,
                      "rng": RANGE_OVERRIDE.get(k, rng)}
        return out

    flat_sum = summarise(flat, n)
    probe_n = max(len(v) for v in _HEAVY_SAMPLE.values()) if _HEAVY_SAMPLE else 0
    for k, vals in _HEAVY_SAMPLE.items():
        flat_sum[k] = {"present": len(vals) / probe_n * 100 if probe_n else 0,
                       "dtype": type(vals[0]).__name__, "rng": "free text"}

    return {"n": n, "patients": len({d["patient_id"] for d in docs}),
            "flat": flat_sum,
            "signals": summarise(signals, n),
            "baseline": summarise(baseline, n)}


def weekly_rows(prof: dict, descs: dict, tag=None) -> str:
    out = []
    for k, p in sorted(prof.items(), key=lambda kv: -kv[1]["present"]):
        if isinstance(descs.get(k), tuple):
            desc, scope = descs[k]
            desc = f'<strong>{esc(scope)}</strong> — {desc}'
        else:
            desc = descs.get(k, "—")
        pres = p["present"]
        cls = "zero" if pres >= 99.9 else ("warn" if pres < 50 else "")
        ptxt = "all rows" if pres >= 99.9 else f"{pres:.0f}%"
        search = f"{k} {html.unescape(desc)} {p['rng']}".lower()
        out.append(f'<tr data-s="{esc(search)}">'
                   f'<td class="name"><code>{esc(k)}</code></td>'
                   f'<td class="type">{esc(p["dtype"])}</td>'
                   f'<td class="miss {cls}">{ptxt}</td>'
                   f'<td class="rng">{esc(p["rng"])}</td>'
                   f'<td class="desc">{desc}</td></tr>')
    return ('<div class="scroll"><table><thead><tr>'
            '<th>Field</th><th>Type</th><th>Present on</th><th>Range / values</th><th>Meaning</th>'
            '</tr></thead><tbody>' + "".join(out) + '</tbody></table></div>')



def esc(x) -> str:
    return html.escape(str(x))


def describe(n: str) -> str:
    """
    What a matrix column means, as a fragment of HTML.

    Lives here rather than inside the HTML renderer because the Markdown
    renderer needs exactly the same answer. Two copies of this logic would drift
    the moment a lab range changed, and the whole point of generating the
    document is that it cannot drift from the data.
    """
    if n.startswith("lab_") and n != "lab_id":
        return lab_description(n)
    if n in _CHARLSON_LABELS:
        return (f"Charlson flag: 1 if <strong>{esc(_CHARLSON_LABELS[n].lower())}</strong> was coded "
                f"for this stay. Mapped from ICD-9 and ICD-10 via Quan et al. (2005).")
    if n.startswith("med_"):
        return (f"1 if any <strong>{esc(n[4:])}</strong> was ordered during the stay. Exposure only - "
                f"it carries no dose, duration or indication.")
    return DESC.get(n, "—")


def rows_html(cols: dict, names: list, table: str) -> str:
    out = []
    for n in names:
        if n not in cols:
            continue
        p = cols[n]
        desc = describe(n)
        miss = p["null_pct"]
        cls = "zero" if miss == 0 else ("warn" if miss >= 30 else "")
        mtxt = "—" if miss == 0 else f"{miss:.1f}%"
        search = f"{n} {html.unescape(desc)} {p['rng']}".lower()
        out.append(
            f'<tr data-s="{esc(search)}">'
            f'<td class="name"><code>{esc(n)}</code></td>'
            f'<td class="type">{esc(p["dtype"])}</td>'
            f'<td class="miss {cls}">{mtxt}</td>'
            f'<td class="rng">{esc(p["rng"])}</td>'
            f'<td class="desc">{desc}</td></tr>')
    if not out:
        return ""
    return ('<div class="scroll"><table><thead><tr>'
            '<th>Column</th><th>Type</th><th>Missing</th><th>Range / values</th><th>Meaning</th>'
            '</tr></thead><tbody>' + "".join(out) + '</tbody></table></div>')


def gather() -> dict:
    """
    One pass over the parquet files and MongoDB.

    Separated from rendering so the HTML and the Markdown are built from the
    same numbers in the same run - reading the data twice would let the two
    documents disagree if anything were written between them.
    """
    prof, meta = {}, {}
    for t in TABLES:
        df = pd.read_parquet(os.path.join(RESULTS, t + ".parquet"))
        prof[t] = profile(df)
        meta[t] = (len(df), df.shape[1])

    m = pd.read_parquet(os.path.join(RESULTS, "phase1_matrix.parquet"),
                        columns=["subject_id", "readmit_30d"])
    stays, patients = len(m), m.subject_id.nunique()
    rate = m.readmit_30d.mean() * 100
    total_cols = sum(v[1] for v in meta.values())

    return {
        "prof": prof, "meta": meta, "stays": stays, "patients": patients,
        "rate": rate, "total_cols": total_cols,
        "groups": [(t, lab_columns() if c is None else c) for t, c in GROUPS],
        "wk": profile_weekly(),
    }


def build(d: dict) -> str:
    prof, meta, wk, groups = d["prof"], d["meta"], d["wk"], d["groups"]
    stays, patients = d["stays"], d["patients"]
    rate, total_cols = d["rate"], d["total_cols"]

    nav = ['<div class="eyebrow">Start here</div>',
           '<a href="#about">What this covers</a>', '<a href="#quality">Before you analyse</a>',
           '<div class="eyebrow">Modelling table</div>']
    nav += [f'<a href="#g{i}">{esc(t)}</a>' for i, (t, _) in enumerate(groups)]
    nav.append('<div class="eyebrow">Supporting tables</div>')
    nav += [f'<a href="#{t}">{esc(DISPLAY[t])}</a>' for t in TABLES[1:]]
    if wk:
        nav += ['<div class="eyebrow">Post-discharge</div>',
                '<a href="#weekly">weekly monitoring</a>',
                '<a href="#signals">observed signals</a>',
                '<a href="#baseline">discharge baseline</a>']

    body = [
      '<header class="top"><h1>MIMIC-IV Readmission Cohort</h1>',
      '<p class="sub">A data dictionary for every column in the five tables behind the Preventra '
      'readmission model. Each figure below is measured from the data itself, not transcribed.</p>',
      '<div class="facts">',
      f'<div class="fact"><span class="n">{stays:,}</span><span class="k">Hospital stays</span></div>',
      f'<div class="fact"><span class="n">{patients:,}</span><span class="k">Patients</span></div>',
      f'<div class="fact"><span class="n">{total_cols}</span><span class="k">Columns</span></div>',
      f'<div class="fact"><span class="n">{rate:.1f}%</span><span class="k">Readmitted in 30 days</span></div>',
      '</div></header>',

      '<section id="about"><h2>What this covers</h2>',
      '<p class="note">Five parquet tables derived from the MIMIC-IV <code>hosp</code> module, '
      'plus one MongoDB collection holding the post-discharge weekly series. '
      'Every table has one row per hospital stay, keyed on <code>hadm_id</code>, so they join '
      'cleanly. <code>matrix</code> is the modelling table and already contains the lab and '
      'medication features; the separate tables exist so you can work with those groups without '
      'loading 97 columns.</p>',
      f'<p class="note" style="margin-top:12px">The cohort is {stays:,} stays from {patients:,} '
      'patients — MIMIC-IV stays that met the modelling criteria, not the whole of MIMIC-IV. '
      f'{rate:.1f}% end in a readmission within 30 days, which is the outcome the model predicts.</p>',
      '</section>',

      '<section id="quality"><h2>Before you analyse</h2>',
      '<p class="note">Six things in this data will produce wrong answers if you do not know about '
      'them. None is a defect in the extract; all are properties of the source or of '
      'de-identification.</p><div class="flags">']
    for title, text, sev in QUALITY:
        body.append(f'<div class="flag {sev}"><span class="sev {sev}">{sev}</span>'
                    f'<h4>{esc(title)}</h4><p>{text}</p></div>')
    body.append('</div></section>')

    body.append('<div class="filter"><input id="q" type="search" '
                'placeholder="Filter columns — try &ldquo;sodium&rdquo;, &ldquo;charlson&rdquo;, &ldquo;null&rdquo;, &ldquo;discharge&rdquo;" '
                'aria-label="Filter columns"><div class="count" id="cnt"></div></div>')

    body.append(f'<section data-tbl="1" id="phase1_matrix"><h2>matrix</h2>'
                f'<p class="note">{TABLE_NOTES["phase1_matrix"]} '
                f'<strong>{meta["phase1_matrix"][0]:,} rows · {meta["phase1_matrix"][1]} columns.</strong> '
                f'<span class="file">phase1_matrix.parquet</span></p>')
    for i, (title, names) in enumerate(groups):
        body.append(f'<h3 class="grp" id="g{i}">{esc(title)}</h3>')
        body.append(rows_html(prof["phase1_matrix"], names, "phase1_matrix"))
    body.append('</section>')

    for t in TABLES[1:]:
        body.append(f'<section data-tbl="1" id="{t}"><h2>{esc(DISPLAY[t])}</h2>'
                    f'<p class="note">{TABLE_NOTES[t]} '
                    f'<strong>{meta[t][0]:,} rows · {meta[t][1]} columns.</strong> '
                    f'<span class="file">{esc(t)}.parquet</span></p>')
        body.append(rows_html(prof[t], list(prof[t]), t))
        body.append('</section>')

    if wk:
        body.append(
          f'<section data-tbl="1" id="weekly"><h2>weekly monitoring</h2>'
          f'<p class="note">The post-discharge series behind the dashboard\'s risk trend. '
          f'<strong>{wk["n"]:,} documents · {wk["patients"]:,} patients · 5 weeks each.</strong> '
          f'<span class="file">MongoDB · weekly_monitoring</span></p>'
          '<h3 class="grp" id="weekly-fields">Document fields</h3>'
          + weekly_rows(wk["flat"], WEEKLY_DESC))

        body.append(
          '<h3 class="grp" id="signals">Observed signals — the <code>monitoring</code> sub-document</h3>'
          '<p class="note" style="margin-bottom:10px">Absent at week 0. Seven signals are collected for '
          'everyone; the rest appear only for the clinical groups they are meaningful to, which is why '
          'their presence rates are low. A low rate here means <em>not applicable to this patient</em>, '
          'not missing data.</p>'
          + weekly_rows(wk["signals"], WEEKLY_SIGNALS))

        body.append(
          '<h3 class="grp" id="baseline">Discharge baseline — the <code>discharge_baseline</code> sub-document</h3>'
          '<p class="note" style="margin-bottom:10px">Week 0 only. These are the reference values every '
          'later week is compared against — a 2 kg gain means 2 kg above <code>dry_weight_kg</code>.</p>'
          + weekly_rows(wk["baseline"], WEEKLY_BASELINE) + '</section>')

    return (
      '<title>MIMIC-IV Readmission Cohort</title>\n'
      '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
      '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
      '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
      'family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&'
      'family=Source+Serif+4:opsz,wght@8..60,600&display=swap">\n'
      f'<style>{CSS}</style>\n'
      f'<div class="wrap"><nav>{"".join(nav)}</nav><main>{"".join(body)}</main></div>\n'
      f'<script>{JS}</script>')


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------
# Same content, same numbers, rendered as text. The descriptions are authored as
# HTML fragments because the HTML document is the primary one, so the only work
# here is translating the two inline tags they use and protecting the table
# syntax.

_MD_INLINE = [
    (re.compile(r"</?strong>"), "**"),
    (re.compile(r"</?em>"), "*"),
    (re.compile(r"</?code>"), "`"),
]


def md(x) -> str:
    """An HTML description fragment as Markdown, safe to put in a table cell."""
    text = str(x)
    for pattern, replacement in _MD_INLINE:
        text = pattern.sub(replacement, text)
    text = html.unescape(text)
    # A pipe inside a cell ends the cell. Ranges like "a | b" are the usual
    # source, and the escape has to happen after unescaping or &verbar; slips
    # through unprotected.
    return text.replace("|", "\\|").replace("\n", " ").strip()


def md_table(header: list, rows: list) -> str:
    if not rows:
        return ""
    out = ["| " + " | ".join(header) + " |",
           "|" + "|".join(["---"] * len(header)) + "|"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(out) + "\n"


def rows_md(cols: dict, names: list) -> str:
    rows = []
    for n in names:
        if n not in cols:
            continue
        p = cols[n]
        miss = p["null_pct"]
        rows.append([f"`{n}`", md(p["dtype"]),
                     "—" if miss == 0 else f"{miss:.1f}%",
                     md(p["rng"]), md(describe(n))])
    return md_table(["Column", "Type", "Missing", "Range / values", "Meaning"], rows)


def weekly_rows_md(prof: dict, descs: dict) -> str:
    rows = []
    for k, p in sorted(prof.items(), key=lambda kv: -kv[1]["present"]):
        if isinstance(descs.get(k), tuple):
            desc, scope = descs[k]
            desc = f"**{scope}** — {desc}"
        else:
            desc = descs.get(k, "—")
        pres = p["present"]
        rows.append([f"`{k}`", md(p["dtype"]),
                     "all rows" if pres >= 99.9 else f"{pres:.0f}%",
                     md(p["rng"]), md(desc)])
    return md_table(["Field", "Type", "Present on", "Range / values", "Meaning"], rows)


def _anchor(title: str) -> str:
    """GitHub-style heading anchor, for the contents list."""
    return re.sub(r"[^a-z0-9\s-]", "", title.lower()).strip().replace(" ", "-")


def build_markdown(d: dict) -> str:
    prof, meta, wk, groups = d["prof"], d["meta"], d["wk"], d["groups"]
    stays, patients = d["stays"], d["patients"]
    rate, total_cols = d["rate"], d["total_cols"]

    out = [
        "# MIMIC-IV Readmission Cohort",
        "",
        "A data dictionary for every column in the five tables behind the Preventra "
        "readmission model. Each figure below is measured from the data itself, not "
        "transcribed.",
        "",
        "> Generated by `scripts/build_data_dictionary.py`. Do not edit by hand — "
        "re-run it after any change to the extract.",
        "",
        "| Hospital stays | Patients | Columns | Readmitted in 30 days |",
        "|---|---|---|---|",
        f"| {stays:,} | {patients:,} | {total_cols} | {rate:.1f}% |",
        "",
        "## Contents",
        "",
        "- [What this covers](#what-this-covers)",
        "- [Before you analyse](#before-you-analyse)",
        "- [matrix](#matrix) — the modelling table",
    ]
    out += [f"    - [{t}](#{_anchor(t)})" for t, _ in groups]
    out += [f"- [{DISPLAY[t]}](#{_anchor(DISPLAY[t])})" for t in TABLES[1:]]
    if wk:
        out += ["- [weekly monitoring](#weekly-monitoring)",
                "    - [Observed signals](#observed-signals)",
                "    - [Discharge baseline](#discharge-baseline)"]

    out += [
        "",
        "## What this covers",
        "",
        "Five parquet tables derived from the MIMIC-IV `hosp` module, plus one MongoDB "
        "collection holding the post-discharge weekly series. Every table has one row per "
        "hospital stay, keyed on `hadm_id`, so they join cleanly. `matrix` is the modelling "
        "table and already contains the lab and medication features; the separate tables "
        "exist so you can work with those groups without loading 97 columns.",
        "",
        f"The cohort is {stays:,} stays from {patients:,} patients — MIMIC-IV stays that met "
        f"the modelling criteria, not the whole of MIMIC-IV. {rate:.1f}% end in a readmission "
        "within 30 days, which is the outcome the model predicts.",
        "",
        "## Before you analyse",
        "",
        "Six things in this data will produce wrong answers if you do not know about them. "
        "None is a defect in the extract; all are properties of the source or of "
        "de-identification.",
        "",
    ]
    for title, text, sev in QUALITY:
        out += [f"### {title}", "", f"**{sev.upper()}** — {md(text)}", ""]

    out += [
        "## matrix",
        "",
        f"{md(TABLE_NOTES['phase1_matrix'])} "
        f"**{meta['phase1_matrix'][0]:,} rows · {meta['phase1_matrix'][1]} columns.** "
        "`phase1_matrix.parquet`",
        "",
    ]
    for title, names in groups:
        out += [f"### {title}", "", rows_md(prof["phase1_matrix"], names)]

    for t in TABLES[1:]:
        out += [
            f"## {DISPLAY[t]}",
            "",
            f"{md(TABLE_NOTES[t])} **{meta[t][0]:,} rows · {meta[t][1]} columns.** "
            f"`{t}.parquet`",
            "",
            rows_md(prof[t], list(prof[t])),
        ]

    if wk:
        out += [
            "## weekly monitoring",
            "",
            "The post-discharge series behind the dashboard's risk trend. "
            f"**{wk['n']:,} documents · {wk['patients']:,} patients · 5 weeks each.** "
            "MongoDB · `weekly_monitoring`",
            "",
            "### Document fields",
            "",
            weekly_rows_md(wk["flat"], WEEKLY_DESC),
            "### Observed signals",
            "",
            "The `monitoring` sub-document. Absent at week 0. Seven signals are collected for "
            "everyone; the rest appear only for the clinical groups they are meaningful to, "
            "which is why their presence rates are low. A low rate here means *not applicable "
            "to this patient*, not missing data.",
            "",
            weekly_rows_md(wk["signals"], WEEKLY_SIGNALS),
            "### Discharge baseline",
            "",
            "The `discharge_baseline` sub-document. Week 0 only. These are the reference "
            "values every later week is compared against — a 2 kg gain means 2 kg above "
            "`dry_weight_kg`.",
            "",
            weekly_rows_md(wk["baseline"], WEEKLY_BASELINE),
        ]

    return "\n".join(out).rstrip() + "\n"


if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    data = gather()
    for path, doc in ((OUT, build(data)), (MD_OUT, build_markdown(data))):
        open(path, "w").write(doc)
        print(f"wrote {path}  ({len(doc)/1024:.0f} KB)")
