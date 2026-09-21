"""
GLP-1 Analytics Platform — Fusion Layer 2 (Corrected)
Adds bio_friction from FAERS + ClinicalTrials to master dataset.

FIXES:
  - FAERS folder typo: FARES -> FAERS
  - drop(columns=...) uses errors='ignore' to prevent crash on missing cols
"""

import pandas as pd
import numpy as np


def fuse_layer_2():
    print("=" * 60)
    print("LAYER 2 — Biological Friction Fusion")
    print("=" * 60)

    # ── LOAD ──────────────────────────────────────────────────────────────────
    master     = pd.read_csv("FUSION/FUSION_LAYER_1.csv")
    faers      = pd.read_csv("FAERS/faers_glp1_side_effects.csv")      # FIX: was FARES
    ct_adverse = pd.read_csv("ClinicalTrials/trial_adverse_events.csv")

    print(f"  Master rows     : {len(master):,}")
    print(f"  FAERS rows      : {len(faers):,}")
    print(f"  CT adverse rows : {len(ct_adverse):,}")

    # ── FAERS: REAL WORLD RISK ────────────────────────────────────────────────
    faers["drug"] = faers["drug"].str.upper().str.strip()
    faers_risk = faers.groupby("drug")["frequency"].sum().reset_index()
    faers_risk["real_world_risk"] = (
        faers_risk["frequency"] / faers_risk["frequency"].max()
    )
    print(f"\n  FAERS drug-level risk scores:")
    print(faers_risk.to_string(index=False))

    # ── CLINICAL TRIALS: GI ADVERSE EVENT RATE ───────────────────────────────
    gi_terms = ["Nausea", "Vomiting", "Diarrhea", "Gastrointestinal"]
    ct_gi = ct_adverse[
        ct_adverse["ae_term"].str.contains("|".join(gi_terms), case=False, na=False)
    ].copy()

    ct_gi["ae_rate"] = ct_gi["num_events"] / ct_gi["num_at_risk"]

    def get_series(name):
        for series in ["STEP", "SUSTAIN", "SURMOUNT", "AWARD", "LEAD"]:
            if series in str(name).upper():
                return series
        return "OTHER"

    ct_gi["series"] = ct_gi["trial_name"].apply(get_series)

    series_to_mol = {
        "STEP":     "SEMAGLUTIDE",
        "SUSTAIN":  "SEMAGLUTIDE",
        "SURMOUNT": "TIRZEPATIDE",
        "AWARD":    "DULAGLUTIDE",
        "LEAD":     "LIRAGLUTIDE",
    }

    # Aggregate to molecule level to prevent fan-out on merge
    ct_gi["unified_molecule"] = ct_gi["series"].map(series_to_mol)
    trial_stats = (
        ct_gi[ct_gi["unified_molecule"].notna()]
        .groupby("unified_molecule")["ae_rate"]
        .mean()
        .reset_index()
    )
    print(f"\n  Trial GI adverse event rates by molecule:")
    print(trial_stats.to_string(index=False))

    # ── MERGE ─────────────────────────────────────────────────────────────────
    master = master.merge(
        faers_risk[["drug", "real_world_risk"]],
        left_on="assigned_molecule", right_on="drug", how="left"
    )
    master = master.merge(
        trial_stats[["unified_molecule", "ae_rate"]],
        left_on="assigned_molecule", right_on="unified_molecule", how="left"
    )

    # ── BIO FRICTION ──────────────────────────────────────────────────────────
    master["bio_friction"] = (master["real_world_risk"] + master["ae_rate"]) / 2
    median_friction = master["bio_friction"].median()
    master["bio_friction"] = master["bio_friction"].fillna(median_friction)

    print(f"\n  bio_friction stats:")
    print(master["bio_friction"].describe().round(4).to_string())
    print(f"\n  bio_friction by molecule:")
    print(master.groupby("assigned_molecule")["bio_friction"].mean().round(4).to_string())

    # FIX: errors='ignore' prevents crash if columns already dropped
    master = master.drop(
        columns=["drug", "unified_molecule"], errors="ignore"
    )

    # ── SAVE ──────────────────────────────────────────────────────────────────
    master.to_csv("FUSION_LAYER_2.csv", index=False)
    print(f"\n  Saved {len(master):,} rows → FUSION_LAYER_2.csv")
    print(f"  Columns: {list(master.columns)}")

    # Validation
    nulls = master["bio_friction"].isna().sum()
    print(f"\n  bio_friction nulls : {nulls} {'✅' if nulls == 0 else '❌ FAIL'}")


if __name__ == "__main__":
    fuse_layer_2()