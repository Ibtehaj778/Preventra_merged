"""
features/build_features.py
---------------------------
Orchestrates the full Week 2 pipeline:
  1. Load and clean raw CSV       (features/clean.py)
  2. Add binary label             (features/label.py)
  3. Compute CCI feature          (features/cci.py)
  4. Derive all remaining features(features/engineer.py)
  5. Validate: zero nulls, correct row count, ~11% positive label
  6. Save to data/diabetic/features.csv

Run this file directly to produce the features artifact:
  python -m features.build_features
"""

import sys
from pathlib import Path
import pandas as pd

# Add project root to path when running as script
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from features.clean import load_and_clean
from features.label import add_label
from features.cci import add_cci_feature
from features.engineer import run_feature_pipeline

LABEL_COL = "label"
OUTPUT_CSV = Path("data/diabetic/features.csv")
EXPECTED_ROWS = 101_766


def build_features(
    df: pd.DataFrame,
    output_path: Path = OUTPUT_CSV,
    expected_rows: int = EXPECTED_ROWS,
) -> pd.DataFrame:
    """
    Run the final steps of the feature engineering pipeline (drop source columns,
    validate, and save) on a pre-processed DataFrame.

    Also saves to output_path and prints a validation report.
    """
    # Drop source columns that have been transformed to avoid duplicates
    source_cols_to_drop = [
        "readmitted",
        "number_inpatient",
        "number_emergency",
        "num_medications",
        "time_in_hospital",
        "change",
        "admission_type_id",
        "insulin",
        "number_diagnoses",
        "diag_1",
        "diag_2",
        "diag_3",
        "age",
    ]
    # Drop only those that exist
    cols_present = [c for c in source_cols_to_drop if c in df.columns]
    if cols_present:
        df.drop(columns=cols_present, inplace=True)
        print(f"[build] Dropped source columns: {cols_present}")

    # Keep all engineered features (no filtering)
    features_df = df.copy()

    # --- Validation gate ---
    null_total = features_df.isnull().sum().sum()
    row_count  = len(features_df)
    pos_rate   = features_df[LABEL_COL].mean()

    print("\n" + "=" * 55)
    print("  WEEK 2 VERIFICATION GATE")
    print("=" * 55)
    _check("Zero null values",      null_total == 0,               f"{null_total} nulls found")
    _check("Row count ~101,766",    abs(row_count - expected_rows) < 500, f"{row_count:,} rows")
    _check("Positive rate ~11%",    0.09 <= pos_rate <= 0.14,      f"{pos_rate:.2%}")
    print("=" * 55)

    # --- Save ---
    output_path.parent.mkdir(parents=True, exist_ok=True)
    features_df.to_csv(output_path, index=False)
    print(f"\n[build] Saved -> {output_path}  ({len(features_df):,} rows x {len(features_df.columns)} cols)")

    return features_df


def _check(label: str, condition: bool, detail: str) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label:<35} {detail}")


if __name__ == "__main__":
    # Execute the full pipeline step by step
    df = load_and_clean()
    df = add_label(df)
    df = add_cci_feature(df)
    df = run_feature_pipeline(df)

    # Then call build_features for validation and saving
    features_df = build_features(df)
    print("\nSample output:")
    print(features_df.head(3).to_string())
    print(f"\nColumn dtypes:\n{features_df.dtypes}")