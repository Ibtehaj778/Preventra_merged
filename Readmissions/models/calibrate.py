"""
NeuroShield -- models/calibrate.py
Week 3: Calibration curve, risk band threshold derivation, model_card.md update.

Must be run AFTER models/train.py, which produces data/diabetic/test_scored.csv.

Usage:
    python models/calibrate.py

Outputs:
    docs/diabetic/calibration_curve.png       -- decile calibration plot
    docs/calibration_summary.csv     -- decile table
    docs/diabetic/band_thresholds.json        -- chosen threshold values (read by FastAPI)
    docs/diabetic/model_validation_report.md  -- filled validation report
    Console printout of final thresholds and guidance
"""

import os
import sys
import json
import logging
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")   # non-interactive backend -- no display required
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from sklearn.metrics import (
    roc_auc_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    roc_curve,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
# TEST_SCORED_CSV = "data/diabetic/test_scored.csv"
# DOCS_DIR = "docs"
# CALIBRATION_PNG = os.path.join(DOCS_DIR, "calibration_curve.png")
# CALIBRATION_CSV = os.path.join(DOCS_DIR, "calibration_summary.csv")
# THRESHOLDS_JSON = os.path.join(DOCS_DIR, "band_thresholds.json")
# VALIDATION_REPORT_MD = os.path.join(DOCS_DIR, "model_validation_report.md")
# ROC_CURVE_PNG = os.path.join(DOCS_DIR, "roc_curve.png")

# TEST_SCORED_CSV = "data/diabetic/test_scored_balanced.csv"
# DOCS_DIR = "docs"
# CALIBRATION_PNG = os.path.join(DOCS_DIR, "calibration_curve_balanced.png")
# CALIBRATION_CSV = os.path.join(DOCS_DIR, "calibration_summary_balanced.csv")
# THRESHOLDS_JSON = os.path.join(DOCS_DIR, "band_thresholds_balanced.json")
# VALIDATION_REPORT_MD = os.path.join(DOCS_DIR, "model_validation_report_balanced.md")
# ROC_CURVE_PNG = os.path.join(DOCS_DIR, "roc_curve.png")

# TEST_SCORED_CSV = "data/diabetic/test_scored_xgb.csv"
# DOCS_DIR = "docs"
# CALIBRATION_PNG = os.path.join(DOCS_DIR, "calibration_curve_xgb.png")
# CALIBRATION_CSV = os.path.join(DOCS_DIR, "calibration_summary_xgb.csv")
# THRESHOLDS_JSON = os.path.join(DOCS_DIR, "band_thresholds_xgb.json")
# VALIDATION_REPORT_MD = os.path.join(DOCS_DIR, "model_validation_report_xgb.md")
# ROC_CURVE_PNG = os.path.join(DOCS_DIR, "roc_curve.png")

TEST_SCORED_CSV = "data/diabetic/test_scored_balanced_importance.csv"
DOCS_DIR = "docs"
CALIBRATION_PNG = os.path.join(DOCS_DIR, "calibration_curve_balanced_importance.png")
CALIBRATION_CSV = os.path.join(DOCS_DIR, "calibration_summary_balanced_importance.csv")
THRESHOLDS_JSON = os.path.join(DOCS_DIR, "band_thresholds_balanced_importance.json")
VALIDATION_REPORT_MD = os.path.join(DOCS_DIR, "model_validation_report_balanced_importance.md")
ROC_CURVE_PNG = os.path.join(DOCS_DIR, "roc_curve.png")


# Number of deciles for calibration plot
N_DECILES = 10

# Risk band rules (project plan spec):
#   High  : observed rate >= 2x population average
#   Low   : observed rate <  1x population average
#   Medium: between Low and High
HIGH_MULTIPLIER = 2.0
LOW_MULTIPLIER = 1.0

# Fallback thresholds (probability, 0-1 scale) used if auto-detection fails
FALLBACK_HIGH_PROB = 0.22
FALLBACK_LOW_PROB = 0.11


# ---------------------------------------------------------------------------
# Load scored test set
# ---------------------------------------------------------------------------
def load_scored(path: str) -> pd.DataFrame:
    log.info(f"Loading scored test set from {path}")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} not found. Run models/train.py first."
        )
    df = pd.read_csv(path)
    if "predicted_prob_xgb" in df.columns:
        df = df.rename(columns={"predicted_prob_xgb": "predicted_prob", "risk_score_xgb": "risk_score"})
    required = {"predicted_prob", "risk_score", "label"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in {path}: {missing}")
    log.info(f"Loaded {len(df):,} scored test records")
    return df


# ---------------------------------------------------------------------------
# Population statistics
# ---------------------------------------------------------------------------
def population_stats(df: pd.DataFrame) -> dict:
    pop_avg = df["label"].mean()
    high_threshold_prob = pop_avg * HIGH_MULTIPLIER
    low_threshold_prob = pop_avg * LOW_MULTIPLIER

    stats = {
        "population_readmission_rate": round(pop_avg, 4),
        "high_multiplier": HIGH_MULTIPLIER,
        "low_multiplier": LOW_MULTIPLIER,
        "target_high_prob": round(high_threshold_prob, 4),
        "target_low_prob": round(low_threshold_prob, 4),
    }
    log.info(f"Population readmission rate: {pop_avg:.4f}")
    log.info(f"Target High threshold (prob): >= {high_threshold_prob:.4f}")
    log.info(f"Target Low threshold (prob):  <  {low_threshold_prob:.4f}")
    return stats


# ---------------------------------------------------------------------------
# Decile calibration analysis
# ---------------------------------------------------------------------------
def compute_decile_table(df: pd.DataFrame, n_deciles: int = N_DECILES) -> pd.DataFrame:
    """
    Split predicted_prob into n_deciles quantile buckets.
    Compute mean predicted probability and observed readmission rate per bucket.
    """
    df = df.copy()
    df["decile"] = pd.qcut(
        df["predicted_prob"],
        q=n_deciles,
        labels=False,
        duplicates="drop",
    )

    summary = (
        df.groupby("decile")
        .agg(
            decile_min=("predicted_prob", "min"),
            decile_max=("predicted_prob", "max"),
            avg_predicted_prob=("predicted_prob", "mean"),
            observed_readmission_rate=("label", "mean"),
            patient_count=("label", "count"),
            readmitted_count=("label", "sum"),
        )
        .reset_index()
    )
    summary["decile_label"] = summary["decile"] + 1   # 1-indexed for readability
    return summary


# ---------------------------------------------------------------------------
# Threshold derivation from decile table
# ---------------------------------------------------------------------------
def derive_thresholds(
    summary: pd.DataFrame,
    stats: dict,
) -> dict:
    """
    Walk decile table from highest to lowest risk.
    High threshold: lowest avg_predicted_prob where observed_rate >= HIGH_MULTIPLIER * pop_avg.
    Low threshold: highest avg_predicted_prob where observed_rate < LOW_MULTIPLIER * pop_avg.

    Falls back to pre-defined values if the data pattern does not yield clean crossings.
    """
    pop_avg = stats["population_readmission_rate"]
    high_target = pop_avg * HIGH_MULTIPLIER
    low_target = pop_avg * LOW_MULTIPLIER

    high_deciles = summary[summary["observed_readmission_rate"] >= high_target]
    low_deciles = summary[summary["observed_readmission_rate"] < low_target]

    if not high_deciles.empty:
        high_prob = high_deciles["decile_min"].min()
        log.info(f"Auto-derived High threshold probability: {high_prob:.4f}")
    else:
        high_prob = summary.iloc[-1]["decile_min"]
        log.warning(
            f"No decile reached {high_target:.4f} observed rate. "
            f"Using fallback High threshold (top decile min): {high_prob:.4f}"
        )

    if not low_deciles.empty:
        low_prob = low_deciles["decile_max"].max()
        log.info(f"Auto-derived Low threshold probability: {low_prob:.4f}")
    else:
        low_prob = summary.iloc[0]["decile_max"]
        log.warning(
            f"No decile stayed below {low_target:.4f} observed rate. "
            f"Using fallback Low threshold (bottom decile max): {low_prob:.4f}"
        )

    # Convert to 0-100 risk score scale
    high_score = round(high_prob * 100, 1)
    low_score = round(low_prob * 100, 1)

    # Guard: Low must be < High
    if low_score >= high_score:
        log.warning(
            f"Low threshold ({low_score}) >= High threshold ({high_score}). "
            "Applying fallback split based on percentiles (Low=D3, High=D8)."
        )
        low_prob = summary.iloc[2]["decile_max"]
        high_prob = summary.iloc[7]["decile_min"]
        low_score = round(low_prob * 100, 1)
        high_score = round(high_prob * 100, 1)

    thresholds = {
        "high_score_threshold": high_score,
        "low_score_threshold": low_score,
        "high_prob_threshold": round(high_prob, 4),
        "low_prob_threshold": round(low_prob, 4),
        "population_readmission_rate": pop_avg,
        "band_definitions": {
            "High": f"risk_score >= {high_score}",
            "Medium": f"{low_score} <= risk_score < {high_score}",
            "Low": f"risk_score < {low_score}",
        },
    }

    log.info(f"Final thresholds -> High: score >= {high_score} | Low: score < {low_score}")
    return thresholds


# ---------------------------------------------------------------------------
# Apply risk bands to scored DataFrame
# ---------------------------------------------------------------------------
def apply_risk_bands(df: pd.DataFrame, thresholds: dict) -> pd.DataFrame:
    high_t = thresholds["high_score_threshold"]
    low_t = thresholds["low_score_threshold"]

    conditions = [
        df["risk_score"] >= high_t,
        (df["risk_score"] >= low_t) & (df["risk_score"] < high_t),
        df["risk_score"] < low_t,
    ]
    choices = ["High", "Medium", "Low"]
    df = df.copy()
    df["risk_band"] = np.select(conditions, choices, default="Medium")

    band_counts = df["risk_band"].value_counts()
    log.info(f"Risk band distribution:\n{band_counts.to_string()}")
    return df


# ---------------------------------------------------------------------------
# Precision / Recall at High-risk threshold
# ---------------------------------------------------------------------------
def metrics_at_high_threshold(df: pd.DataFrame, thresholds: dict) -> dict:
    high_t = thresholds["high_prob_threshold"]
    y_true = df["label"].values
    y_pred_high = (df["predicted_prob"] >= high_t).astype(int)

    auc = roc_auc_score(y_true, df["predicted_prob"].values)
    precision = precision_score(y_true, y_pred_high, zero_division=0)
    recall = recall_score(y_true, y_pred_high, zero_division=0)
    f1 = f1_score(y_true, y_pred_high, zero_division=0)
    cm = confusion_matrix(y_true, y_pred_high).tolist()

    metrics = {
        "auc_roc": round(auc, 4),
        "precision_at_high_threshold": round(precision, 4),
        "recall_at_high_threshold": round(recall, 4),
        "f1_at_high_threshold": round(f1, 4),
        "confusion_matrix": cm,
    }

    log.info(f"AUC-ROC: {auc:.4f}")
    log.info(f"Precision at High threshold: {precision:.4f}")
    log.info(f"Recall at High threshold:    {recall:.4f}")
    log.info(f"F1 at High threshold:        {f1:.4f}")
    log.info(f"Confusion matrix:\n  TN={cm[0][0]}  FP={cm[0][1]}\n  FN={cm[1][0]}  TP={cm[1][1]}")
    return metrics


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------
def plot_calibration_curve(summary: pd.DataFrame, stats: dict, thresholds: dict, save_path: str):
    pop_avg = stats["population_readmission_rate"]
    high_target = pop_avg * HIGH_MULTIPLIER

    fig, ax = plt.subplots(figsize=(9, 6))
    fig.patch.set_facecolor("#0f1117")
    ax.set_facecolor("#0f1117")

    # Perfect calibration reference line
    ax.plot(
        [0, 1], [0, 1],
        linestyle="--", color="#555555", linewidth=1.2, label="Perfect calibration", zorder=1
    )

    # Decile calibration line
    ax.plot(
        summary["avg_predicted_prob"],
        summary["observed_readmission_rate"],
        marker="o", color="#00c4a1", linewidth=2, markersize=7,
        label="Observed vs predicted (decile)", zorder=3
    )

    # Scatter with decile index labels
    for _, row in summary.iterrows():
        ax.annotate(
            f"D{int(row['decile_label'])}",
            xy=(row["avg_predicted_prob"], row["observed_readmission_rate"]),
            xytext=(4, 4), textcoords="offset points",
            fontsize=7, color="#aaaaaa"
        )

    # Population average line
    ax.axhline(
        y=pop_avg, color="#f5a623", linestyle=":",
        linewidth=1.5, label=f"Population avg ({pop_avg:.3f})", zorder=2
    )

    # High threshold line
    ax.axhline(
        y=high_target, color="#e74c3c", linestyle=":",
        linewidth=1.5, label=f"High threshold target ({high_target:.3f})", zorder=2
    )

    # Threshold vertical lines on score/prob axis
    ax.axvline(
        x=thresholds["high_prob_threshold"], color="#e74c3c", linestyle="--",
        linewidth=1, alpha=0.6, label=f"High prob cutoff ({thresholds['high_prob_threshold']})"
    )
    ax.axvline(
        x=thresholds["low_prob_threshold"], color="#27ae60", linestyle="--",
        linewidth=1, alpha=0.6, label=f"Low prob cutoff ({thresholds['low_prob_threshold']})"
    )

    ax.set_xlabel("Mean Predicted Probability", color="#cccccc", fontsize=11)
    ax.set_ylabel("Observed Readmission Rate", color="#cccccc", fontsize=11)
    ax.set_title("NeuroShield -- Calibration Curve\n(Predicted Deciles vs Observed Rate)", color="#ffffff", fontsize=13)
    ax.tick_params(colors="#aaaaaa")
    for spine in ax.spines.values():
        spine.set_edgecolor("#333333")

    legend = ax.legend(fontsize=8, framealpha=0.3, facecolor="#1a1a2e", labelcolor="#cccccc")
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    log.info(f"Calibration curve saved to {save_path}")


def plot_roc_curve(df: pd.DataFrame, metrics: dict, save_path: str):
    fpr, tpr, _ = roc_curve(df["label"].values, df["predicted_prob"].values)
    auc = metrics["auc_roc"]

    fig, ax = plt.subplots(figsize=(7, 6))
    fig.patch.set_facecolor("#0f1117")
    ax.set_facecolor("#0f1117")

    ax.plot([0, 1], [0, 1], linestyle="--", color="#555555", linewidth=1.2, label="Random classifier")
    ax.plot(fpr, tpr, color="#00c4a1", linewidth=2.2, label=f"NeuroShield DT (AUC = {auc:.4f})")
    ax.fill_between(fpr, tpr, alpha=0.08, color="#00c4a1")

    ax.axhline(y=0.65, color="#f5a623", linestyle=":", linewidth=1.2, label="AUC target (0.65)")

    ax.set_xlabel("False Positive Rate", color="#cccccc", fontsize=11)
    ax.set_ylabel("True Positive Rate (Recall)", color="#cccccc", fontsize=11)
    ax.set_title("NeuroShield -- ROC Curve", color="#ffffff", fontsize=13)
    ax.tick_params(colors="#aaaaaa")
    for spine in ax.spines.values():
        spine.set_edgecolor("#333333")

    ax.legend(fontsize=9, framealpha=0.3, facecolor="#1a1a2e", labelcolor="#cccccc")
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    log.info(f"ROC curve saved to {save_path}")


# ---------------------------------------------------------------------------
# Validation report writer
# ---------------------------------------------------------------------------
def write_validation_report(
    metrics: dict,
    thresholds: dict,
    stats: dict,
    summary: pd.DataFrame,
    output_path: str,
):
    cm = metrics["confusion_matrix"]
    auc_gate = "PASSED" if metrics["auc_roc"] >= 0.65 else "FAILED -- see troubleshooting"

    band_dist_lines = []
    for band in ["High", "Medium", "Low"]:
        defn = thresholds["band_definitions"][band]
        band_dist_lines.append(f"- {band}: {defn}")

    report = f"""# NeuroShield Model Validation Report

Generated by: models/calibrate.py

---

## 1. Exit Gate Status

| Gate | Threshold | Result |
|------|-----------|--------|
| AUC-ROC | >= 0.65 | {metrics['auc_roc']} -- **{auc_gate}** |

---

## 2. AUC-ROC on Temporal Test Set

**{metrics['auc_roc']}**

Evaluated on the most recent 20% of discharge encounters (temporal test split).
Train: earliest 80% of encounters. Test: most recent 20%.

---

## 3. Precision and Recall at High-Risk Threshold

Threshold applied: predicted probability >= {thresholds['high_prob_threshold']}
(equivalent to risk score >= {thresholds['high_score_threshold']})

| Metric | Value |
|--------|-------|
| Precision | {metrics['precision_at_high_threshold']} |
| Recall | {metrics['recall_at_high_threshold']} |
| F1 Score | {metrics['f1_at_high_threshold']} |

---

## 4. Confusion Matrix

At High-risk threshold (prob >= {thresholds['high_prob_threshold']}):

|  | Predicted Negative | Predicted Positive |
|--|--------------------|--------------------|
| **Actual Negative** | {cm[0][0]} (TN) | {cm[0][1]} (FP) |
| **Actual Positive** | {cm[1][0]} (FN) | {cm[1][1]} (TP) |

---

## 5. Calibration Plot

See: docs/diabetic/calibration_curve.png

Population average readmission rate: {stats['population_readmission_rate']}

### Decile Summary Table

{summary[['decile_label', 'avg_predicted_prob', 'observed_readmission_rate', 'patient_count', 'readmitted_count']].to_markdown(index=False)}

---

## 6. ROC Curve

See: docs/diabetic/roc_curve.png

---

## 7. Risk Band Thresholds Chosen

{chr(10).join(band_dist_lines)}

Derivation method: decile analysis. High threshold set where observed readmission
rate >= {HIGH_MULTIPLIER}x population average ({stats['population_readmission_rate'] * HIGH_MULTIPLIER:.4f}).
Low threshold set where observed rate < {LOW_MULTIPLIER}x population average
({stats['population_readmission_rate'] * LOW_MULTIPLIER:.4f}).

Thresholds stored in machine-readable form at: docs/diabetic/band_thresholds.json

---

## 8. Known Limitations

- Dataset spans 1999-2008. Clinical practice has changed significantly.
- Age is a bracket string; lower-bound extraction is approximate.
- no_show features are proxied or transferred, not directly observed.
- No social determinant features (housing, insurance, transportation).
- No post-discharge compliance signals.
- Model is a DecisionTreeClassifier -- suitable for interpretability at MVP scale.
  Random Forest upgrade is planned post-MVP when more data is available.

---

*This report must be reviewed and signed off before Week 4 begins.*
"""

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w") as f:
        f.write(report)
    log.info(f"Validation report written to {output_path}")


# ---------------------------------------------------------------------------
# Save thresholds JSON for downstream use (FastAPI, driver extractor)
# ---------------------------------------------------------------------------
def save_thresholds(thresholds: dict, path: str):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(thresholds, f, indent=2)
    log.info(f"Band thresholds saved to {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    log.info("=" * 60)
    log.info("NeuroShield Week 3 -- Calibration")
    log.info("=" * 60)

    os.makedirs(DOCS_DIR, exist_ok=True)

    # 1. Load scored test set
    df = load_scored(TEST_SCORED_CSV)

    # 2. Population stats
    stats = population_stats(df)

    # 3. Decile calibration table
    summary = compute_decile_table(df, N_DECILES)
    summary.to_csv(CALIBRATION_CSV, index=False)
    log.info(f"Calibration summary saved to {CALIBRATION_CSV}")
    log.info(f"\nDecile table:\n{summary[['decile_label','avg_predicted_prob','observed_readmission_rate','patient_count']].to_string(index=False)}")

    # 4. Derive thresholds
    thresholds = derive_thresholds(summary, stats)

    # 5. Apply risk bands to scored df
    df = apply_risk_bands(df, thresholds)

    # 6. Metrics at High threshold
    metrics = metrics_at_high_threshold(df, thresholds)

    # 7. Plots
    plot_calibration_curve(summary, stats, thresholds, CALIBRATION_PNG)
    plot_roc_curve(df, metrics, ROC_CURVE_PNG)

    # 8. Save thresholds JSON
    save_thresholds(thresholds, THRESHOLDS_JSON)

    # 9. Validation report
    write_validation_report(metrics, thresholds, stats, summary, VALIDATION_REPORT_MD)

    # 10. Print final summary
    log.info("=" * 60)
    log.info("CALIBRATION COMPLETE")
    log.info(f"  AUC-ROC:          {metrics['auc_roc']}")
    log.info(f"  High threshold:   score >= {thresholds['high_score_threshold']}")
    log.info(f"  Low threshold:    score <  {thresholds['low_score_threshold']}")
    log.info(f"  Medium:           between Low and High")
    log.info("Next: run models/driver_extractor.py for interpretability review")
    log.info("=" * 60)

    return thresholds, metrics


if __name__ == "__main__":
    main()