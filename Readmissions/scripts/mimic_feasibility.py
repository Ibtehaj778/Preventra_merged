#!/usr/bin/env python3
"""
MIMIC-IV feasibility probe for Preventra Phase 1 (discharge-time risk) and
Phase 2 (weekly post-discharge trend).

Answers, with real numbers rather than assumptions:

  Phase 1  - Is the 30-day readmission label constructible, and what is its
             base rate once deaths/hospice/observation stays are excluded?
           - What fraction of admissions carry each modelling feature?
           - What is the ICD-9 vs ICD-10 split (their CCI mapping is ICD-9 only)?

  Phase 2  - Does the `omr` table contain post-discharge observations?
           - How long after discharge does the FIRST one land?
           - How many distinct monitoring weeks per patient fall inside a
             30/90-day window? (this is the question that decides Phase 2)

Usage
-----
    python scripts/mimic_feasibility.py --dir /path/to/mimic-iv/hosp

Works against the open demo or the full hosp module; reads .csv or .csv.gz.
Only loads the columns it needs, so the full dataset stays manageable.
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd

# Discharge dispositions that make a readmission impossible or non-comparable.
# Standard practice for readmission measures: a patient who died or went to
# hospice cannot be readmitted, so leaving them in deflates the rate.
TERMINAL_DISPOSITIONS = {"DIED", "HOSPICE"}

# CMS readmission measures generally exclude observation stays, which are not
# true inpatient admissions. Keeping them inflates the denominator.
OBSERVATION_TYPES = {
    "EU OBSERVATION",
    "OBSERVATION ADMIT",
    "AMBULATORY OBSERVATION",
    "DIRECT OBSERVATION",
}

READMIT_WINDOW_DAYS = 30
MONITORING_WINDOWS = (30, 90)


def _read(directory: str, name: str, **kwargs) -> pd.DataFrame:
    """Load a MIMIC table, tolerating .csv / .csv.gz and the demo's sample_ prefix."""
    for candidate in (f"{name}.csv", f"{name}.csv.gz", f"sample_{name}.csv"):
        path = os.path.join(directory, candidate)
        if os.path.exists(path):
            return pd.read_csv(path, **kwargs)
    raise FileNotFoundError(f"{name}.csv[.gz] not found in {directory}")


def _pct(n, d):
    return f"{(100.0 * n / d):5.1f}%" if d else "    n/a"


def _header(title):
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


# ---------------------------------------------------------------------------
# Phase 1
# ---------------------------------------------------------------------------

def phase1(directory: str) -> pd.DataFrame:
    _header("PHASE 1 - discharge-time readmission label")

    adm = _read(
        directory, "admissions",
        usecols=["subject_id", "hadm_id", "admittime", "dischtime",
                 "admission_type", "discharge_location", "insurance",
                 "edregtime", "hospital_expire_flag"],
        parse_dates=["admittime", "dischtime", "edregtime"],
    )

    total = len(adm)
    print(f"admissions                : {total:,}")
    print(f"distinct patients         : {adm.subject_id.nunique():,}")
    print(f"admissions per patient    : {total / max(adm.subject_id.nunique(), 1):.2f}")

    # --- build the label on the FULL admission sequence, then filter -------
    # Order matters: the "next" admission must be found before dropping rows,
    # otherwise a readmission that followed an excluded stay is lost.
    adm = adm.sort_values(["subject_id", "admittime"]).reset_index(drop=True)
    adm["next_admittime"] = adm.groupby("subject_id")["admittime"].shift(-1)
    adm["next_type"] = adm.groupby("subject_id")["admission_type"].shift(-1)
    adm["days_to_next"] = (adm.next_admittime - adm.dischtime).dt.total_seconds() / 86400

    # Index-stay exclusions
    died = adm.hospital_expire_flag.eq(1)
    terminal = adm.discharge_location.isin(TERMINAL_DISPOSITIONS)
    observation = adm.admission_type.isin(OBSERVATION_TYPES)

    eligible = adm[~(died | terminal | observation)].copy()

    print("\nindex-stay exclusions")
    print(f"  died in hospital        : {died.sum():,} ({_pct(died.sum(), total)})")
    print(f"  died/hospice at disch.  : {terminal.sum():,} ({_pct(terminal.sum(), total)})")
    print(f"  observation stays       : {observation.sum():,} ({_pct(observation.sum(), total)})")
    print(f"  -> eligible index stays : {len(eligible):,} ({_pct(len(eligible), total)})")

    # Numerator: an UNPLANNED readmission inside the window. Elective returns
    # are typically planned follow-up surgery, not a care failure.
    within = eligible.days_to_next.le(READMIT_WINDOW_DAYS) & eligible.days_to_next.ge(0)
    unplanned = ~eligible.next_type.eq("ELECTIVE")
    eligible["readmit_30d"] = (within & unplanned).astype(int)

    n_pos = int(eligible.readmit_30d.sum())
    print(f"\n{READMIT_WINDOW_DAYS}-day unplanned readmission rate : "
          f"{n_pos:,} / {len(eligible):,} = {_pct(n_pos, len(eligible))}")
    print(f"  (all-cause, incl. elective)     : "
          f"{_pct(int(within.sum()), len(eligible))}")

    if n_pos < 50:
        print("  !! too few positives here for model fitting - demo-sized data only")

    # --- feature coverage --------------------------------------------------
    print("\nfeature coverage on eligible index stays")
    los = (eligible.dischtime - eligible.admittime).dt.total_seconds() / 86400
    print(f"  length of stay          : {_pct(los.notna().sum(), len(eligible))}"
          f"   median {los.median():.1f} d")
    print(f"  ED visit (edregtime)    : {_pct(eligible.edregtime.notna().sum(), len(eligible))}")
    print(f"  insurance               : {_pct(eligible.insurance.notna().sum(), len(eligible))}")
    print(f"  discharge_location      : {_pct(eligible.discharge_location.notna().sum(), len(eligible))}")

    # DRG severity - a real severity proxy, but only on APR rows
    try:
        drg = _read(directory, "drgcodes", usecols=["hadm_id", "drg_type", "drg_severity"])
        apr = drg[drg.drg_type.eq("APR")]
        cov = eligible.hadm_id.isin(apr.hadm_id).sum()
        print(f"  APR-DRG severity        : {_pct(cov, len(eligible))}"
              f"   <- severity 1-4, better than ICD-only proxies")
    except FileNotFoundError:
        print("  APR-DRG severity        : drgcodes.csv not found")

    # ICD version split - decides whether the ICD-9 CCI mapping still works
    try:
        dx = _read(directory, "diagnoses_icd", usecols=["hadm_id", "icd_version"])
        split = dx.icd_version.value_counts(normalize=True)
        print(f"\nICD version split         : "
              f"ICD-9 {split.get(9, 0):.0%} / ICD-10 {split.get(10, 0):.0%}")
        if split.get(10, 0) > 0.05:
            print("  !! api/main.py _CCI_PATTERNS are ICD-9 regexes only.")
            print("     ICD-10 rows will silently score CCI = 0.")
            print("     Fix: add the Quan et al. (2005) ICD-10 Charlson mapping.")
    except FileNotFoundError:
        print("\nICD version split         : diagnoses_icd.csv not found")

    return eligible


# ---------------------------------------------------------------------------
# Phase 2
# ---------------------------------------------------------------------------

def phase2(directory: str, eligible: pd.DataFrame) -> None:
    _header("PHASE 2 - post-discharge weekly monitoring signal")

    try:
        omr = _read(directory, "omr",
                    usecols=["subject_id", "chartdate", "result_name", "result_value"],
                    parse_dates=["chartdate"])
    except FileNotFoundError:
        print("omr.csv not found - Phase 2 cannot be assessed")
        return

    print(f"omr rows                  : {len(omr):,}")
    print(f"distinct patients         : {omr.subject_id.nunique():,}")
    print(f"rows per patient (median) : "
          f"{omr.groupby('subject_id').size().median():.0f}  "
          f"over the patient's ENTIRE record")
    print("\nmeasurement types available:")
    for name, n in omr.result_name.value_counts().items():
        print(f"  {name:<24} {n:>8,}")

    # Join each eligible discharge to that patient's later omr readings.
    disch = eligible[["subject_id", "hadm_id", "dischtime"]].copy()
    j = disch.merge(omr, on="subject_id", how="inner")
    j = j[j.chartdate > j.dischtime]
    j["days_after"] = (j.chartdate - j.dischtime).dt.total_seconds() / 86400

    if j.empty:
        print("\nNo post-discharge omr readings found -> Phase 2 not supportable here.")
        return

    # Days until the FIRST post-discharge reading: the decisive number.
    first = j.groupby("hadm_id").days_after.min()
    print(f"\ndischarges with >=1 later omr reading : "
          f"{first.size:,} / {len(disch):,} ({_pct(first.size, len(disch))})")
    print("\ndays until FIRST post-discharge reading")
    for q in (10, 25, 50, 75, 90):
        print(f"  p{q:<3}                   : {np.percentile(first, q):8.0f} days")

    # Distinct monitoring weeks inside each window - the actual Phase 2 test.
    print("\ndistinct monitoring WEEKS with >=1 reading, per discharge")
    for w in MONITORING_WINDOWS:
        win = j[j.days_after <= w].copy()
        if win.empty:
            print(f"  within {w:>2}d            : no readings")
            continue
        win["week"] = (win.days_after // 7).astype(int)
        weeks = win.groupby("hadm_id").week.nunique()
        covered = weeks.reindex(disch.hadm_id.unique()).fillna(0)
        max_weeks = w // 7
        print(f"  within {w:>2}d ({max_weeks} possible): "
              f"median {covered.median():.0f}, mean {covered.mean():.2f}, max {int(covered.max())}"
              f"   | >=2 weeks: {_pct((covered >= 2).sum(), len(covered))}")

    print("\nVERDICT")
    win30 = j[j.days_after <= 30]
    share_30 = j.hadm_id.nunique() and (win30.hadm_id.nunique() / len(disch))
    if share_30 < 0.25:
        print("  omr is OPPORTUNISTIC clinic measurement, not scheduled monitoring.")
        print("  Weekly re-scoring inside 30 days is NOT supportable from MIMIC alone.")
        print("  -> Use irregular-interval trend (last-observation + gap feature),")
        print("     or source the weekly cadence from All of Us / your own product.")
    else:
        print("  Enough post-discharge density to attempt irregular weekly binning.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", required=True, help="MIMIC-IV hosp module directory")
    args = ap.parse_args()

    if not os.path.isdir(args.dir):
        sys.exit(f"not a directory: {args.dir}")

    print(f"MIMIC-IV feasibility probe\nsource: {args.dir}")
    eligible = phase1(args.dir)
    phase2(args.dir, eligible)
    print()


if __name__ == "__main__":
    main()
