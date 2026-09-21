"""
features/label.py
-----------------
Engineers the binary readmission_30d label from the 'readmitted' column.

Label definition (also documented in /docs/diabetic/label_definition.md):
  '<30'  -> 1  (readmitted within 30 days — positive class)
  '>30'  -> 0  (readmitted after 30 days — negative)
  'NO'   -> 0  (not readmitted — negative)

Class balance: ~11% positive. This imbalance is handled in Week 3
via class_weight='balanced' in the DecisionTreeClassifier.
"""

import pandas as pd


def add_label(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add the binary 'label' column to the DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned DataFrame that still contains the 'readmitted' column.

    Returns
    -------
    pd.DataFrame
        Same DataFrame with a new integer 'label' column (0 or 1).
    """
    if "readmitted" not in df.columns:
        raise KeyError("Column 'readmitted' not found. Run clean.py first.")

    df["label"] = (df["readmitted"] == "<30").astype(int)

    counts = df["label"].value_counts(normalize=True)
    positive_rate = counts.get(1, 0.0)
    print(f"[label] Positive rate (readmitted <30d) : {positive_rate:.2%}")
    print(f"[label] Raw counts:\n{df['label'].value_counts()}")

    return df


def add_balanced_label(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add the binary 'label' column to the DataFrame.
    Categorizes readmitted > 30 days as a positive class as well.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned DataFrame that still contains the 'readmitted' column.

    Returns
    -------
    pd.DataFrame
        Same DataFrame with a new integer 'label' column (0 or 1).
    """
    if "readmitted" not in df.columns:
        raise KeyError("Column 'readmitted' not found. Run clean.py first.")

    df["label"] = df["readmitted"].isin(["<30", ">30"]).astype(int)

    counts = df["label"].value_counts(normalize=True)
    positive_rate = counts.get(1, 0.0)
    print(f"[label] Positive rate (readmitted <30d or >30d) : {positive_rate:.2%}")
    print(f"[label] Raw counts:\n{df['label'].value_counts()}")

    return df


def add_balanced_label_with_importance(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add the binary 'label' column to the DataFrame (all readmissions = 1).
    Creates a 'sample_weight' column evaluating >30 days readmission at 0.5 importance, 
    and all others at 1.0 importance.
    """
    if "readmitted" not in df.columns:
        raise KeyError("Column 'readmitted' not found. Run clean.py first.")

    df["label"] = df["readmitted"].isin(["<30", ">30"]).astype(int)
    
    weight_map = {
        "<30": 1.0,
        ">30": 0.5,
        "NO": 1.0
    }
    df["sample_weight"] = df["readmitted"].map(weight_map)

    counts = df["label"].value_counts(normalize=True)
    positive_rate = counts.get(1, 0.0)
    print(f"[label] Balanced+Importance positive rate: {positive_rate:.2%}")
    print(f"[label] Sample weight distribution:\n{df['sample_weight'].value_counts()}")

    return df


if __name__ == "__main__":
    from features.clean import load_and_clean

    df = load_and_clean()
    df = add_label(df)
    print(df["label"].value_counts(normalize=True))