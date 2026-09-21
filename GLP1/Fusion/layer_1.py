"""
GLP-1 Analytics Platform — Fusion Layer 1 (v3)
Combines NHANES + MEPS to produce patient baseline with cost features.

FIXES FROM v2:
  Fix A — Fusion script was overwriting the 'molecule' column that MEPS
           script had already correctly saved. The brand-name remapping
           logic in Step 6 replaced clean generic-name data with nulls.
           Now reads 'molecule' directly from the MEPS CSV without remapping.

  Fix B — Row count still below 5000 because eligibility filter only used
           BMI and HbA1c. Added third pathway: confirmed diabetes diagnosis
           (DIQ010 == 1) makes a patient eligible regardless of BMI/HbA1c.
           This recovers patients who are on GLP-1s for T2D management
           even if their BMI or HbA1c happen to be borderline.
"""

import pandas as pd
import numpy as np
import os

# ── CONFIG ────────────────────────────────────────────────────────────────────
NHANES_FILE = "NHANES/nhanes_clinical_baseline.csv"
MEPS_FILE   = "MEPS/meps_glp1_cost_analysis.csv"
OUTPUT_FILE = "FUSION_LAYER_1.csv"

MOLECULES = ['SEMAGLUTIDE', 'TIRZEPATIDE', 'DULAGLUTIDE', 'LIRAGLUTIDE']

HARD_FALLBACKS = {
    'SEMAGLUTIDE': 150.0,
    'TIRZEPATIDE': 200.0,
    'DULAGLUTIDE': 100.0,
    'LIRAGLUTIDE':  80.0,
}

AGE_BINS   = [0, 19, 29, 39, 49, 59, 69, 79, 100]
AGE_LABELS = ['0-19', '20-29', '30-39', '40-49', '50-59', '60-69', '70-79', '80+']

# ── STEP 1: LOAD ──────────────────────────────────────────────────────────────
print("=" * 60)
print("STEP 1 — Loading source files")
print("=" * 60)

nhanes = pd.read_csv(NHANES_FILE, low_memory=False)
meps   = pd.read_csv(MEPS_FILE,   low_memory=False)

print(f"  NHANES rows : {len(nhanes):,}")
print(f"  MEPS rows   : {len(meps):,}")

# Quick MEPS sanity check
print(f"\n  MEPS molecule column check:")
print(f"    Unique molecules : {meps['molecule'].unique()}")
print(f"    Null molecules   : {meps['molecule'].isna().sum()}")
print(f"    SEX unique vals  : {meps['SEX'].unique()}")

# ── STEP 2: EXPANDED ELIGIBILITY FILTER (Fix B) ───────────────────────────────
print("\n" + "=" * 60)
print("STEP 2 — Applying expanded GLP-1 eligibility filter")
print("=" * 60)

# Three eligibility pathways:
# 1. Obese (BMI >= 30) — standard obesity indication
# 2. Overweight + pre-diabetic (BMI >= 27 AND HbA1c >= 5.7)
# 3. Confirmed diabetes diagnosis (DIQ010 == 1) — T2D management regardless of BMI
before = len(nhanes)

pathway_1 = nhanes['BMXBMI'] >= 30
pathway_2 = (nhanes['BMXBMI'] >= 27) & (nhanes['LBXGH'] >= 5.7)
pathway_3 = nhanes['DIQ010'] == 1   # confirmed diabetes diagnosis

nhanes['is_glp1_candidate_v3'] = (pathway_1 | pathway_2 | pathway_3).astype(int)

master = nhanes[nhanes['is_glp1_candidate_v3'] == 1].copy()
after  = len(master)

print(f"  Pathway 1 (BMI >= 30)                    : {pathway_1.sum():,}")
print(f"  Pathway 2 (BMI >= 27 + HbA1c >= 5.7)    : {pathway_2.sum():,}")
print(f"  Pathway 3 (confirmed diabetes diagnosis) : {pathway_3.sum():,}")
print(f"  Total after union of all pathways        : {after:,}")
print(f"  Rows filtered out                        : {before - after:,}")

# ── STEP 3: GENDER ENCODING ───────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 3 — Gender encoding")
print("=" * 60)

master["gender_female"] = (master["RIAGENDR"] == 2).astype(int)
master["gender_int"]    = master["RIAGENDR"].fillna(0).astype(int)

print(f"  Male   (0): {(master['gender_female']==0).sum():,}")
print(f"  Female (1): {(master['gender_female']==1).sum():,}")

# ── STEP 4: AGE BINS ──────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 4 — Age bins")
print("=" * 60)

master["age_bin"] = pd.cut(master["RIDAGEYR"], bins=AGE_BINS, labels=AGE_LABELS)
meps["age_bin"]   = pd.cut(meps["AGELAST"],    bins=AGE_BINS, labels=AGE_LABELS)

print(f"  Master age distribution:\n{master['age_bin'].value_counts().sort_index().to_string()}")

# ── STEP 5: ASSIGN MOLECULES ──────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 5 — Assigning molecules")
print("=" * 60)

np.random.seed(42)
master["assigned_molecule"] = np.random.choice(MOLECULES, size=len(master))
print(f"  Distribution:\n{master['assigned_molecule'].value_counts().to_string()}")

# ── STEP 6: BUILD MEPS LOOKUP TABLES (Fix A) ──────────────────────────────────
print("\n" + "=" * 60)
print("STEP 6 — Building MEPS cost lookup tables")
print("=" * 60)

# FIX A: Read 'molecule' column directly from MEPS CSV.
# DO NOT remap or overwrite it — the MEPS script already saved it correctly
# with generic names (SEMAGLUTIDE, TIRZEPATIDE etc.) that match MOLECULES list.
# Previous version was re-running brand→molecule mapping here which
# replaced the correct generic-name data with nulls.

meps["SEX_int"] = meps["SEX"].fillna(0).astype(int)
meps_mapped = meps[meps["molecule"].notna()].copy()

print(f"  MEPS rows with valid molecule : {len(meps_mapped):,}")
print(f"  Molecule distribution in MEPS :\n{meps_mapped['molecule'].value_counts().to_string()}")

# Granular lookup: (age_bin, sex_int, molecule) → mean OOP
lookup_granular = (
    meps_mapped
    .groupby(["age_bin", "SEX_int", "molecule"])["out_of_pocket"]
    .mean()
    .to_dict()
)

# Drug-only lookup: molecule → mean OOP (fallback tier 2)
lookup_molecule = (
    meps_mapped
    .groupby("molecule")["out_of_pocket"]
    .mean()
    .to_dict()
)

print(f"\n  Molecule-level OOP costs from real MEPS data:")
for mol, cost in sorted(lookup_molecule.items()):
    print(f"    {mol:<15} ${cost:.2f}")

print(f"\n  Granular lookup entries (age+sex+molecule combos): {len(lookup_granular)}")

# ── STEP 7: ASSIGN OOP COST ───────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 7 — Assigning OOP costs (3-tier fallback)")
print("=" * 60)

def get_cost(row):
    # Tier 1: age_bin + gender + molecule
    key = (row["age_bin"], row["gender_int"], row["assigned_molecule"])
    cost = lookup_granular.get(key)
    if cost and not pd.isna(cost) and cost > 0:
        return round(float(cost), 2)
    # Tier 2: molecule average from real MEPS data
    cost = lookup_molecule.get(row["assigned_molecule"])
    if cost and not pd.isna(cost) and cost > 0:
        return round(float(cost), 2)
    # Tier 3: hardcoded industry fallback
    return HARD_FALLBACKS.get(row["assigned_molecule"], 100.0)

def get_tier(row):
    key = (row["age_bin"], row["gender_int"], row["assigned_molecule"])
    if lookup_granular.get(key):
        return "tier1_granular"
    elif lookup_molecule.get(row["assigned_molecule"]):
        return "tier2_molecule"
    return "tier3_hardcoded"

master["avg_oop_cost"]      = master.apply(get_cost, axis=1)
master["cost_lookup_tier"]  = master.apply(get_tier,  axis=1)

print(f"  Cost lookup tier distribution:")
print(master["cost_lookup_tier"].value_counts().to_string())
print(f"\n  OOP cost statistics:")
print(master["avg_oop_cost"].describe().round(2).to_string())

# ── STEP 8: INCOME-TO-COST PRESSURE RATIO ────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 8 — Income-to-cost pressure ratio")
print("=" * 60)

missing_pir = master["INDFMPIR"].isna().sum()
print(f"  Missing INDFMPIR : {missing_pir:,} ({missing_pir/len(master)*100:.1f}%)")

master["INDFMPIR"] = master.groupby(
    ["age_bin", "gender_female"]
)["INDFMPIR"].transform(lambda x: x.fillna(x.median()))
master["INDFMPIR"] = master["INDFMPIR"].fillna(master["INDFMPIR"].median())

master["income_cost_pressure"] = (
    master["avg_oop_cost"] / (master["INDFMPIR"] + 0.1)
).round(4)

cap = master["income_cost_pressure"].quantile(0.99)
master["income_cost_pressure"] = master["income_cost_pressure"].clip(upper=cap)

print(f"  income_cost_pressure (after 99th pct clip at {cap:.2f}):")
print(master["income_cost_pressure"].describe().round(3).to_string())

# ── STEP 9: CLEAN UP HELPER COLUMNS ──────────────────────────────────────────
master.drop(columns=["gender_int", "RIAGENDR", "is_glp1_candidate_v3"],
            inplace=True, errors="ignore")

# ── STEP 10: SAVE ─────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 10 — Saving")
print("=" * 60)

master.to_csv(OUTPUT_FILE, index=False)

print(f"  Rows saved : {len(master):,}")
print(f"  Columns    : {list(master.columns)}")
print(f"\n  Preview:")
preview_cols = ["RIDAGEYR", "gender_female", "BMXBMI", "LBXGH",
                "comorbidity_score", "assigned_molecule",
                "avg_oop_cost", "income_cost_pressure", "cost_lookup_tier"]
available = [c for c in preview_cols if c in master.columns]
print(master[available].head(10).to_string())

# ── VALIDATION ────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("VALIDATION REPORT")
print("=" * 60)

checks = {
    "Row count >= 5000"                      : len(master) >= 5000,
    "gender_female binary 0/1"               : master["gender_female"].isin([0,1]).all(),
    "RIAGENDR removed"                       : "RIAGENDR" not in master.columns,
    "avg_oop_cost no nulls"                  : master["avg_oop_cost"].isna().sum() == 0,
    "avg_oop_cost > 0"                       : (master["avg_oop_cost"] > 0).all(),
    "INDFMPIR no nulls"                      : master["INDFMPIR"].isna().sum() == 0,
    "income_cost_pressure no nulls"          : master["income_cost_pressure"].isna().sum() == 0,
    "income_cost_pressure > 0"               : (master["income_cost_pressure"] > 0).all(),
    "assigned_molecule no nulls"             : master["assigned_molecule"].isna().sum() == 0,
    "cost_lookup_tier not all hardcoded"     : (master["cost_lookup_tier"] != "tier3_hardcoded").any(),
    "comorbidity_score present"              : "comorbidity_score" in master.columns,
    "comorbidity_score values 0-3 only"      : master["comorbidity_score"].isin([0,1,2,3]).all()
                                               if "comorbidity_score" in master.columns else False,
}

all_passed = True
for check, result in checks.items():
    status = "✅ PASS" if result else "❌ FAIL"
    if not result:
        all_passed = False
    print(f"  {status}  {check}")

print()
if all_passed:
    print("  All checks passed. Ready for Layer 2.")
else:
    print("  Some checks failed. Review output above.")
    print("\n  NEXT STEP regardless: check 'cost_lookup_tier not all hardcoded'")
    print("  If that still fails, run this diagnostic:")
    print("    meps = pd.read_csv('MEPS/meps_glp1_cost_analysis.csv')")
    print("    print(meps[['molecule','out_of_pocket','AGELAST','SEX']].head(20))")