"""
features/clean.py
-----------------
Loads the raw Diabetes 130-US Hospitals CSV, handles all missing values,
and returns a cleaned pandas DataFrame ready for feature engineering.

Null-handling decisions (also documented in /docs/diabetic/feature_notes.md):
  - '?' in source CSV is the dataset's null marker -> replaced with NaN
  - Numeric columns  -> fillna(0)
  - Categorical columns -> fillna(column mode)
  - Any remaining NaN after the above -> forward-fill then back-fill
"""

import pandas as pd
from pathlib import Path

RAW_CSV = Path("data/diabetic/diabetic_data.csv")

# Columns to drop: IDs and columns not used as features or labels
DROP_COLS = [
    "encounter_id",
    "patient_nbr",
    "weight",           # >95% missing
    "payer_code",       # administrative, not clinical
    "medical_specialty", # high cardinality, not mapped to any feature
]


def load_and_clean(csv_path: Path = RAW_CSV) -> pd.DataFrame:
    """
    Load the raw CSV and return a cleaned DataFrame.

    Parameters
    ----------
    csv_path : Path
        Path to diabetic_data.csv

    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame with '?' replaced, nulls handled,
        and unused columns removed.
    """
    df = pd.read_csv(csv_path, low_memory=False)
    print(f"[clean] Loaded  : {df.shape[0]:,} rows x {df.shape[1]} columns")

    # 1. Replace dataset null marker
    df.replace("?", pd.NA, inplace=True)

    # 2. Drop unused columns (ignore missing cols in case CSV varies)
    cols_to_drop = [c for c in DROP_COLS if c in df.columns]
    df.drop(columns=cols_to_drop, inplace=True)
    print(f"[clean] Dropped  : {cols_to_drop}")

    # 3. Separate numeric vs categorical columns
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    categorical_cols = df.select_dtypes(exclude=["number"]).columns.tolist()

    # 4. Fill numeric nulls with 0
    df[numeric_cols] = df[numeric_cols].fillna(0)

    # 5. Fill categorical nulls with column mode
    for col in categorical_cols:
        mode_val = df[col].mode(dropna=True)
        if not mode_val.empty:
            df[col] = df[col].fillna(mode_val[0])

    # 6. Safety net: forward-fill then back-fill any stragglers
    df = df.ffill().bfill()

    null_count = df.isnull().sum().sum()
    print(f"[clean] Null cells remaining : {null_count}")
    print(f"[clean] Final shape          : {df.shape}")

    return df


if __name__ == "__main__":
    df = load_and_clean()
    print(df.dtypes)
    print(df.head(3))