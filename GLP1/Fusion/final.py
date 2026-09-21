"""
GLP-1 Analytics Platform — Final Behavioral Simulation (Corrected)
Produces FINAL_GLP1_MODEL_DATA.csv — the ML-ready training dataset.

FIXES:
  - RIAGENDR replaced with gender_female in final_cols (column was renamed in Layer 1)
  - Duplicate is_adherent assignment removed (lines 20-21 in original overwrote line 29)
  - final_cols expanded to include ALL improvement plan features:
    gender_female, income_cost_pressure, comorbidity_score,
    has_hypertension, has_dyslipidemia, has_dysglycemia,
    drug_generation, is_newer_drug
"""

import pandas as pd
import numpy as np

np.random.seed(42)


def generate_final_dataset():
    print("=" * 60)
    print("FINAL — Behavioral Simulation + Feature Assembly")
    print("=" * 60)

    # ── LOAD ──────────────────────────────────────────────────────────────────
    df = pd.read_csv("Fusion/FUSION_LAYER_3.csv")
    print(f"  Input rows    : {len(df):,}")
    print(f"  Input columns : {list(df.columns)}")

    # ── VERIFY ALL REQUIRED COLUMNS EXIST ────────────────────────────────────
    required = [
        "RIDAGEYR", "gender_female", "BMXBMI", "LBXGH",
        "assigned_molecule", "avg_oop_cost", "bio_friction",
        "system_refill_score", "income_cost_pressure",
        "comorbidity_score", "has_hypertension", "has_dyslipidemia",
        "has_dysglycemia", "drug_generation", "is_newer_drug",
    ]
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        print(f"\n  ❌ MISSING COLUMNS: {missing_cols}")
        print("  These features were supposed to be added in earlier layers.")
        print("  Check that Layer 1, 2, and 3 all ran with corrected scripts.")
        raise ValueError(f"Missing required columns: {missing_cols}")
    else:
        print(f"\n  ✅ All required columns present")

    # ── NORMALIZE FEATURES (0–1 scale for equation stability) ────────────────
    def normalize(col):
        col_min, col_max = col.min(), col.max()
        if col_max == col_min:
            return pd.Series(0.5, index=col.index)
        return (col - col_min) / (col_max - col_min)

    cost_factor       = normalize(df["avg_oop_cost"])
    bio_factor        = normalize(df["bio_friction"])
    system_factor     = normalize(df["system_refill_score"])
    pressure_factor   = normalize(df["income_cost_pressure"])   # new
    comorbid_factor   = normalize(df["comorbidity_score"])      # new — cuts both ways
    newer_drug_factor = df["is_newer_drug"].astype(float)       # new — 0 or 1

    # Motivation: higher BMI and higher HbA1c = more clinical urgency to stay on drug
    motivation_factor = (
        normalize(df["BMXBMI"]) * 0.5 +
        normalize(df["LBXGH"])  * 0.5
    )

    # ── BEHAVIORAL EQUATION ───────────────────────────────────────────────────
    # Base adherence probability = 65%
    # Subtract frictions, add motivation and system support
    #
    # income_cost_pressure replaces raw avg_oop_cost as the cost signal
    # because it is personally calibrated (cost / income ratio)
    #
    # comorbidity_score has a small positive effect — sicker patients have
    # more clinical urgency to stay on therapy despite higher friction
    #
    # is_newer_drug has a small negative effect — newer drugs face more
    # prior authorization barriers and patient uncertainty
    base_prob = 0.65

    p_adherent = (
        base_prob
        - (pressure_factor   * 0.40)   # financial pressure (income-adjusted cost)
        - (bio_factor        * 0.30)   # side effect friction
        - (newer_drug_factor * 0.05)   # PA/access friction for newer drugs
        + (system_factor     * 0.10)   # provider/system reliability
        + (motivation_factor * 0.15)   # clinical urgency (BMI + HbA1c)
        + (comorbid_factor   * 0.05)   # disease severity motivation
    )

    # ── ADD STOCHASTIC NOISE (human randomness) ───────────────────────────────
    # Some patients with high cost still stay. Some with low cost still quit.
    noise      = np.random.normal(0, 0.10, size=len(df))
    final_prob = p_adherent + noise

    # ── FIX: SINGLE is_adherent ASSIGNMENT (original had two, second overwrote first)
    df["is_adherent"] = (final_prob > 0.5).astype(int)

    adherence_rate = df["is_adherent"].mean()
    print(f"\n  Simulated adherence rate : {adherence_rate:.1%}")
    print(f"  Dropout rate             : {1 - adherence_rate:.1%}")

    # Validate class balance — we want roughly 35–65% in either class
    if adherence_rate < 0.30 or adherence_rate > 0.75:
        print(f"  ⚠️  WARNING: Class imbalance detected ({adherence_rate:.1%} adherent)")
        print("  Consider adjusting base_prob or weights in the behavioral equation")
    else:
        print(f"  ✅ Class balance acceptable for ML training")

    # ── FINAL COLUMN SELECTION ────────────────────────────────────────────────
    # FIX: includes gender_female (not RIAGENDR) and all improvement plan features
    final_cols = [
        # Core clinical features
        "RIDAGEYR",
        "gender_female",          # FIX: was RIAGENDR in original
        "BMXBMI",
        "LBXGH",
        # Drug assignment
        "assigned_molecule",
        "drug_generation",        # NEW: improvement plan Task 5
        "is_newer_drug",          # NEW: improvement plan Task 5
        # Economic features
        "avg_oop_cost",
        "income_cost_pressure",   # NEW: improvement plan Task 3
        # Biological friction
        "bio_friction",
        # System reliability
        "system_refill_score",
        # Comorbidity features
        "comorbidity_score",      # NEW: improvement plan Task 4
        "has_hypertension",       # NEW: improvement plan Task 4
        "has_dyslipidemia",       # NEW: improvement plan Task 4
        "has_dysglycemia",        # NEW: improvement plan Task 4
        # Target variable
        "is_adherent",
    ]

    # Only keep columns that actually exist (graceful handling)
    available_cols = [c for c in final_cols if c in df.columns]
    missing_final  = [c for c in final_cols if c not in df.columns]
    if missing_final:
        print(f"\n  ⚠️  Some final columns not found and skipped: {missing_final}")

    df_final = df[available_cols].copy()

    # ── FINAL VALIDATION ──────────────────────────────────────────────────────
    print(f"\n  Final dataset shape : {df_final.shape}")
    print(f"  Columns ({len(available_cols)}): {available_cols}")

    total_nulls = df_final.isnull().sum().sum()
    print(f"\n  Total null values   : {total_nulls} {'✅' if total_nulls == 0 else '⚠️  has nulls'}")

    print(f"\n  is_adherent distribution:")
    print(df_final["is_adherent"].value_counts().to_string())

    print(f"\n  Sample rows:")
    print(df_final.head(5).to_string())

    # ── SAVE ──────────────────────────────────────────────────────────────────
    df_final.to_csv("FINAL_GLP1_MODEL_DATA.csv", index=False)
    print(f"\n  ✅ Saved {len(df_final):,} rows → FINAL_GLP1_MODEL_DATA.csv")
    print(f"\n  NEXT STEP: Run the ML modeling pipeline (Week 2)")
    print(f"  Features ready for SHAP explainability: {len(available_cols) - 1}")

    return df_final


if __name__ == "__main__":
    generate_final_dataset()