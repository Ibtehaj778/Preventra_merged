"""
MIMIC-IV scoring path for the Preventra API.

Replaces the UCI-diabetes scoring code in api/main.py:
  _build_feature_vector   34 diabetes features  -> 94 MIMIC features
  _extract_top3_drivers   decision-tree walker  -> SHAP (see models/mimic_drivers)
  _get_risk_band          UCI thresholds        -> MIMIC score distribution

Design note on manual entry
---------------------------
The model was trained on batch-derived features, many of which nobody can type
at a bedside (48 lab aggregates, APR-DRG severity, 17 Charlson flags). The form
therefore collects only what a clinician plausibly knows at discharge, and
every other feature is left as NaN.

That is deliberate and safe: HistGradientBoosting learned a split direction for
missing values during training, so NaN is a value it handles natively rather
than an error. Fields left blank simply carry less information - they do not
break the prediction. Population medians are available via
`docs/mimic/mimic_feature_spec.json` for callers that prefer imputation, but the
default is honest missingness.
"""

from __future__ import annotations

import json
import os
import threading
from typing import Optional

import numpy as np
import pandas as pd

from models.mimic_drivers import (inner_estimator, load_bundle,
                                  preprocess_for_shap, top_drivers)

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The Phase 1 notebook writes its artefacts to this results directory. Both the
# model and the feature spec are read from there so a retrain can never leave
# the serving form describing a different model than the one doing the scoring.
_RESULTS = os.path.join(_BASE, "data", "mimic",
                        "model", "results")
MODEL_PATH = os.environ.get("MIMIC_MODEL_PATH",
                            os.path.join(_RESULTS, "phase1_model.joblib"))

_SPEC_IN_RESULTS = os.path.join(_RESULTS, "mimic_feature_spec.json")
SPEC_PATH = (_SPEC_IN_RESULTS if os.path.exists(_SPEC_IN_RESULTS)
             else os.path.join(_BASE, "docs", "mimic", "mimic_feature_spec.json"))
BANDS_PATH = os.path.join(_BASE, "docs", "mimic", "band_thresholds_mimic.json")

_lock = threading.Lock()
_state: dict = {}


def _load():
    """Load model, spec and explainer once, on first use."""
    if _state:
        return _state
    with _lock:
        if _state:
            return _state

        bundle = load_bundle(MODEL_PATH)
        spec = json.load(open(SPEC_PATH))

        try:
            bands = json.load(open(BANDS_PATH))
        except FileNotFoundError:
            # Fall back to the model's tuned operating point if the ETL that
            # writes the band file has not been run yet.
            # Same fixed bands as docs/mimic/band_thresholds_mimic.json, so a
            # missing file cannot silently reband the whole cohort.
            bands = {"high_score_threshold": 40.0, "low_score_threshold": 20.0}

        import shap
        hgb = inner_estimator(bundle["model"])

        _state.update({
            "model": bundle["model"],
            "hgb": hgb,
            "features": spec["features"],
            "categoricals": spec["categoricals"],
            "defaults": spec.get("population_defaults", {}),
            "bands": bands,
            "explainer": shap.TreeExplainer(hgb),
        })
    return _state


# ---------------------------------------------------------------------------
# Manual-entry contract
# ---------------------------------------------------------------------------
# Only fields a clinician can realistically supply at discharge. Anything the
# model wants but this does not cover is left missing.

ENTERABLE_CATEGORICAL = ["gender", "race", "insurance", "marital_status", "admission_type"]

ENTERABLE_NUMERIC = [
    "anchor_age", "los_days", "n_prior_adm", "days_since_prev",
    "ed_hours", "n_procedures", "n_diagnoses",
    "n_drug_orders", "n_distinct_drugs",
    "drg_severity", "drg_mortality",
]

ENTERABLE_FLAGS = [
    "ed_visit", "is_emergency", "readmit_history",
    "med_insulin", "med_anticoagulant", "med_opioid", "med_diuretic", "med_antipsychotic",
    "disch_home", "disch_snf", "disch_ama",
]

# Charlson comorbidities are checkboxes; charlson_score is derived, never typed.
CHARLSON_FLAGS = [
    "myocardial_infarction", "congestive_heart_failure", "peripheral_vascular",
    "cerebrovascular", "dementia", "chronic_pulmonary", "rheumatic", "peptic_ulcer",
    "mild_liver", "diabetes_uncomplicated", "diabetes_complicated", "hemiplegia",
    "renal_disease", "malignancy", "severe_liver", "metastatic_cancer", "hiv_aids",
]

CHARLSON_WEIGHTS = {
    "myocardial_infarction": 1, "congestive_heart_failure": 1, "peripheral_vascular": 1,
    "cerebrovascular": 1, "dementia": 1, "chronic_pulmonary": 1, "rheumatic": 1,
    "peptic_ulcer": 1, "mild_liver": 1, "diabetes_uncomplicated": 1,
    "diabetes_complicated": 2, "hemiplegia": 2, "renal_disease": 2, "malignancy": 2,
    "severe_liver": 3, "metastatic_cancer": 6, "hiv_aids": 6,
}

# A short list of labs worth asking for; the rest of the 48 stay missing.
ENTERABLE_LABS = [
    "lab_sodium_last", "lab_creatinine_last", "lab_hemoglobin_last",
    "lab_albumin_min", "lab_wbc_max", "lab_glucose_last", "lab_hba1c_last",
    "lab_potassium_last", "lab_bun_last", "lab_platelets_last",
]


def manual_entry_schema() -> dict:
    """Describes the manual-entry form to the frontend, including valid categories."""
    st = _load()
    return {
        "categorical": {c: st["categoricals"].get(c, []) for c in ENTERABLE_CATEGORICAL},
        "numeric": ENTERABLE_NUMERIC,
        "flags": ENTERABLE_FLAGS,
        "comorbidities": CHARLSON_FLAGS,
        "labs": ENTERABLE_LABS,
        "note": "Blank fields are treated as unknown, not as zero.",
    }


def build_feature_frame(payload: dict) -> pd.DataFrame:
    """
    Turn a manual-entry payload into the single-row frame the model expects.

    Unsupplied features become NaN. Categorical columns are cast to the exact
    category set seen in training so an unrecognised level lands as NaN rather
    than being silently mis-encoded as a different category.
    """
    st = _load()
    features, cats = st["features"], st["categoricals"]

    row = {f: np.nan for f in features}

    for key, value in (payload or {}).items():
        if key in row and value is not None and value != "":
            row[key] = value

    # charlson_score is always derived from the checkboxes, never trusted from input
    if any(payload.get(c) for c in CHARLSON_FLAGS):
        row["charlson_score"] = float(sum(
            CHARLSON_WEIGHTS[c] for c in CHARLSON_FLAGS if payload.get(c)
        ))
    for c in CHARLSON_FLAGS:
        if c in row:
            row[c] = 1.0 if payload.get(c) else 0.0

    # prior_adm_flag follows from n_prior_adm rather than being asked twice
    npa = payload.get("n_prior_adm")
    if npa not in (None, ""):
        row["prior_adm_flag"] = 1.0 if float(npa) > 0 else 0.0

    df = pd.DataFrame([row], columns=features)

    for c, levels in cats.items():
        if c in df.columns:
            df[c] = pd.Categorical(df[c].astype("object"), categories=levels)

    for c in df.columns:
        if c not in cats:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


def risk_band(score_pct: float) -> str:
    b = _load()["bands"]
    if score_pct >= b["high_score_threshold"]:
        return "High"
    if score_pct >= b["low_score_threshold"]:
        return "Medium"
    return "Low"


def score_frame(df: pd.DataFrame) -> dict:
    """Score a prepared single-row frame and explain it."""
    st = _load()
    proba = float(st["model"].predict_proba(df[st["features"]])[0][1])
    score = round(proba * 100, 1)

    Xt, names = preprocess_for_shap(st["hgb"], df[st["features"]], st["features"])
    sv = np.array(st["explainer"].shap_values(Xt))[0]
    raw = df[st["features"]].reindex(columns=names).iloc[0].values
    drivers = top_drivers(sv, names, raw, top_n=3)

    return {
        "risk_score": score,
        "risk_band": risk_band(score),
        "drivers": [_split_driver(d) for d in drivers],
        "driver_1_raw": drivers[0],
        "driver_2_raw": drivers[1],
        "driver_3_raw": drivers[2],
    }


def score_manual_entry(payload: dict) -> dict:
    return score_frame(build_feature_frame(payload))


def _split_driver(s: str) -> dict:
    """
    Parse 'Label: value (explanation)' into the shape the dashboard renders.

    Splits on the FIRST ': ' to take the label, then on the LAST ' (' to peel
    off the explanation. Doing it in that order keeps labels and values that
    themselves contain brackets from being truncated.
    """
    label, sep, rest = s.partition(": ")
    if not sep:
        return {"category": "clinical", "label": s.strip(), "value": "", "explanation": ""}

    if rest.endswith(")") and " (" in rest:
        value, _, explanation = rest.rpartition(" (")
        return {"category": "clinical", "label": label.strip(),
                "value": value.strip(), "explanation": explanation.rstrip(")").strip()}

    return {"category": "clinical", "label": label.strip(),
            "value": rest.strip(), "explanation": ""}
