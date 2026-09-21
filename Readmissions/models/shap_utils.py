"""
models/shap_utils.py
SHAP explainability utilities for XGBoost. 
Produces human-readable feature importance drivers suitable for clinical displays.
"""

import shap
import numpy as np
import pandas as pd

# Human-readable translations for clinical end-users
FEATURE_MAPPING = {
    "discharge_disposition_id": "Discharge destination",
    "admission_source_id": "Admission source",
    "num_lab_procedures": "Number of lab tests performed",
    "num_procedures": "Number of medical procedures performed",
    "number_outpatient": "Number of prior outpatient visits",
    "diabetesMed": "Prescribed diabetic medication",
    "charlson_comorbidity_index": "Patient comorbidity index (CCI)",
    "ip_admissions_365d_prior": "Prior inpatient admissions (last 365 days)",
    "ed_visits_90d_prior": "Prior emergency visits (last 90 days)",
    "medication_count_at_discharge": "Number of medications prescribed",
    "length_of_stay_days": "Length of hospital stay",
    "medication_change_flag": "Change in medication regimen",
    "admission_acuity_flag": "High-acuity admission status",
    "high_utilizer_flag": "High historical utilization of hospital resources",
    "high_risk_medication_flag": "Prescribed high-risk medication",
    "complex_discharge_flag": "Complex discharge parameters",
    "behavioral_health_flag": "Underlying behavioral health condition",
    "frailty_proxy": "Frailty proxy (age >= 75)",
    "no_show_proxy": "Historical missed appointment pattern",
    "probabilistic_no_show": "Predictive missed appointment likelihood",
    "race_AfricanAmerican": "Patient demographic: African American",
    "race_Asian": "Patient demographic: Asian",
    "race_Caucasian": "Patient demographic: Caucasian",
    "race_Hispanic": "Patient demographic: Hispanic",
    "race_Other": "Patient demographic: Other",
    "gender_Female": "Patient gender: Female",
    "gender_Male": "Patient gender: Male",
    "gender_Unknown/Invalid": "Patient gender: Unknown",
    "max_glu_serum_>200": "Max glucose serum level (>200)",
    "max_glu_serum_>300": "Max glucose serum level (>300)",
    "max_glu_serum_Norm": "Normal max glucose serum level",
    "A1Cresult_>7": "A1C test result (>7)",
    "A1Cresult_>8": "A1C test result (>8)",
    "A1Cresult_Norm": "Normal A1C test result",
}


def build_shap_explainer(model, X_background=None):
    """
    Build and return a SHAP TreeExplainer for the given tree-based model.
    X_background is typically not strictly required for TreeExplainer without interactions, 
    but can be supplied for baseline expected values.
    """
    explainer = shap.TreeExplainer(model)
    return explainer


def compute_shap_values(explainer, X: pd.DataFrame) -> np.ndarray:
    """
    Compute raw SHAP values for the provided dataframe X.
    """
    shap_obj = explainer(X)
    return shap_obj.values


def get_top_3_drivers(shap_values_row: np.ndarray, feature_names: list) -> list:
    """
    Extract the top 3 strongest drivers (by absolute SHAP magnitude) for one patient.
    Returns a list of dicts: [{ "feature": str, "contribution": float, "direction": str }]
    """
    # Sort absolute magnitudes descending
    top_indices = np.argsort(np.abs(shap_values_row))[::-1]
    
    drivers = []
    for idx in top_indices[:3]:
        val = shap_values_row[idx]
        if val == 0:
            continue
        
        direction = "increased risk" if val > 0 else "decreased risk"
        drivers.append({
            "feature": feature_names[idx],
            "contribution": float(val),
            "direction": direction
        })
        
    return drivers


def format_human_readable_drivers(drivers: list) -> list:
    """
    Takes the structured output of `get_top_3_drivers` and turns it into clean 
    user-facing text explanations.
    """
    explanations = []
    for driver in drivers:
        raw_feat_name = driver["feature"]
        clean_name = FEATURE_MAPPING.get(raw_feat_name, raw_feat_name)
        direction = driver["direction"]
        
        # e.g., "Frequent inpatient admissions (increased risk)"
        explanations.append(f"{clean_name} ({direction})")
        
    return explanations


def get_patient_explanation(explainer, X_row: pd.DataFrame) -> list:
    """
    End-to-end convenience method: pass an explainer and a single-row DataFrame.
    Returns a list of human-readable text strings explaining the prediction.
    """
    feature_names = list(X_row.columns)
    shap_vals = compute_shap_values(explainer, X_row)
    
    # Select first row's array
    row_vals = shap_vals[0]
    
    top_drivers = get_top_3_drivers(row_vals, feature_names)
    human_text = format_human_readable_drivers(top_drivers)
    
    return human_text
