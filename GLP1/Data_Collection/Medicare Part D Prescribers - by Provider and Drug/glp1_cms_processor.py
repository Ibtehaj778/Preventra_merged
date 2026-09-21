"""
GLP-1 Analytics Platform — Phase 1 Data Processing (v2)
CMS Medicare Part D Prescribers by Provider and Drug (2023)
File: MUP_DPR_RY25_P04_V10_DY23_NPIBN.csv

CHANGES FROM v1:
  Fix 1 — Refill continuity threshold is now percentile-based (bottom 25th per drug)
           instead of a fixed < 0.8 cutoff (which caught nothing due to CMS bottom-coding)
  Fix 2 — Suppressed beneficiary counts (CMS hides values < 11) are now handled cleanly
           so they don't corrupt cost and therapy duration averages

Run this script in the same folder as the CSV file.
Requirements: pip install pandas openpyxl
"""

import pandas as pd
import os

# ── CONFIG ───────────────────────────────────────────────────────────────────
CSV_FILE   = "MUP_DPR_RY25_P04_V10_DY23_NPIBN.csv"
OUTPUT_DIR = "glp1_outputs_v2"
os.makedirs(OUTPUT_DIR, exist_ok=True)

GLP1_BRANDS = [
    "OZEMPIC", "WEGOVY", "RYBELSUS",
    "MOUNJARO", "ZEPBOUND",
    "VICTOZA", "SAXENDA",
    "TRULICITY",
    "BYDUREON", "BYETTA",
    "ADLYXIN",
]

GLP1_GENERICS = [
    "SEMAGLUTIDE", "TIRZEPATIDE",
    "LIRAGLUTIDE", "DULAGLUTIDE",
    "EXENATIDE",   "LIXISENATIDE",
]

# ── STEP 1: LOAD ─────────────────────────────────────────────────────────────
print("=" * 60)
print("STEP 1 — Loading CSV")
print("=" * 60)
df = pd.read_csv(
    CSV_FILE,
    dtype={"Prscrbr_NPI": str, "Prscrbr_State_FIPS": str,
           "GE65_Sprsn_Flag": str, "GE65_Bene_Sprsn_Flag": str},
    low_memory=False,
)
print(f"  Total rows loaded : {len(df):,}")
print(f"  Columns           : {list(df.columns)}\n")

# ── STEP 2: FILTER FOR GLP-1 DRUGS ──────────────────────────────────────────
print("=" * 60)
print("STEP 2 — Filtering GLP-1 drugs")
print("=" * 60)
brand_mask   = df["Brnd_Name"].str.upper().isin(GLP1_BRANDS)
generic_mask = df["Gnrc_Name"].str.upper().str.contains(
    "|".join(GLP1_GENERICS), na=False
)
glp1 = df[brand_mask | generic_mask].copy()
print(f"  GLP-1 rows        : {len(glp1):,}")
print(f"  Drug brands found : {sorted(glp1['Brnd_Name'].unique())}\n")

# ── STEP 3: CLEAN NUMERICS ───────────────────────────────────────────────────
print("=" * 60)
print("STEP 3 — Cleaning numeric columns")
print("=" * 60)
numeric_cols = [
    "Tot_Clms", "Tot_30day_Fills", "Tot_Day_Suply", "Tot_Drug_Cst", "Tot_Benes",
    "GE65_Tot_Clms", "GE65_Tot_30day_Fills", "GE65_Tot_Drug_Cst",
    "GE65_Tot_Day_Suply", "GE65_Tot_Benes",
]
for col in numeric_cols:
    if col in glp1.columns:
        glp1[col] = pd.to_numeric(glp1[col], errors="coerce")

# ── FIX 2: FLAG SUPPRESSED BENEFICIARY ROWS ──────────────────────────────────
# CMS suppresses Tot_Benes when the count is < 11 to protect privacy.
# These rows are still valid for prescriber counts and cost signals,
# but must be excluded from any per-beneficiary average calculations.
glp1["Benes_Suppressed"] = glp1["Tot_Benes"].isna()

suppressed_count = glp1["Benes_Suppressed"].sum()
valid_count      = (~glp1["Benes_Suppressed"]).sum()
print(f"  Rows with valid beneficiary count   : {valid_count:,}")
print(f"  Rows with suppressed count (< 11)   : {suppressed_count:,}")
print(f"  Suppressed rows kept for cost/volume signals, excluded from per-bene averages\n")

# ── STEP 4: FEATURE ENGINEERING ─────────────────────────────────────────────
print("=" * 60)
print("STEP 4 — Engineering features")
print("=" * 60)

# Base features (all rows)
glp1["Refill_Continuity_Ratio"] = (
    glp1["Tot_30day_Fills"] / glp1["Tot_Clms"].replace(0, float("nan"))
).round(3)

# Per-beneficiary features — only on rows where Tot_Benes is not suppressed
glp1["Avg_Cost_Per_Bene"]   = None
glp1["Avg_Days_On_Therapy"] = None

valid_mask = ~glp1["Benes_Suppressed"]
glp1.loc[valid_mask, "Avg_Cost_Per_Bene"] = (
    glp1.loc[valid_mask, "Tot_Drug_Cst"] /
    glp1.loc[valid_mask, "Tot_Benes"]
).round(2)

glp1.loc[valid_mask, "Avg_Days_On_Therapy"] = (
    glp1.loc[valid_mask, "Tot_Day_Suply"] /
    glp1.loc[valid_mask, "Tot_Benes"]
).round(1)

glp1["Avg_Cost_Per_Bene"]   = pd.to_numeric(glp1["Avg_Cost_Per_Bene"],   errors="coerce")
glp1["Avg_Days_On_Therapy"] = pd.to_numeric(glp1["Avg_Days_On_Therapy"], errors="coerce")

# ── FIX 1: PERCENTILE-BASED LOW REFILL FLAG ──────────────────────────────────
# CMS bottom-codes all 30-day fills at 1.0, so a fixed < 0.8 threshold catches nothing.
# Instead we flag prescribers in the bottom 25th percentile of refill continuity
# WITHIN EACH DRUG — because each drug has its own prescribing patterns.
# These are the prescribers whose patients refill least relative to their peers.

p25_by_drug = (
    glp1.groupby("Brnd_Name")["Refill_Continuity_Ratio"]
    .transform(lambda x: x.quantile(0.25))
)
glp1["Drug_P25_Refill_Threshold"] = p25_by_drug.round(3)
glp1["Low_Refill_Flag"] = glp1["Refill_Continuity_Ratio"] <= glp1["Drug_P25_Refill_Threshold"]

# Show the thresholds we computed per drug
thresholds = (
    glp1.groupby("Brnd_Name")["Drug_P25_Refill_Threshold"]
    .first()
    .sort_values()
)
print("  Percentile-based low refill thresholds by drug (P25):")
for drug, thresh in thresholds.items():
    flagged = glp1[(glp1["Brnd_Name"] == drug) & glp1["Low_Refill_Flag"]].shape[0]
    print(f"    {drug:<25} threshold = {thresh:.3f}   flagged prescribers = {flagged:,}")

total_flagged = glp1["Low_Refill_Flag"].sum()
print(f"\n  Total low-refill prescriber-drug records flagged : {total_flagged:,}")
print(f"  Low refill flag rate                             : {glp1['Low_Refill_Flag'].mean()*100:.1f}%\n")

# ── STEP 5: SAVE CLEAN DATASET ───────────────────────────────────────────────
print("=" * 60)
print("STEP 5 — Saving clean dataset")
print("=" * 60)
clean_path = os.path.join(OUTPUT_DIR, "glp1_cms_clean_v2.csv")
glp1.to_csv(clean_path, index=False)
print(f"  Saved → {clean_path}  ({len(glp1):,} rows)\n")

# ── STEP 6: SUMMARY TABLES ──────────────────────────────────────────────────
print("=" * 60)
print("STEP 6 — Building summary tables")
print("=" * 60)

# A) Drug-level summary
drug_summary = (
    glp1.groupby("Brnd_Name")
    .agg(
        Prescribers              = ("Prscrbr_NPI",              "nunique"),
        Total_Beneficiaries      = ("Tot_Benes",                 "sum"),
        Suppressed_Bene_Rows     = ("Benes_Suppressed",          "sum"),
        Total_Claims             = ("Tot_Clms",                  "sum"),
        Total_30day_Fills        = ("Tot_30day_Fills",            "sum"),
        Total_Drug_Cost_USD      = ("Tot_Drug_Cst",               "sum"),
        Avg_Refill_Continuity    = ("Refill_Continuity_Ratio",   "mean"),
        P25_Refill_Threshold     = ("Drug_P25_Refill_Threshold",  "first"),
        Low_Refill_Prescribers   = ("Low_Refill_Flag",            "sum"),
        Avg_Cost_Per_Bene        = ("Avg_Cost_Per_Bene",          "mean"),
        Avg_Days_On_Therapy      = ("Avg_Days_On_Therapy",        "mean"),
    )
    .sort_values("Total_Beneficiaries", ascending=False)
    .round(2)
)
drug_sum_path = os.path.join(OUTPUT_DIR, "summary_by_drug.csv")
drug_summary.to_csv(drug_sum_path)
print("\n=== Drug-Level Summary ===")
print(drug_summary.to_string())
print(f"\n  Saved → {drug_sum_path}\n")

# B) State × Drug summary
state_summary = (
    glp1.groupby(["Prscrbr_State_Abrvtn", "Brnd_Name"])
    .agg(
        Prescribers            = ("Prscrbr_NPI",             "nunique"),
        Total_Beneficiaries    = ("Tot_Benes",                "sum"),
        Total_Drug_Cost_USD    = ("Tot_Drug_Cst",              "sum"),
        Avg_Refill_Continuity  = ("Refill_Continuity_Ratio",  "mean"),
        Low_Refill_Prescribers = ("Low_Refill_Flag",           "sum"),
        Avg_Cost_Per_Bene      = ("Avg_Cost_Per_Bene",         "mean"),
        Avg_Days_On_Therapy    = ("Avg_Days_On_Therapy",       "mean"),
    )
    .sort_values(["Prscrbr_State_Abrvtn", "Total_Beneficiaries"], ascending=[True, False])
    .round(2)
)
state_sum_path = os.path.join(OUTPUT_DIR, "summary_by_state_and_drug.csv")
state_summary.to_csv(state_sum_path)
print(f"  State × Drug summary saved → {state_sum_path}")

# C) Specialty summary
specialty_summary = (
    glp1.groupby("Prscrbr_Type")
    .agg(
        Prescribers            = ("Prscrbr_NPI",             "nunique"),
        Total_Beneficiaries    = ("Tot_Benes",                "sum"),
        Total_Drug_Cost_USD    = ("Tot_Drug_Cst",              "sum"),
        Avg_Refill_Continuity  = ("Refill_Continuity_Ratio",  "mean"),
        Low_Refill_Prescribers = ("Low_Refill_Flag",           "sum"),
        Avg_Cost_Per_Bene      = ("Avg_Cost_Per_Bene",         "mean"),
    )
    .sort_values("Total_Beneficiaries", ascending=False)
    .head(20)
    .round(2)
)
spec_sum_path = os.path.join(OUTPUT_DIR, "summary_by_specialty.csv")
specialty_summary.to_csv(spec_sum_path)
print(f"  Specialty summary saved    → {spec_sum_path}")

# D) Low refill prescribers — the dropout risk list
low_refill_cols = [
    "Prscrbr_NPI", "Prscrbr_Last_Org_Name", "Prscrbr_First_Name",
    "Prscrbr_City", "Prscrbr_State_Abrvtn", "Prscrbr_Type",
    "Brnd_Name", "Gnrc_Name",
    "Tot_Clms", "Tot_30day_Fills", "Tot_Benes",
    "Refill_Continuity_Ratio", "Drug_P25_Refill_Threshold",
    "Avg_Cost_Per_Bene", "Avg_Days_On_Therapy",
    "Benes_Suppressed", "Low_Refill_Flag",
]
low_refill = (
    glp1[glp1["Low_Refill_Flag"]][low_refill_cols]
    .sort_values(["Brnd_Name", "Refill_Continuity_Ratio"])
)
low_refill_path = os.path.join(OUTPUT_DIR, "low_refill_prescribers.csv")
low_refill.to_csv(low_refill_path, index=False)
print(f"  Low refill prescribers     → {low_refill_path}  ({len(low_refill):,} rows)")

# E) Top 10 states by total GLP-1 spend (quick executive insight)
top_states = (
    glp1.groupby("Prscrbr_State_Abrvtn")
    .agg(
        Total_Beneficiaries  = ("Tot_Benes",               "sum"),
        Total_Drug_Cost_USD  = ("Tot_Drug_Cst",             "sum"),
        Avg_Refill_Continuity= ("Refill_Continuity_Ratio", "mean"),
    )
    .sort_values("Total_Drug_Cost_USD", ascending=False)
    .head(10)
    .round(2)
)
print("\n  Top 10 States by GLP-1 Spend:")
print(top_states.to_string())

# ── STEP 7: FINAL REPORT ─────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("PHASE 1 v2 — CMS DATA PROCESSING COMPLETE")
print("=" * 60)
print(f"  Total GLP-1 prescriber-drug records  : {len(glp1):,}")
print(f"  Unique GLP-1 prescribers             : {glp1['Prscrbr_NPI'].nunique():,}")
print(f"  Unique drug brands                   : {glp1['Brnd_Name'].nunique()}")
print(f"  Total Medicare beneficiaries covered : {glp1['Tot_Benes'].sum():,.0f}")
print(f"  Total drug cost (USD)                : ${glp1['Tot_Drug_Cst'].sum():,.0f}")
print(f"  Rows with suppressed beneficiary cnt : {suppressed_count:,}")
print(f"  Avg refill continuity ratio          : {glp1['Refill_Continuity_Ratio'].mean():.3f}")
print(f"  Low refill prescribers flagged       : {total_flagged:,}  ({glp1['Low_Refill_Flag'].mean()*100:.1f}%)")
print()
print("Output files in /glp1_outputs_v2/:")
print("  glp1_cms_clean_v2.csv           — full filtered dataset with all features")
print("  summary_by_drug.csv             — drug-level aggregates with P25 thresholds")
print("  summary_by_state_and_drug.csv   — geographic breakdown")
print("  summary_by_specialty.csv        — prescriber specialty breakdown")
print("  low_refill_prescribers.csv      — bottom 25th percentile dropout risk list")
print()
print("NEXT STEP → Load NHANES files for patient demographics and clinical markers")
print("  Download from: https://wwwn.cdc.gov/nchs/nhanes/")
print("  Files needed : DEMO_L.XPT  BMX_L.XPT  GHB_L.XPT  DIQ_L.XPT")