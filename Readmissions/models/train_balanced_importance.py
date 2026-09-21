"""
NeuroShield -- models/train_balanced_importance.py
Experimental training pipeline applying both DecisionTree and XGBoost
using the 'features_balanced_importance.csv' which maps all readmissions
to the positive class, but assigns a 0.5 sample weight to >30 days readmissions.

Usage:
    python models/train_balanced_importance.py
    python -m models.train_balanced_importance
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
FEATURES_CSV = "data/diabetic/features_balanced_importance.csv"
TEST_SCORED_CSV = "data/diabetic/test_scored_balanced_importance.csv"
TRAIN_SPLIT_RATIO = 0.80
RANDOM_STATE = 42
MLFLOW_EXPERIMENT = "neuroshield-readmission"
MLFLOW_TRACKING_URI = "http://127.0.0.1:5000"

LABEL_COL = "label"
WEIGHT_COL = "sample_weight"

# Hyperparameter grids slightly narrowed for speed
PARAM_GRID_DT = {
    "max_depth": [5, 7, 10],
    "min_samples_leaf": [10, 50],
}

PARAM_GRID_XGB = {
    "n_estimators": [50, 100],
    "max_depth": [3, 5],
    "learning_rate": [0.1],
}

# ---------------------------------------------------------------------------
# Data loading and validation
# ---------------------------------------------------------------------------
def load_and_validate(path: str) -> tuple:
    log.info(f"Loading features from {path}")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Features CSV not found at {path}. "
            "Ensure you've generated it first with add_balanced_label_with_importance()."
        )

    df = pd.read_csv(path)
    log.info(f"Loaded {len(df):,} rows, {len(df.columns)} columns")

    if LABEL_COL not in df.columns:
        raise ValueError(f"Label column '{LABEL_COL}' not found in {path}")
    if WEIGHT_COL not in df.columns:
        raise ValueError(f"Weight column '{WEIGHT_COL}' not found in {path}")

    feature_cols = [c for c in df.columns if c not in [LABEL_COL, WEIGHT_COL]]
    null_counts = df.isnull().sum()
    if null_counts.sum() > 0:
        raise ValueError(f"Null values found:\n{null_counts[null_counts > 0]}")

    log.info(f"Positive label rate: {df[LABEL_COL].mean():.4f}")
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
        f"| test={len(test_df):,} rows"
    )
    return train_df, test_df


# ---------------------------------------------------------------------------
# Tuner: DecisionTree
# ---------------------------------------------------------------------------
def tune_decision_tree(X_train, y_train, w_train, X_test, y_test) -> tuple:
    log.info("--- Tuning DecisionTreeClassifier ---")
    base_estimator = DecisionTreeClassifier(random_state=RANDOM_STATE)
    
    grid_search = GridSearchCV(
        estimator=base_estimator,
        param_grid=PARAM_GRID_DT,
        scoring="roc_auc",
        cv=3,
        n_jobs=-1,
        refit=True,
    )
    # Pass sample weight down to fit
    grid_search.fit(X_train, y_train, sample_weight=w_train.values)
    
    best_model = grid_search.best_estimator_
    y_prob = best_model.predict_proba(X_test)[:, 1]
    y_pred = best_model.predict(X_test)
    auc = roc_auc_score(y_test, y_prob)

    log.info(f"[DT] Best params: {grid_search.best_params_}")
    log.info(f"[DT] CV AUC: {grid_search.best_score_:.4f} | Test AUC: {auc:.4f}")
    return best_model, auc, y_prob, y_pred


# ---------------------------------------------------------------------------
# Tuner: XGBoost
# ---------------------------------------------------------------------------
def tune_xgboost(X_train, y_train, w_train, X_test, y_test) -> tuple:
    log.info("--- Tuning XGBClassifier ---")
    base_estimator = XGBClassifier(
        random_state=RANDOM_STATE,
        use_label_encoder=False,
        eval_metric="logloss",
        n_jobs=-1
    )
    
    grid_search = GridSearchCV(
        estimator=base_estimator,
        param_grid=PARAM_GRID_XGB,
        scoring="roc_auc",
        cv=3,
        n_jobs=1,
        refit=True,
    )
    grid_search.fit(X_train, y_train, sample_weight=w_train.values)
    
    best_model = grid_search.best_estimator_
    y_prob = best_model.predict_proba(X_test)[:, 1]
    y_pred = best_model.predict(X_test)
    auc = roc_auc_score(y_test, y_prob)

    log.info(f"[XGB] Best params: {grid_search.best_params_}")
    log.info(f"[XGB] CV AUC: {grid_search.best_score_:.4f} | Test AUC: {auc:.4f}")
    return best_model, auc, y_prob, y_pred


# ---------------------------------------------------------------------------
# Logger utility
# ---------------------------------------------------------------------------
def log_to_mlflow(model, run_name: str, test_auc: float, X_train, y_test, y_pred):
    with mlflow.start_run(run_name=run_name):
        mlflow.log_param("train_rows", len(X_train))
        mlflow.log_metric("auc_roc_test", test_auc)
        mlflow.log_metric("accuracy", accuracy_score(y_test, y_pred))
        mlflow.sklearn.log_model(model, "model", registered_model_name=run_name)
    log.info(f"Logged {run_name} to MLflow.")


# ---------------------------------------------------------------------------
# Training Pipeline Wrapper
# ---------------------------------------------------------------------------
def run_training_pipeline(features_path=FEATURES_CSV):
    df, feature_cols = load_and_validate(features_path)

    train_df, test_df = temporal_split(df, TRAIN_SPLIT_RATIO)

    X_train = train_df[feature_cols]
    y_train = train_df[LABEL_COL]
    w_train = train_df[WEIGHT_COL]

    X_test = test_df[feature_cols]
    y_test = test_df[LABEL_COL]

    model_dt, auc_dt, y_prob_dt, y_pred_dt = tune_decision_tree(
        X_train, y_train, w_train, X_test, y_test
    )

    model_xgb, auc_xgb, y_prob_xgb, y_pred_xgb = tune_xgboost(
        X_train, y_train, w_train, X_test, y_test
    )

    return {
        "model_dt": model_dt,
        "auc_dt": auc_dt,
        "model_xgb": model_xgb,
        "auc_xgb": auc_xgb,
        "X_test": X_test,
        "y_test": y_test,
        "y_prob_xgb": y_prob_xgb
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    log.info("=" * 60)
    log.info("NeuroShield -- Importance-Weighted Model Training")
    log.info("=" * 60)

    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(MLFLOW_EXPERIMENT)
    except:
        mlflow.set_tracking_uri("./mlruns")
        mlflow.set_experiment(MLFLOW_EXPERIMENT)

    df, feature_cols = load_and_validate(FEATURES_CSV)

    train_df, test_df = temporal_split(df, TRAIN_SPLIT_RATIO)
    X_train = train_df[feature_cols]
    y_train = train_df[LABEL_COL]
    w_train = train_df[WEIGHT_COL]
    
    X_test = test_df[feature_cols]
    y_test = test_df[LABEL_COL]

    # Model 1: Decision Tree
    model_dt, auc_dt, y_prob_dt, y_pred_dt = tune_decision_tree(X_train, y_train, w_train, X_test, y_test)
    log_to_mlflow(model_dt, "readmission-dt-balanced-importance", auc_dt, X_train, y_test, y_pred_dt)

    # Model 2: XGBoost
    model_xgb, auc_xgb, y_prob_xgb, y_pred_xgb = tune_xgboost(X_train, y_train, w_train, X_test, y_test)
    log_to_mlflow(model_xgb, "readmission-xgb-balanced-importance", auc_xgb, X_train, y_test, y_pred_xgb)

    # Export scored test set using the best XGBoost output
    scored = test_df.copy()
    scored["predicted_prob_xgb"] = y_prob_xgb
    scored["risk_score_xgb"] = (y_prob_xgb * 100).round(1)
    scored.to_csv(TEST_SCORED_CSV, index=False)
    log.info(f"Exported combined scoring test set to {TEST_SCORED_CSV}")

    log.info("=" * 60)
    log.info("train_balanced_importance.py complete.")
    log.info("=" * 60)

if __name__ == "__main__":
    main()
