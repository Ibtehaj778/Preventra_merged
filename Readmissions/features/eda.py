"""
features/eda.py
---------------
Runs Exploratory Data Analysis (EDA) on the final features DataFrame and
writes a markdown summary to docs/eda_summary.md.

Checks performed:
  1. Class balance (positive label rate)
  2. Per-feature distribution stats (mean, std, min, max)
  3. Missing value rates per column
  4. Pairwise correlation matrix
  5. Flags:
       - Features with > 30% missing values
       - Feature pairs with pairwise correlation > 0.85

Run after build_features.py has produced data/diabetic/features.csv:
  python -m features.eda
"""

import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

FEATURES_CSV  = Path("data/diabetic/features.csv")
EDA_OUTPUT_MD = Path("docs/eda_summary.md")

MISSING_FLAG_THRESHOLD = 0.30   # flag if > 30% missing
CORR_FLAG_THRESHOLD    = 0.85   # flag if pairwise corr > 0.85


def run_eda(
    features_path: Path = FEATURES_CSV,
    output_path: Path = EDA_OUTPUT_MD,
) -> None:
    """Load features CSV, compute EDA stats, and write markdown report."""

    df = pd.read_csv(features_path)
    feature_cols = [c for c in df.columns if c != "label"]

    lines: list[str] = []

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------
    lines += [
        "# NeuroShield — EDA Summary (Week 2)",
        "",
        f"**Dataset:** `{features_path}`  ",
        f"**Rows:** {len(df):,}  ",
        f"**Feature columns:** {len(feature_cols)}  ",
        "",
    ]

    # ------------------------------------------------------------------
    # 1. Class balance
    # ------------------------------------------------------------------
    pos_rate = df["label"].mean()
    pos_count = df["label"].sum()
    neg_count = len(df) - pos_count

    lines += [
        "## 1. Class Balance",
        "",
        f"| Class | Count | Rate |",
        f"|-------|-------|------|",
        f"| Positive (readmitted <30d) | {pos_count:,} | {pos_rate:.2%} |",
        f"| Negative | {neg_count:,} | {1 - pos_rate:.2%} |",
        "",
        (
            "> Class imbalance (~11% positive) must be addressed in Week 3 "
            "via `class_weight='balanced'` in DecisionTreeClassifier."
        ),
        "",
    ]

    # ------------------------------------------------------------------
    # 2. Feature distribution stats
    # ------------------------------------------------------------------
    desc = df[feature_cols].describe().T[["mean", "std", "min", "max"]]
    desc = desc.round(3)

    lines += [
        "## 2. Feature Distribution Statistics",
        "",
        "| Feature | Mean | Std | Min | Max |",
        "|---------|------|-----|-----|-----|",
    ]
    for feat, row in desc.iterrows():
        lines.append(
            f"| {feat} | {row['mean']} | {row['std']} | {row['min']} | {row['max']} |"
        )
    lines.append("")

    # ------------------------------------------------------------------
    # 3. Missing value rates
    # ------------------------------------------------------------------
    missing_rates = df[feature_cols].isnull().mean().sort_values(ascending=False)
    flagged_missing = missing_rates[missing_rates > MISSING_FLAG_THRESHOLD]

    lines += [
        "## 3. Missing Value Rates",
        "",
        "| Feature | Missing Rate | Flagged |",
        "|---------|-------------|---------|",
    ]
    for feat, rate in missing_rates.items():
        flag = "YES — review before Week 3" if rate > MISSING_FLAG_THRESHOLD else ""
        lines.append(f"| {feat} | {rate:.2%} | {flag} |")
    lines.append("")

    if flagged_missing.empty:
        lines.append("> All features have < 30% missing values. No action required.")
    else:
        lines.append(f"> **{len(flagged_missing)} feature(s) flagged** for high missing rate.")
    lines.append("")

    # ------------------------------------------------------------------
    # 4. Pairwise correlation
    # ------------------------------------------------------------------
    corr = df[feature_cols].corr().round(3)

    lines += [
        "## 4. Pairwise Correlation Matrix",
        "",
        "| Feature A | Feature B | Correlation | Flagged |",
        "|-----------|-----------|-------------|---------|",
    ]

    flagged_pairs = []
    seen = set()
    for i, col_a in enumerate(feature_cols):
        for col_b in feature_cols[i + 1:]:
            pair_key = tuple(sorted([col_a, col_b]))
            if pair_key in seen:
                continue
            seen.add(pair_key)
            val = corr.loc[col_a, col_b]
            flag = ""
            if abs(val) > CORR_FLAG_THRESHOLD:
                flag = "YES — potential redundancy"
                flagged_pairs.append((col_a, col_b, val))
            lines.append(f"| {col_a} | {col_b} | {val} | {flag} |")
    lines.append("")

    if flagged_pairs:
        lines.append(f"> **{len(flagged_pairs)} pair(s) flagged** for high correlation (>{CORR_FLAG_THRESHOLD}):")
        for a, b, v in flagged_pairs:
            lines.append(f">  - `{a}` vs `{b}`: {v:.3f}")
    else:
        lines.append("> No feature pairs exceed the 0.85 correlation threshold.")
    lines.append("")

    # ------------------------------------------------------------------
    # 5. Summary verdict
    # ------------------------------------------------------------------
    lines += [
        "## 5. Summary",
        "",
        f"- Row count: {len(df):,}",
        f"- Positive label rate: {pos_rate:.2%}",
        f"- Null cells in features_df: {df[feature_cols].isnull().sum().sum()}",
        f"- Features flagged for missing data: {len(flagged_missing)}",
        f"- Feature pairs flagged for high correlation: {len(flagged_pairs)}",
        "",
        "**Week 2 exit criteria status:**",
        f"- Zero nulls: {'PASS' if df.isnull().sum().sum() == 0 else 'FAIL'}",
        f"- Positive rate ~11%: {'PASS' if 0.09 <= pos_rate <= 0.14 else 'FAIL'}",
        "",
    ]

    # ------------------------------------------------------------------
    # Write output
    # ------------------------------------------------------------------
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[eda] Report written -> {output_path}")

    # Also print a quick console summary
    print(f"\n  Rows              : {len(df):,}")
    print(f"  Positive rate     : {pos_rate:.2%}")
    print(f"  Null cells        : {df.isnull().sum().sum()}")
    print(f"  Missing flagged   : {len(flagged_missing)}")
    print(f"  Corr pairs flagged: {len(flagged_pairs)}")


if __name__ == "__main__":
    run_eda()