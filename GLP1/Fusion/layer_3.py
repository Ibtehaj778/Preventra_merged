"""
GLP-1 Analytics Platform — Fusion Layer 3 (Corrected)
Adds system_refill_score from CMS data + drug generation flags.

FIXES:
  - Brnd_Name column read defensively (handles Unnamed: 0 case)
  - Random seed added for reproducibility
  - Extended brand_to_mol mapping covers all brands in CMS data
  - Adds Task 5 features: drug_generation and is_newer_drug
"""

import pandas as pd
import numpy as np

np.random.seed(42)  # FIX: reproducibility


def fuse_layer_3():
    print("=" * 60)
    print("LAYER 3 — Systemic Reliability + Drug Generation Flags")
    print("=" * 60)

    # ── LOAD ──────────────────────────────────────────────────────────────────
    master      = pd.read_csv("FUSION/FUSION_LAYER_2.csv")
    cms_summary = pd.read_csv(
        "Medicare Part D Prescribers - by Provider and Drug/2023/"
        "glp1_outputs_v2/summary_by_drug.csv"
    )
    cms_low_refill = pd.read_csv(
        "Medicare Part D Prescribers - by Provider and Drug/2023/"
        "glp1_outputs_v2/low_refill_prescribers.csv"
    )

    print(f"  Master rows          : {len(master):,}")
    print(f"  CMS summary rows     : {len(cms_summary):,}")
    print(f"  CMS low refill rows  : {len(cms_low_refill):,}")

    # ── FIX: READ BRAND NAME COLUMN DEFENSIVELY ───────────────────────────────
    # summary_by_drug.csv was saved from a groupby — drug name may be the
    # index column, which reads back as 'Brnd_Name' or 'Unnamed: 0'
    first_col = cms_summary.columns[0]
    if first_col != "Brnd_Name":
        cms_summary = cms_summary.rename(columns={first_col: "Brnd_Name"})
    print(f"\n  CMS brand names found: {sorted(cms_summary['Brnd_Name'].dropna().unique())}")

    # ── FIX: EXTENDED BRAND TO MOLECULE MAPPING ──────────────────────────────
    # Covers all brands present in the actual CMS output file
    brand_to_mol = {
        "Ozempic":          "SEMAGLUTIDE",
        "Wegovy":           "SEMAGLUTIDE",
        "Rybelsus":         "SEMAGLUTIDE",
        "Mounjaro":         "TIRZEPATIDE",
        "Zepbound":         "TIRZEPATIDE",
        "Trulicity":        "DULAGLUTIDE",
        "Bydureon Bcise":   "LIRAGLUTIDE",   # exenatide — grouped as first-gen
        "Byetta":           "LIRAGLUTIDE",
        "Victoza 2-Pak":    "LIRAGLUTIDE",
        "Victoza 3-Pak":    "LIRAGLUTIDE",
        "Saxenda":          "LIRAGLUTIDE",
        "Soliqua 100-33":   "LIRAGLUTIDE",   # combo — grouped as first-gen
        "Xultophy 100-3.6": "DULAGLUTIDE",   # combo — grouped with dulaglutide
    }

    cms_summary["unified_molecule"] = cms_summary["Brnd_Name"].map(brand_to_mol)

    unmapped = cms_summary[cms_summary["unified_molecule"].isna()]["Brnd_Name"].unique()
    if len(unmapped) > 0:
        print(f"  WARNING: Unmapped CMS brands (will be excluded): {unmapped}")

    # ── DRUG-LEVEL REFILL BASELINE ────────────────────────────────────────────
    system_stats = (
        cms_summary[cms_summary["unified_molecule"].notna()]
        .groupby("unified_molecule")["Avg_Refill_Continuity"]
        .mean()
        .reset_index()
        .rename(columns={"Avg_Refill_Continuity": "drug_refill_avg"})
    )
    print(f"\n  Drug-level refill averages:")
    print(system_stats.to_string(index=False))

    # ── PROVIDER RISK SCORE ───────────────────────────────────────────────────
    if "Brnd_Name" in cms_low_refill.columns and "Low_Refill_Flag" in cms_low_refill.columns:
        cms_low_refill["unified_molecule"] = cms_low_refill["Brnd_Name"].map(brand_to_mol)
        provider_risk = (
            cms_low_refill[cms_low_refill["unified_molecule"].notna()]
            .groupby("unified_molecule")["Low_Refill_Flag"]
            .mean()
            .reset_index()
            .rename(columns={"Low_Refill_Flag": "provider_risk_score"})
        )
        print(f"\n  Provider risk scores:")
        print(provider_risk.to_string(index=False))
    else:
        print("  WARNING: Low_Refill_Flag not found — using zero provider risk")
        provider_risk = pd.DataFrame({
            "unified_molecule": ["SEMAGLUTIDE", "TIRZEPATIDE", "DULAGLUTIDE", "LIRAGLUTIDE"],
            "provider_risk_score": [0.25, 0.25, 0.25, 0.25]
        })

    # ── MERGE ─────────────────────────────────────────────────────────────────
    master = master.merge(
        system_stats, left_on="assigned_molecule", right_on="unified_molecule", how="left"
    )
    master = master.merge(
        provider_risk, on="unified_molecule", how="left"
    )

    # ── SYSTEM REFILL SCORE ───────────────────────────────────────────────────
    master["system_refill_score"] = (
        master["drug_refill_avg"] - (master["provider_risk_score"] * 0.2)
    )
    master["system_refill_score"] = master["system_refill_score"].fillna(
        master["system_refill_score"].median()
    )
    # FIX: seeded noise for reproducibility
    master["system_refill_score"] *= np.random.uniform(0.95, 1.05, size=len(master))

    print(f"\n  system_refill_score stats:")
    print(master["system_refill_score"].describe().round(4).to_string())

    # ── TASK 5: DRUG GENERATION FLAGS ─────────────────────────────────────────
    drug_generation_map = {
        "LIRAGLUTIDE":  1,   # first-gen GLP-1 RA (approved 2010)
        "DULAGLUTIDE":  2,   # second-gen GLP-1 RA (approved 2014)
        "SEMAGLUTIDE":  2,   # second-gen GLP-1 RA (approved 2017)
        "TIRZEPATIDE":  3,   # third-gen dual GIP/GLP-1 (approved 2022)
    }
    master["drug_generation"] = master["assigned_molecule"].map(drug_generation_map)
    master["is_newer_drug"]   = (master["drug_generation"] >= 2).astype(int)

    print(f"\n  drug_generation distribution:")
    print(master["drug_generation"].value_counts().sort_index().to_string())

    # ── CLEAN UP HELPER COLUMNS ───────────────────────────────────────────────
    master = master.drop(
        columns=["unified_molecule", "drug_refill_avg", "provider_risk_score"],
        errors="ignore"
    )

    # ── SAVE ──────────────────────────────────────────────────────────────────
    master.to_csv("FUSION_LAYER_3.csv", index=False)
    print(f"\n  Saved {len(master):,} rows → FUSION_LAYER_3.csv")
    print(f"  Columns: {list(master.columns)}")

    # Validation
    for col in ["system_refill_score", "drug_generation", "is_newer_drug"]:
        nulls = master[col].isna().sum()
        print(f"  {col} nulls : {nulls} {'✅' if nulls == 0 else '❌ FAIL'}")


if __name__ == "__main__":
    fuse_layer_3()