"""
NeuroShield -- models/train_balanced.py
Trains the DecisionTree using the add_balanced_label feature pipeline.
Risk score computation and logging via MLflow.
"""

import os
import sys
import json
import logging
import numpy as np
import pandas as pd
import mlflow
import mlflow.sklearn
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import (
    roc_auc_score,
    precision_score,
    recall_score,
    confusion_matrix,
    classification_report,
)

from features.clean import load_and_clean
from features.label import add_balanced_label
from features.cci import add_cci_feature
from features.engineer import run_feature_pipeline
from features.build_features import build_features
from pathlib import Path

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
FEATURES_CSV = "data/diabetic/features_balanced.csv"
TEST_SCORED_CSV = "data/diabetic/test_scored_balanced.csv"
TRAIN_SPLIT_RATIO = 0.80
RANDOM_STATE = 42
MLFLOW_EXPERIMENT = "neuroshield-readmission"
MLFLOW_TRACKING_URI = "http://127.0.0.1:5000"

LABEL_COL = "label"

PARAM_GRID = {
    "max_depth": [3, 5, 7, 10],
    "min_samples_leaf": [5, 10, 20, 50],
    "min_samples_split": [10, 20, 50],
}


# ---------------------------------------------------------------------------
# Data loading and validation
# ---------------------------------------------------------------------------
def generate_and_validate() -> tuple:
    log.info("Generating features using balanced label pipeline...")
    
    df = load_and_clean()
    df = add_balanced_label(df)
    df = add_cci_feature(df)
    df = run_feature_pipeline(df)
    
    df = build_features(df, output_path=Path(FEATURES_CSV))
    
    feature_cols = [c for c in df.columns if c != LABEL_COL]
    return df, feature_cols


# ---------------------------------------------------------------------------
# Temporal split
# ---------------------------------------------------------------------------
def temporal_split(df: pd.DataFrame, ratio: float):
    df = df.reset_index(drop=True)
    split_idx = int(len(df) * ratio)
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()

    log.info(
        f"Temporal split: train={len(train_df):,} rows "
        f"({train_df[LABEL_COL].mean():.4f} positive rate) | "
        f"test={len(test_df):,} rows "
        f"({test_df[LABEL_COL].mean():.4f} positive rate)"
    )
    return train_df, test_df


# ---------------------------------------------------------------------------
# Baseline model
# ---------------------------------------------------------------------------
def train_baseline(X_train, y_train, X_test, y_test) -> tuple:
    log.info("Training baseline DecisionTreeClassifier...")

    model = DecisionTreeClassifier(
        class_weight="balanced",
        random_state=RANDOM_STATE,
    )
    model.fit(X_train, y_train)

    y_prob = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_prob)

    log.info(f"Baseline AUC-ROC: {auc:.4f}")
    return model, auc, y_prob


def log_baseline_to_mlflow(model, auc: float, X_train, y_train):
    log.info("Logging baseline run to MLflow...")
    with mlflow.start_run(run_name="readmission-dt-balanced-baseline"):
        feature_cols = list(X_train.columns)
        mlflow.log_param("model_type", "DecisionTreeClassifier")
        mlflow.log_param("class_weight", "balanced")
        mlflow.log_param("max_depth", "None (default)")
        mlflow.log_param("train_rows", len(X_train))
        mlflow.log_param("feature_count", len(feature_cols))
        mlflow.log_param("features", json.dumps(feature_cols))
        mlflow.log_metric("auc_roc", auc)
        mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path="model",
            registered_model_name="readmission-dt-balanced-baseline",
        )
        log.info(f"Baseline run logged. AUC-ROC = {auc:.4f}")


# ---------------------------------------------------------------------------
# Hyperparameter tuning
# ---------------------------------------------------------------------------
def tune_model(X_train, y_train, X_test, y_test) -> tuple:
    log.info("Starting GridSearchCV hyperparameter tuning...")
    log.info(
        f"Grid size: {len(PARAM_GRID['max_depth']) * len(PARAM_GRID['min_samples_leaf']) * len(PARAM_GRID['min_samples_split'])} "
        f"combinations x 5 folds"
    )

    base_estimator = DecisionTreeClassifier(
        class_weight="balanced",
        random_state=RANDOM_STATE,
    )

    grid_search = GridSearchCV(
        estimator=base_estimator,
        param_grid=PARAM_GRID,
        scoring="roc_auc",
        cv=5,
        n_jobs=-1,
        verbose=1,
        refit=True,
    )
    grid_search.fit(X_train, y_train)

    best_model = grid_search.best_estimator_
    best_params = grid_search.best_params_
    best_cv_score = grid_search.best_score_

    y_prob = best_model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_prob)

    log.info(f"Best params: {best_params}")
    log.info(f"Best CV AUC-ROC: {best_cv_score:.4f}")
    log.info(f"Test set AUC-ROC: {auc:.4f}")

    return best_model, best_params, best_cv_score, auc, y_prob


def log_tuned_to_mlflow(
    model,
    best_params: dict,
    cv_auc: float,
    test_auc: float,
    X_train,
    y_train,
    X_test,
    y_test,
    y_prob,
):
    log.info("Logging tuned run to MLflow...")

    y_pred = (y_prob >= 0.5).astype(int)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    cm = confusion_matrix(y_test, y_pred).tolist()

    with mlflow.start_run(run_name="readmission-dt-balanced-tuned") as run:
        # Parameters
        feature_cols = list(X_train.columns)
        mlflow.log_param("model_type", "DecisionTreeClassifier")
        mlflow.log_param("class_weight", "balanced")
        mlflow.log_param("train_rows", len(X_train))
        mlflow.log_param("test_rows", len(X_test))
        mlflow.log_param("feature_count", len(feature_cols))
        mlflow.log_param("features", json.dumps(feature_cols))
        for param_name, param_value in best_params.items():
            mlflow.log_param(param_name, param_value)

        # Metrics
        mlflow.log_metric("auc_roc_cv", cv_auc)
        mlflow.log_metric("auc_roc_test", test_auc)
        mlflow.log_metric("precision_at_0_5", precision)
        mlflow.log_metric("recall_at_0_5", recall)

        # Log confusion matrix as artifact
        cm_df = pd.DataFrame(
            cm,
            index=["Actual_0", "Actual_1"],
            columns=["Pred_0", "Pred_1"],
        )
        cm_path = "data/diabetic/confusion_matrix_balanced.csv"
        cm_df.to_csv(cm_path)
        mlflow.log_artifact(cm_path)

        # Log classification report
        report = classification_report(y_test, y_pred, output_dict=False)
        report_path = "docs/diabetic/classification_report_balanced.txt"
        os.makedirs("docs", exist_ok=True)
        with open(report_path, "w") as f:
            f.write(report)
        mlflow.log_artifact(report_path)

        # Register model
        mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path="model",
            registered_model_name="readmission-dt-balanced-tuned",
        )

        run_id = run.info.run_id
        log.info(f"Tuned run logged. Run ID: {run_id} | Test AUC-ROC = {test_auc:.4f}")
        return run_id


# ---------------------------------------------------------------------------
# Risk score computation and export
# ---------------------------------------------------------------------------
def compute_and_export_scores(
    model,
    test_df: pd.DataFrame,
    y_prob: np.ndarray,
    output_path: str,
):
    scored = test_df.copy()
    scored["predicted_prob"] = y_prob
    scored["risk_score"] = (y_prob * 100).round(1)

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    scored.to_csv(output_path, index=False)

    log.info(f"Risk scores computed. Score distribution:")
    log.info(f"  min={scored['risk_score'].min():.1f}  "
             f"max={scored['risk_score'].max():.1f}  "
             f"mean={scored['risk_score'].mean():.1f}  "
             f"median={scored['risk_score'].median():.1f}")
    log.info(f"Scored test set saved to {output_path}")
    return scored


# ---------------------------------------------------------------------------
# AUC-ROC gate
# ---------------------------------------------------------------------------
def check_exit_gate(auc: float, threshold: float = 0.64):
    if auc >= threshold:
        log.info(f"EXIT GATE PASSED: AUC-ROC {auc:.4f} >= {threshold}")
    else:
        log.warning(
            f"EXIT GATE NOT MET: AUC-ROC {auc:.4f} < {threshold}. "
            "See troubleshooting steps in the Week 3 guide. "
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    log.info("=" * 60)
    log.info("NeuroShield Week 3 -- Model Training (Balanced Labels)")
    log.info("=" * 60)

    # MLflow setup
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(MLFLOW_EXPERIMENT)
        log.info(f"MLflow tracking URI: {MLFLOW_TRACKING_URI}")
    except Exception as e:
        log.warning(f"Could not connect to MLflow server: {e}")
        log.warning("Falling back to local file-based tracking (./mlruns)")
        mlflow.set_tracking_uri("./mlruns")
        mlflow.set_experiment(MLFLOW_EXPERIMENT)

    # 1. Generate and validate features
    df, feature_cols = generate_and_validate()

    # 2. Temporal split
    train_df, test_df = temporal_split(df, TRAIN_SPLIT_RATIO)
    X_train = train_df[feature_cols]
    y_train = train_df[LABEL_COL]
    X_test = test_df[feature_cols]
    y_test = test_df[LABEL_COL]

    # 3. Baseline model
    baseline_model, baseline_auc, _ = train_baseline(X_train, y_train, X_test, y_test)
    log_baseline_to_mlflow(baseline_model, baseline_auc, X_train, y_train)

    # 4. Tuned model
    best_model, best_params, cv_auc, tuned_auc, y_prob_tuned = tune_model(
        X_train, y_train, X_test, y_test
    )
    log_tuned_to_mlflow(
        best_model, best_params, cv_auc, tuned_auc,
        X_train, y_train, X_test, y_test, y_prob_tuned,
    )

    # 5. Compute and export risk scores
    compute_and_export_scores(best_model, test_df, y_prob_tuned, TEST_SCORED_CSV)

    # 6. Exit gate
    check_exit_gate(tuned_auc)

    log.info("=" * 60)
    log.info("train_balanced.py complete.")
    log.info("=" * 60)

    return best_model, tuned_auc


if __name__ == "__main__":
    main()
