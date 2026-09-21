"""
NeuroShield -- models/train_xgboost.py
Experimental training pipeline using XGBoost, in parallel with the Decision Tree model.
Uses the same features, temporal split, and MLflow logging as train.py.

Usage:
    python models/train_xgboost.py
    python -m models.train_xgboost
"""

import os
import sys
import json
import logging
import numpy as np
import pandas as pd
import mlflow
import mlflow.sklearn
from xgboost import XGBClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import (
    roc_auc_score,
    accuracy_score,
    precision_score,
    recall_score,
    confusion_matrix,
    classification_report,
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
FEATURES_CSV = "data/diabetic/features.csv"
TEST_SCORED_CSV = "data/diabetic/test_scored_xgb.csv"
TRAIN_SPLIT_RATIO = 0.80
RANDOM_STATE = 42
MLFLOW_EXPERIMENT = "neuroshield-readmission"
MLFLOW_TRACKING_URI = "http://127.0.0.1:5000"

LABEL_COL = "label"

PARAM_GRID = {
    "n_estimators": [50, 100],
    "max_depth": [3, 5, 7],
    "learning_rate": [0.05, 0.1],
    "subsample": [0.8, 1.0],
    "colsample_bytree": [0.8, 1.0],
}


# ---------------------------------------------------------------------------
# Data loading and validation
# ---------------------------------------------------------------------------
def load_and_validate(path: str) -> tuple:
    log.info(f"Loading features from {path}")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Features CSV not found at {path}. "
            "Run the Week 2 feature engineering pipeline first."
        )

    df = pd.read_csv(path)
    
    log.info(f"Loaded {len(df):,} rows, {len(df.columns)} columns")

    if LABEL_COL not in df.columns:
        raise ValueError(f"Label column '{LABEL_COL}' not found in {path}")

    feature_cols = [c for c in df.columns if c != LABEL_COL]

    null_counts = df.isnull().sum()
    if null_counts.sum() > 0:
        raise ValueError(
            f"Null values found in feature/label columns:\n{null_counts[null_counts > 0]}"
        )

    log.info(f"Positive label rate: {df[LABEL_COL].mean():.4f} ({df[LABEL_COL].sum():,} positives)")
    return df, feature_cols


# ---------------------------------------------------------------------------
# Temporal split
# ---------------------------------------------------------------------------
def temporal_split(df: pd.DataFrame, ratio: float):
    """
    Sort by index (encounter order as temporal proxy -- dataset is roughly
    chronological). Assign earliest `ratio` fraction to train, rest to test.
    This exactly matches the logic in train.py.
    """
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
# Hyperparameter tuning (including Baseline logging equivalents)
# ---------------------------------------------------------------------------
def tune_model(X_train, y_train, X_test, y_test) -> tuple:
    """
    GridSearchCV over PARAM_GRID, scoring on roc_auc, 3-fold CV.
    Returns (best_model, best_params, auc_roc, y_prob).
    """
    log.info("Starting GridSearchCV hyperparameter tuning for XGBoost...")
    log.info(
        f"Grid size: {len(PARAM_GRID['n_estimators']) * len(PARAM_GRID['max_depth']) * len(PARAM_GRID['learning_rate']) * len(PARAM_GRID['subsample']) * len(PARAM_GRID['colsample_bytree'])} "
        f"combinations x 3 folds"
    )

    # Compute class weight for imbalance
    neg_count = (y_train == 0).sum()
    pos_count = (y_train == 1).sum()
    scale_pos_weight = neg_count / pos_count if pos_count > 0 else 1.0
    log.info(f"Computed scale_pos_weight for XGBoost: {scale_pos_weight:.2f}")

    base_estimator = XGBClassifier(
        random_state=RANDOM_STATE,
        scale_pos_weight=scale_pos_weight,
        use_label_encoder=False,
        eval_metric="logloss",
        n_jobs=-1
    )

    # Using 3 folds for faster experimental turnaround
    grid_search = GridSearchCV(
        estimator=base_estimator,
        param_grid=PARAM_GRID,
        scoring="roc_auc",
        cv=3,
        n_jobs=1,
        verbose=1,
        refit=True,
    )
    grid_search.fit(X_train, y_train)

    best_model = grid_search.best_estimator_
    best_params = grid_search.best_params_
    best_cv_score = grid_search.best_score_

    y_prob = best_model.predict_proba(X_test)[:, 1]
    y_pred = best_model.predict(X_test)
    auc = roc_auc_score(y_test, y_prob)

    log.info(f"Best params: {best_params}")
    log.info(f"Best CV AUC-ROC: {best_cv_score:.4f}")
    log.info(f"Test set AUC-ROC: {auc:.4f}")

    # Optional: Feature Importance printout
    if hasattr(best_model, "feature_importances_"):
        top_indices = np.argsort(best_model.feature_importances_)[::-1][:10]
        feature_cols = list(X_train.columns)
        log.info("Top 10 Feature Importances (XGBoost):")
        for idx in top_indices:
            log.info(f"  {feature_cols[idx]}: {best_model.feature_importances_[idx]:.4f}")

    return best_model, best_params, best_cv_score, auc, y_prob, y_pred


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
    y_pred,
):
    log.info("Logging XGBoost run to MLflow...")

    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    acc = accuracy_score(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred).tolist()

    with mlflow.start_run(run_name="readmission-xgb-tuned") as run:
        # Parameters
        feature_cols = list(X_train.columns)
        mlflow.log_param("model_type", "XGBClassifier")
        mlflow.log_param("scale_pos_weight", model.scale_pos_weight)
        mlflow.log_param("train_rows", len(X_train))
        mlflow.log_param("test_rows", len(X_test))
        mlflow.log_param("feature_count", len(feature_cols))
        mlflow.log_param("features", json.dumps(feature_cols))
        
        for param_name, param_value in best_params.items():
            mlflow.log_param(param_name, param_value)

        # Metrics requested
        mlflow.log_metric("auc_roc_cv", cv_auc)
        mlflow.log_metric("auc_roc_test", test_auc)
        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("precision", precision)
        mlflow.log_metric("recall", recall)

        # Log confusion matrix as artifact
        cm_df = pd.DataFrame(
            cm,
            index=["Actual_0", "Actual_1"],
            columns=["Pred_0", "Pred_1"],
        )
        cm_path = "data/diabetic/confusion_matrix_xgb.csv"
        cm_df.to_csv(cm_path)
        mlflow.log_artifact(cm_path)

        # Log classification report
        report = classification_report(y_test, y_pred, output_dict=False)
        report_path = "docs/diabetic/classification_report_xgb.txt"
        os.makedirs("docs", exist_ok=True)
        with open(report_path, "w") as f:
            f.write(report)
        mlflow.log_artifact(report_path)

        # Register model
        mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path="model",
            registered_model_name="readmission-xgb-tuned",
        )

        run_id = run.info.run_id
        log.info(f"Tuned XGBoost run logged. Run ID: {run_id} | Test AUC-ROC = {test_auc:.4f}")
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
    """
    Attach risk_score (0-100) and predicted_prob to the test DataFrame.
    Save to output_path for use by calibrate.py or worklist views.
    """
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
# Main
# ---------------------------------------------------------------------------
def main():
    log.info("=" * 60)
    log.info("NeuroShield -- EXPERIMENTAL XGBoost Training")
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

    # 1. Load and validate features
    df, feature_cols = load_and_validate(FEATURES_CSV)

    # 2. Temporal split
    train_df, test_df = temporal_split(df, TRAIN_SPLIT_RATIO)
    X_train = train_df[feature_cols]
    y_train = train_df[LABEL_COL]
    X_test = test_df[feature_cols]
    y_test = test_df[LABEL_COL]

    # 3. Tuned model training
    best_model, best_params, cv_auc, tuned_auc, y_prob_tuned, y_pred_tuned = tune_model(
        X_train, y_train, X_test, y_test
    )
    
    # 4. Log to MLflow
    log_tuned_to_mlflow(
        best_model, best_params, cv_auc, tuned_auc,
        X_train, y_train, X_test, y_test, y_prob_tuned, y_pred_tuned
    )

    # 5. Compute and export risk scores
    compute_and_export_scores(best_model, test_df, y_prob_tuned, TEST_SCORED_CSV)

    # 6. Sample SHAP Explainability
    import models.shap_utils as shap_utils
    log.info("Generating SHAP explainability examples for a small sample...")
    explainer = shap_utils.build_shap_explainer(best_model)
    
    # Grab 3 random cases (e.g. indices 0, 10, 20) to print to console
    sample_X = X_test.iloc[[0, 10, 20]]
    for idx_num, i in enumerate(range(len(sample_X))):
        patient_row = sample_X.iloc[[i]]
        prob = best_model.predict_proba(patient_row)[0, 1]
        risk_score = prob * 100
        human_explanation = shap_utils.get_patient_explanation(explainer, patient_row)
        log.info(f"Patient Sample {idx_num + 1} (Risk Score: {risk_score:.1f}%): top drivers: {human_explanation}")

    log.info("=" * 60)
    log.info("train_xgboost.py complete. Experimental model trained and exported.")
    log.info("=" * 60)

    return best_model, tuned_auc


if __name__ == "__main__":
    main()
