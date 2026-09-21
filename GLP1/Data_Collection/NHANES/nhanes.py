"""
GLP-1 Analytics Platform — NHANES Multi-Cycle Clinical Baseline
Combines 2017-2018 (suffix _J) and 2021-2023 (suffix _L) NHANES cycles.

WHY TWO CYCLES:
  The August 2021-August 2023 cycle alone yields only ~3,400 eligible
  GLP-1 candidates after filtering — below the 5,000 minimum needed
  for reliable ML training. Combining with 2017-2018 is standard
  NHANES research practice. Both cycles use identical variable names,
  same SEQN structure, and compatible methodology. A 'cycle' column
  is added to prevent SEQN collisions between cycles.

FILES NEEDED (place all in same directory as this script):
  2021-2023 cycle (_L suffix):
    DEMO_L.XPT, BMX_L.XPT, GHB_L.XPT, DIQ_L.XPT, BPX_L.XPT, TCHOL_L.XPT
  2017-2018 cycle (_J suffix):
    DEMO_J.XPT, BMX_J.XPT, GHB_J.XPT, DIQ_J.XPT, BPX_J.XPT, TCHOL_J.XPT
"""

import pandas as pd
import os

OUTPUT_FILE = "nhanes_clinical_baseline.csv"

# ── CYCLE DEFINITIONS ─────────────────────────────────────────────────────────
CYCLES = {
    "2021-2023": {
        "demo":  "NHANES/DEMO_L.XPT",
        "bmx":   "NHANES/BMX_L.XPT",
        "ghb":   "NHANES/GHB_L.XPT",
        "diq":   "NHANES/DIQ_L.XPT",
        "bpx":   "NHANES/BPX_L.XPT",
        "tchol": "NHANES/TCHOL_L.XPT",
    },
    "2017-2018": {
        "demo":  "NHANES/DEMO_J.XPT",
        "bmx":   "NHANES/BMX_J.XPT",
        "ghb":   "NHANES/GHB_J.XPT",
        "diq":   "NHANES/DIQ_J.XPT",
        "bpx":   "NHANES/BPX_J.XPT",
        "tchol": "NHANES/TCHOL_J.XPT",
    },
}

# Columns to extract per component (same across all cycles)
DEMO_COLS  = ['SEQN', 'RIAGENDR', 'RIDAGEYR', 'RIDRETH3', 'INDFMPIR']
BMX_COLS   = ['SEQN', 'BMXBMI', 'BMXWT']
GHB_COLS   = ['SEQN', 'LBXGH']
DIQ_COLS   = ['SEQN', 'DIQ010', 'DIQ050']
BPX_COLS   = ['SEQN', 'BPXOSY1']
TCHOL_COLS = ['SEQN', 'LBXTC']


def load_cycle(cycle_name: str, file_map: dict) -> pd.DataFrame:
    """Load and merge all components for one NHANES cycle."""
    print(f"\n  --- Cycle: {cycle_name} ---")

    loaded = {}
    for key, fname in file_map.items():
        if os.path.exists(fname):
            loaded[key] = pd.read_sas(fname)
            print(f"    Loaded {fname:<20} {len(loaded[key]):,} rows")
        else:
            loaded[key] = None
            print(f"    MISSING: {fname} — component will be null")

    # Merge components
    df = loaded["demo"][DEMO_COLS].copy()
    df = df.merge(loaded["bmx"][BMX_COLS],   on="SEQN", how="left")
    df = df.merge(loaded["ghb"][GHB_COLS],   on="SEQN", how="left")
    df = df.merge(loaded["diq"][DIQ_COLS],   on="SEQN", how="left")

    if loaded["bpx"] is not None:
        available = [c for c in BPX_COLS if c in loaded["bpx"].columns]
        df = df.merge(loaded["bpx"][available], on="SEQN", how="left")
    else:
        df["BPXOSY1"] = float("nan")

    if loaded["tchol"] is not None:
        available = [c for c in TCHOL_COLS if c in loaded["tchol"].columns]
        df = df.merge(loaded["tchol"][available], on="SEQN", how="left")
    else:
        df["LBXTC"] = float("nan")

    # Tag cycle to avoid SEQN collisions when stacking
    df["cycle"] = cycle_name

    print(f"    Merged rows : {len(df):,}")
    return df


def process_nhanes():
    print("=" * 60)
    print("NHANES Multi-Cycle Clinical Baseline")
    print("=" * 60)

    # ── LOAD ALL CYCLES ───────────────────────────────────────────────────────
    cycle_frames = []
    for cycle_name, file_map in CYCLES.items():
        df_cycle = load_cycle(cycle_name, file_map)
        cycle_frames.append(df_cycle)

    df = pd.concat(cycle_frames, ignore_index=True)
    print(f"\n  Total rows after combining cycles : {len(df):,}")
    print(f"  Rows per cycle:")
    print(df["cycle"].value_counts().to_string())

    # ── RELAXED MISSING VALUE DROP ────────────────────────────────────────────
    # Only drop if BOTH BMI and HbA1c are missing (unclassifiable patient)
    before = len(df)
    df = df[df["BMXBMI"].notna() | df["LBXGH"].notna()].copy()
    print(f"\n  Dropped (both BMI+HbA1c missing) : {before - len(df):,}")
    print(f"  Rows retained                     : {len(df):,}")

    # ── FEATURE ENGINEERING ───────────────────────────────────────────────────
    print("\n  Engineering features...")

    # Eligibility flags
    df["is_obese"]               = (df["BMXBMI"] >= 30).astype(int)
    df["has_diabetes_diagnosis"] = (df["DIQ010"] == 1).astype(int)
    df["is_glp1_candidate"]      = (
        (df["BMXBMI"] >= 30) |
        ((df["BMXBMI"] >= 27) & (df["LBXGH"] >= 6.5))
    ).astype(int)
    df["is_glp1_candidate_relaxed"] = (
        (df["BMXBMI"] >= 27) |
        (df["LBXGH"] >= 5.7)  |
        (df["DIQ010"] == 1)
    ).astype(int)

    strict_count  = df["is_glp1_candidate"].sum()
    relaxed_count = df["is_glp1_candidate_relaxed"].sum()
    print(f"    Strict eligibility  : {strict_count:,}")
    print(f"    Relaxed eligibility : {relaxed_count:,}")

    # ── COMORBIDITY FLAGS ─────────────────────────────────────────────────────
    df["has_hypertension"] = (df["BPXOSY1"] >= 130).fillna(0).astype(int)
    df["has_dyslipidemia"] = (df["LBXTC"]   >= 200).fillna(0).astype(int)
    df["has_dysglycemia"]  = (df["LBXGH"]   >= 5.7).fillna(0).astype(int)

    df["comorbidity_score"] = (
        df["has_hypertension"] +
        df["has_dyslipidemia"] +
        df["has_dysglycemia"]
    )

    print(f"\n  Comorbidity score distribution:")
    print(df["comorbidity_score"].value_counts().sort_index().to_string())

    # ── MISSING VALUE SUMMARY ─────────────────────────────────────────────────
    print(f"\n  Missing rates for key columns:")
    for col in ["BMXBMI", "LBXGH", "INDFMPIR", "BPXOSY1", "LBXTC"]:
        pct = df[col].isna().mean() * 100
        print(f"    {col:<15} {pct:.1f}%")

    # ── SAVE ──────────────────────────────────────────────────────────────────
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\n  Saved {len(df):,} rows → {OUTPUT_FILE}")
    print(f"  Columns : {list(df.columns)}")

    # ── ELIGIBILITY PREVIEW ───────────────────────────────────────────────────
    eligible = df[df["is_glp1_candidate_relaxed"] == 1]
    print(f"\n  Eligible patients (relaxed) : {len(eligible):,}")
    print(f"  Expected fusion Layer 1 output after filter: ~{len(eligible):,} rows")
    print(f"  Target is >= 5,000 ✅" if len(eligible) >= 5000 else
          f"  Still below 5,000 — consider adding 2019-2020 cycle (DEMO_K.XPT etc.)")

    return df


if __name__ == "__main__":
    df_nhanes = process_nhanes()
    print("\nSample rows:")
    print(df_nhanes[["cycle", "RIDAGEYR", "RIAGENDR", "BMXBMI", "LBXGH",
                      "INDFMPIR", "comorbidity_score",
                      "is_glp1_candidate_relaxed"]].head(10).to_string())