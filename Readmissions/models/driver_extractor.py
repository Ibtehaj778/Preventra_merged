"""
NeuroShield -- models/driver_extractor.py
Week 3: Decision path extractor producing Top-3 plain-English driver labels
per patient. Includes interpretability review runner.

Key design: uses depth-weighted impurity reduction so that nodes closer to
the leaf (the most patient-specific decisions) are ranked higher than root
nodes that fire for almost every patient. This produces genuinely distinct
driver sets across patients even when a dominant root feature exists.

This module is both importable (used by the pipeline in Week 4) and
directly runnable for the Week 3 interpretability gate review.

Usage (interpretability review):
    python -m models.driver_extractor

Outputs (review mode):
    docs/diabetic/interpretability_review.txt  -- Top-3 labels for 10 High-risk patients
    Console printout for manual review
"""

import os
import sys
import json
import logging
import numpy as np
import pandas as pd
import mlflow.sklearn

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
TEST_SCORED_CSV = "data/diabetic/test_scored.csv"
THRESHOLDS_JSON = "docs/diabetic/band_thresholds.json"
REVIEW_OUTPUT = "docs/diabetic/interpretability_review.txt"
REGISTERED_MODEL_NAME = "readmission-dt-tuned"
MLFLOW_TRACKING_URI = "http://127.0.0.1:5000"
REVIEW_SAMPLE_SIZE = 4
RANDOM_STATE = 42

# Depth weighting: nodes deeper in the path receive an exponential boost.
# This makes patient-specific leaf-level decisions outweigh dominant root splits.
# Increase DEPTH_WEIGHT_BASE to make the extractor more leaf-focused (more unique
# per patient). Decrease toward 1.0 to weight all depths equally.
DEPTH_WEIGHT_BASE = 2.5

# ---------------------------------------------------------------------------
# Label mapping
# All templates use {value} as the placeholder for the patient's actual value.
# Binary flag features also receive {value_yn} (Yes/No string).
# Float features use {value:.2f} for 2-decimal formatting.
# ---------------------------------------------------------------------------
LABEL_MAP = {
    "charlson_comorbidity_index": (
        "Comorbidity burden score: {value} "
        "(higher score = more chronic conditions increasing readmission risk)"
    ),
    "ip_admissions_365d_prior": (
        "Prior hospital admissions in the past year: {value} "
        "(frequent admissions signal ongoing clinical instability)"
    ),
    "ed_visits_90d_prior": (
        "Emergency department visits in the past 90 days: {value} "
        "(repeated ED use suggests unmanaged acute episodes)"
    ),
    "medication_count_at_discharge": (
        "Total medications at discharge: {value} "
        "(high medication burden increases adherence complexity and adverse event risk)"
    ),
    "medication_change_flag": (
        "Medication regimen changed at discharge: {value_yn} "
        "(recent changes require careful follow-up to confirm adherence and tolerability)"
    ),
    "length_of_stay_days": (
        "Length of hospital stay: {value} days "
        "(longer stays often reflect greater illness severity and complex recovery needs)"
    ),
    "admission_acuity_flag": (
        "Admitted as emergency or urgent case: {value_yn} "
        "(emergency admissions indicate acute decompensation with higher re-admission risk)"
    ),
    "high_utilizer_flag": (
        "High prior utilization of hospital services: {value_yn} "
        "(2 or more prior inpatient or ED visits signals high system engagement and instability)"
    ),
    "high_risk_medication_flag": (
        "Prescribed insulin or other high-risk medication: {value_yn} "
        "(insulin requires careful titration; errors in dosing are a common readmission trigger)"
    ),
    "complex_discharge_flag": (
        "Complex discharge profile: {value_yn} "
        "(stay > 7 days, > 10 medications, and > 7 diagnoses together predict difficult recovery)"
    ),
    "behavioral_health_flag": (
        "Behavioral or mental health diagnosis present: {value_yn} "
        "(co-occurring mental health conditions frequently disrupt post-discharge care plans)"
    ),
    "frailty_proxy": (
        "Patient age 75 or older: {value_yn} "
        "(advanced age is associated with reduced physiological reserve and slower recovery)"
    ),
    "no_show_proxy": (
        "Low engagement with outpatient care (proxy score): {value:.2f} "
        "(derived from ED-to-outpatient visit ratio; low scores suggest poor care-seeking behaviour)"
    ),
    "probabilistic_no_show": (
        "Predicted likelihood of missing follow-up appointments: {value:.2f} "
        "(estimated from demographic and visit patterns; higher value = greater no-show risk)"
    ),
    "discharge_disposition_id": (
        "Discharge disposition ID: {value} "
        "(indicates the type of care setting the patient was discharged to, which can impact their recovery and readmission risk)"
    ),
    "admission_source_id": (
        "Admission source ID: {value} "
        "(indicates where the patient was admitted from, e.g., physician referral vs. emergency room)"
    ),
    "num_lab_procedures": (
        "Number of lab procedures during stay: {value} "
        "(more procedures often indicate higher diagnostic uncertainty or clinical severity)"
    ),
    "num_procedures": (
        "Number of medical procedures during stay: {value} "
        "(surgical or invasive procedures can complicate recovery and increase readmission risk)"
    ),
    "number_outpatient": (
        "Prior outpatient visits in the past year: {value} "
        "(indicates level of engagement with ambulatory care)"
    ),
    "diabetesMed": (
        "Prescribed diabetes medication: {value_yn} "
        "(active pharmacological treatment for diabetes indicates ongoing management needs)"
    ),
    "race_AfricanAmerican": (
        "Patient race is recorded as African American: {value_yn} "
        "(demographic factor that may correlate with specific health disparities or access issues)"
    ),
    "race_Asian": (
        "Patient race is recorded as Asian: {value_yn} "
        "(demographic factor)"
    ),
    "race_Caucasian": (
        "Patient race is recorded as Caucasian: {value_yn} "
        "(demographic factor)"
    ),
    "race_Hispanic": (
        "Patient race is recorded as Hispanic: {value_yn} "
        "(demographic factor)"
    ),
    "race_Other": (
        "Patient race is recorded as Other or Unknown: {value_yn} "
        "(demographic factor)"
    ),
    "gender_Female": (
        "Patient gender is Female: {value_yn} "
        "(demographic factor)"
    ),
    "gender_Male": (
        "Patient gender is Male: {value_yn} "
        "(demographic factor)"
    ),
    "gender_Unknown/Invalid": (
        "Patient gender is Unknown/Invalid: {value_yn} "
        "(demographic factor)"
    ),
    "max_glu_serum_>200": (
        "Max serum glucose > 200: {value_yn} "
        "(indicates poor glycemic control during admission)"
    ),
    "max_glu_serum_>300": (
        "Max serum glucose > 300: {value_yn} "
        "(indicates severe hyperglycemia during admission)"
    ),
    "max_glu_serum_Norm": (
        "Max serum glucose is Normal: {value_yn} "
        "(indicates adequate glycemic control during admission)"
    ),
    "A1Cresult_>7": (
        "A1C result > 7%: {value_yn} "
        "(indicates suboptimal long-term blood sugar control)"
    ),
    "A1Cresult_>8": (
        "A1C result > 8%: {value_yn} "
        "(indicates poor long-term blood sugar control)"
    ),
    "A1Cresult_Norm": (
        "A1C result is Normal: {value_yn} "
        "(indicates good long-term blood sugar control)"
    ),
}

# Binary features that render as Yes/No
BINARY_FEATURES = {
    "medication_change_flag",
    "admission_acuity_flag",
    "high_utilizer_flag",
    "high_risk_medication_flag",
    "complex_discharge_flag",
    "behavioral_health_flag",
    "frailty_proxy",
    "diabetesMed",
    "race_AfricanAmerican",
    "race_Asian",
    "race_Caucasian",
    "race_Hispanic",
    "race_Other",
    "gender_Female",
    "gender_Male",
    "gender_Unknown/Invalid",
    "max_glu_serum_>200",
    "max_glu_serum_>300",
    "max_glu_serum_Norm",
    "A1Cresult_>7",
    "A1Cresult_>8",
    "A1Cresult_Norm",
}

YES_NO = {0: "No", 1: "Yes", 0.0: "No", 1.0: "Yes"}


# ---------------------------------------------------------------------------
# Core driver extraction -- depth-weighted
# ---------------------------------------------------------------------------
def get_top3_drivers(
    model,
    feature_names: list,
    patient_row,
    n_drivers: int = 3,
) -> list:
    """
    Extract Top-N plain-English risk driver labels for a single patient
    using depth-weighted impurity reduction along the decision path.

    Depth weighting gives exponentially higher weight to splits that occur
    deeper in the tree. Root-level splits (shared by most patients) receive
    lower final scores. Leaf-adjacent splits (unique to this patient's
    subgroup) receive the highest scores.

    This produces genuinely distinct driver sets across patients even when
    a single dominant feature sits at the root of the tree.

    Parameters
    ----------
    model        : fitted DecisionTreeClassifier
    feature_names: list of feature column names in training order
    patient_row  : 1D array-like of feature values for this patient
    n_drivers    : number of top drivers to return (default 3)

    Returns
    -------
    List of plain-English driver label strings, length == n_drivers.
    """
    patient_arr = np.array(patient_row, dtype=float).reshape(1, -1)

    node_indicator = model.decision_path(patient_arr)
    node_ids = node_indicator.indices   # path from root to leaf

    tree = model.tree_

    scored_features = []

    for depth_idx, node_id in enumerate(node_ids[:-1]):    # exclude leaf
        feature_idx = tree.feature[node_id]
        if feature_idx < 0:
            continue    # sklearn uses -2 for leaf nodes as safety check

        n_node = tree.n_node_samples[node_id]
        n_left = tree.n_node_samples[tree.children_left[node_id]]
        n_right = tree.n_node_samples[tree.children_right[node_id]]

        # Raw impurity reduction at this split
        raw_impurity_reduction = (
            tree.impurity[node_id]
            - (n_left / n_node) * tree.impurity[tree.children_left[node_id]]
            - (n_right / n_node) * tree.impurity[tree.children_right[node_id]]
        )

        # Depth weight: nodes deeper in the path get exponentially higher weight.
        # depth_idx=0 is root (shared by all patients, weight=1.0).
        # depth_idx=path_length-1 is just above the leaf (most specific, highest weight).
        depth_weight = DEPTH_WEIGHT_BASE ** depth_idx

        weighted_score = raw_impurity_reduction * depth_weight

        scored_features.append(
            (feature_idx, weighted_score, depth_idx, raw_impurity_reduction)
        )

    if not scored_features:
        return [
            "Model path too short to extract drivers. "
            "Consider retraining with greater max_depth."
        ] * n_drivers

    # Sort by weighted score descending, deduplicate feature indices
    # (a feature may appear at multiple depths; keep only its highest-scoring occurrence)
    seen_features = set()
    unique_scored = []
    for feature_idx, w_score, depth_idx, raw_score in sorted(
        scored_features, key=lambda x: x[1], reverse=True
    ):
        if feature_idx not in seen_features:
            seen_features.add(feature_idx)
            unique_scored.append((feature_idx, w_score, depth_idx, raw_score))

    top_n = unique_scored[:n_drivers]
    labels = []

    for feature_idx, w_score, depth_idx, raw_score in top_n:
        fname = feature_names[feature_idx]
        raw_value = float(patient_row[feature_idx])
        label = _format_label(fname, raw_value)
        labels.append(label)

    # Pad to n_drivers if the path was too shallow
    while len(labels) < n_drivers:
        labels.append(
            "Decision path too shallow to extract additional driver. "
            "Retrain with greater max_depth to improve driver diversity."
        )

    return labels


def _format_label(feature_name: str, raw_value: float) -> str:
    """
    Format a plain-English label for a single feature using LABEL_MAP.
    Handles binary yes/no features, float features, and integer features.
    """
    template = LABEL_MAP.get(
        feature_name,
        f"{feature_name.replace('_', ' ').title()}: {{value}}"
    )

    try:
        if feature_name in BINARY_FEATURES:
            yn = YES_NO.get(int(raw_value), "Unknown")
            label = template.format(value=raw_value, value_yn=yn)
        elif "{value:.2f}" in template:
            label = template.format(value=raw_value)
        else:
            display_val = (
                int(raw_value) if raw_value == int(raw_value)
                else round(raw_value, 2)
            )
            label = template.format(
                value=display_val,
                value_yn=YES_NO.get(int(raw_value), str(raw_value))
            )
    except (KeyError, ValueError, TypeError):
        label = f"{feature_name.replace('_', ' ').title()}: {raw_value}"

    return label


# ---------------------------------------------------------------------------
# Batch scoring helper (used by pipeline in Week 4)
# ---------------------------------------------------------------------------
def extract_drivers_for_batch(
    model,
    feature_names: list,
    X: pd.DataFrame,
    n_drivers: int = 3,
) -> pd.DataFrame:
    """
    Run driver extraction for every row in X.
    Returns a DataFrame with columns: driver_1, driver_2, driver_3.
    """
    results = []
    for _, row in X.iterrows():
        drivers = get_top3_drivers(model, feature_names, row.values, n_drivers)
        results.append({f"driver_{i+1}": d for i, d in enumerate(drivers)})
    return pd.DataFrame(results, index=X.index)


# ---------------------------------------------------------------------------
# Model loader
# ---------------------------------------------------------------------------
def load_model(
    tracking_uri: str = MLFLOW_TRACKING_URI,
    model_name: str = REGISTERED_MODEL_NAME,
):
    for uri in [tracking_uri, "./mlruns"]:
        try:
            mlflow.set_tracking_uri(uri)
            model_uri = f"models:/{model_name}/latest"
            model = mlflow.sklearn.load_model(model_uri)
            log.info(f"Model loaded from MLflow ({uri}): {model_name}/latest")
            return model
        except Exception as e:
            log.warning(f"Could not load model from {uri}: {e}")

    raise RuntimeError(
        f"Could not load '{model_name}' from MLflow. "
        "Ensure models/train.py has been run and the model is registered."
    )


# ---------------------------------------------------------------------------
# Driver diversity diagnostic
# ---------------------------------------------------------------------------
def driver_diversity_report(drivers_list: list) -> dict:
    """
    Given a list of driver label lists (one per patient), compute what
    fraction of the Top-1 drivers are unique. A diversity score of 1.0
    means every patient got a different primary driver. A score near 0.0
    means the same feature dominated every patient.
    """
    top1s = [d[0][:40] for d in drivers_list if d]
    unique_top1 = len(set(top1s))
    total = len(top1s)
    diversity = unique_top1 / total if total > 0 else 0

    all_features_used = set()
    for driver_set in drivers_list:
        for label in driver_set:
            all_features_used.add(label.split(":")[0].strip())

    return {
        "total_patients_reviewed": total,
        "unique_top1_drivers": unique_top1,
        "top1_diversity_score": round(diversity, 3),
        "distinct_features_appearing_as_drivers": len(all_features_used),
        "features_seen": sorted(all_features_used),
    }


# ---------------------------------------------------------------------------
# Interpretability review (Week 3 gate)
# ---------------------------------------------------------------------------
def run_interpretability_review(
    model,
    test_scored_path: str = TEST_SCORED_CSV,
    thresholds_path: str = THRESHOLDS_JSON,
    output_path: str = REVIEW_OUTPUT,
    sample_size: int = REVIEW_SAMPLE_SIZE,
):
    if not os.path.exists(test_scored_path):
        raise FileNotFoundError(f"{test_scored_path} not found. Run train.py first.")
    df = pd.read_csv(test_scored_path)

    if not os.path.exists(thresholds_path):
        raise FileNotFoundError(f"{thresholds_path} not found. Run calibrate.py first.")
    with open(thresholds_path) as f:
        thresholds = json.load(f)

    high_threshold = thresholds["high_score_threshold"]

    high_risk = df[df["risk_score"] >= high_threshold]
    if len(high_risk) < sample_size:
        log.warning(
            f"Only {len(high_risk)} High-risk patients in test set. "
            f"Reviewing all of them (requested {sample_size})."
        )
        sample = high_risk
    else:
        sample = high_risk.sample(sample_size, random_state=RANDOM_STATE)

    log.info(
        f"Reviewing Top-3 drivers for {len(sample)} High-risk patients "
        f"(score >= {high_threshold})"
    )

    lines = []
    all_drivers = []
    separator = "=" * 70

    header = (
        f"{separator}\n"
        f"NeuroShield -- Interpretability Review\n"
        f"Week 3 Gate: Top-3 Driver Labels for {len(sample)} High-Risk Patients\n"
        f"High-risk threshold: score >= {high_threshold}\n"
        f"Depth weight base: {DEPTH_WEIGHT_BASE} "
        f"(higher = more patient-specific drivers)\n"
        f"{separator}\n\n"
        "REVIEWER INSTRUCTIONS:\n"
        "For each patient below, read the three driver labels aloud.\n"
        "Ask: Would a care manager with no data science background understand\n"
        "why this factor increases readmission risk for this patient?\n"
        "If any label is ambiguous, note it and update LABEL_MAP in this file.\n"
        f"\n{separator}\n"
    )
    lines.append(header)
    print(header)

    feature_cols = model.feature_names_in_.tolist()

    for i, (_, row) in enumerate(sample.iterrows(), 1):
        missing = [c for c in feature_cols if c not in row.index]
        if missing:
            log.warning(f"Patient {i}: missing feature columns {missing}. Skipping.")
            continue

        patient_features = row[feature_cols].values
        drivers = get_top3_drivers(model, feature_cols, patient_features)
        all_drivers.append(drivers)

        actual = int(row.get("label", -1))
        actual_str = (
            "YES (readmitted <30d)" if actual == 1
            else "NO" if actual == 0
            else "Unknown"
        )

        block = (
            f"Patient {i}/{len(sample)}\n"
            f"  Risk Score:     {row['risk_score']:.1f} / 100\n"
            f"  Risk Band:      High\n"
            f"  Actual outcome: {actual_str}\n"
            f"  --- Top-3 Risk Drivers ---\n"
        )
        for j, driver in enumerate(drivers, 1):
            block += f"  [{j}] {driver}\n"
        block += (
            f"\n  REVIEWER: Were all 3 labels clear? "
            f"[ ] Yes  [ ] Needs rewording\n"
        )
        block += f"  Notes: ____________________________________________\n"
        block += f"\n{'-' * 70}\n"

        lines.append(block)
        print(block)

    # Diversity report
    diversity = driver_diversity_report(all_drivers)
    diversity_block = (
        f"\n{separator}\n"
        f"DRIVER DIVERSITY REPORT\n"
        f"  Patients reviewed:               {diversity['total_patients_reviewed']}\n"
        f"  Unique Top-1 drivers:            {diversity['unique_top1_drivers']}\n"
        f"  Top-1 diversity score:           {diversity['top1_diversity_score']} "
        f"(1.0 = fully unique per patient)\n"
        f"  Distinct features seen overall:  "
        f"{diversity['distinct_features_appearing_as_drivers']}\n"
        f"  Features used: {', '.join(diversity['features_seen'])}\n"
        f"\n"
        f"  If diversity score is below 0.4, retrain with greater max_depth\n"
        f"  or increase DEPTH_WEIGHT_BASE above {DEPTH_WEIGHT_BASE}.\n"
        f"{separator}\n"
    )
    lines.append(diversity_block)
    print(diversity_block)

    footer = (
        f"\n{separator}\n"
        "GATE RESULT:\n"
        "[ ] PASS  -- All labels are clear to a non-technical reviewer\n"
        "[ ] FAIL  -- One or more labels need rewording (see notes above)\n\n"
        "If FAIL: update LABEL_MAP in models/driver_extractor.py,\n"
        "then re-run this script until all labels pass review.\n"
        f"{separator}\n"
    )
    lines.append(footer)
    print(footer)

    os.makedirs(
        os.path.dirname(output_path) if os.path.dirname(output_path) else ".",
        exist_ok=True,
    )
    with open(output_path, "w") as f:
        f.writelines(lines)

    log.info(f"Interpretability review saved to {output_path}")
    return diversity


# ---------------------------------------------------------------------------
# Global feature importance diagnostic
# ---------------------------------------------------------------------------
def print_global_feature_importance(model, feature_names: list):
    importances = model.feature_importances_
    importance_df = (
        pd.DataFrame({"feature": feature_names, "importance": importances})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )
    log.info("Global Feature Importances (Gini-based):")
    print("\n" + importance_df.to_string(index=False))
    print()

    for fname in ["no_show_proxy", "probabilistic_no_show"]:
        row = importance_df[importance_df["feature"] == fname]
        if not row.empty:
            rank = row.index[0] + 1
            imp = row["importance"].values[0]
            signal = (
                "contributing signal" if imp > 0.01
                else "low signal -- consider dropping if AUC does not improve"
            )
            log.info(
                f"  {fname}: rank {rank}/{len(feature_names)}, "
                f"importance={imp:.5f} -- {signal}"
            )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    log.info("=" * 60)
    log.info("NeuroShield Week 3 -- Driver Extractor / Interpretability Review")
    log.info("=" * 60)

    model = load_model()
    feature_cols = model.feature_names_in_.tolist()
    print_global_feature_importance(model, feature_cols)

    diversity = run_interpretability_review(
        model=model,
        test_scored_path=TEST_SCORED_CSV,
        thresholds_path=THRESHOLDS_JSON,
        output_path=REVIEW_OUTPUT,
        sample_size=REVIEW_SAMPLE_SIZE,
    )

    log.info("=" * 60)
    log.info("driver_extractor.py complete.")
    log.info(
        f"Driver diversity score: {diversity['top1_diversity_score']} "
        f"(target >= 0.4 for meaningful per-patient variation)"
    )
    log.info("Review docs/diabetic/interpretability_review.txt and mark PASS or FAIL.")
    log.info("Once PASSED, Week 3 exit criteria are met. Proceed to Week 4.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()