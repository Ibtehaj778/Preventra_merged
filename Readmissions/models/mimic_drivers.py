"""
Per-patient risk-driver extraction for the MIMIC-IV Phase 1 model.

Replaces the decision-path walker in models/driver_extractor.py, which only
works on a DecisionTreeClassifier. The MIMIC model is a
HistGradientBoostingClassifier wrapped in CalibratedClassifierCV, which exposes
neither `.tree_` nor `.decision_path`, so attribution is done with SHAP instead.

SHAP is attributed against the INNER HistGradientBoosting estimator rather than
the calibrated wrapper. Calibration is a monotonic transform of the score, so it
cannot change which features pushed a patient up or down - only the final
probability, which is read separately from the calibrated model.

Output strings match the format the API and dashboard already parse:

    "<Label>: <value> (<explanation>)"
"""

from __future__ import annotations

import warnings

import numpy as np

# ---------------------------------------------------------------------------
# scikit-learn version compatibility
# ---------------------------------------------------------------------------
# The bundle was pickled under scikit-learn 1.6.1 (Kaggle). 1.7 removed the
# private list subclass below that 1.6 pickles reference for ColumnTransformer
# remainder bookkeeping. Re-registering it lets 1.7 unpickle the model.
#
# Verified equivalent: predictions under this shim are BITWISE IDENTICAL to
# those produced by a genuine 1.6.1 environment across a 3,000-row sample.
def _install_sklearn_compat() -> None:
    import sklearn.compose._column_transformer as ct

    if not hasattr(ct, "_RemainderColsList"):
        class _RemainderColsList(list):
            def __init__(self, cols=(), *args, **kwargs):
                super().__init__(cols)

        ct._RemainderColsList = _RemainderColsList


def load_bundle(path: str) -> dict:
    """Load the phase1_model.joblib bundle, applying the version shim first."""
    _install_sklearn_compat()
    import joblib

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return joblib.load(path)


def inner_estimator(calibrated_model):
    """The HistGradientBoosting underneath CalibratedClassifierCV."""
    return calibrated_model.calibrated_classifiers_[0].estimator


def preprocess_for_shap(hgb, X, feature_names):
    """
    Encode a feature frame the way the model does internally, and return the
    matching column names.

    SHAP's TreeExplainer needs a numeric array, but the frame carries pandas
    `category` columns. Rather than re-deriving an encoding (and risking a
    mismatch with training), this reuses the estimator's own fitted
    ColumnTransformer.

    That transformer is built from a boolean mask with `remainder="drop"`, so
    its output is ordered [categorical columns] + [numeric columns], each group
    keeping its original relative order - NOT the original feature order. The
    returned name list encodes that reordering so SHAP columns stay aligned to
    the right features.
    """
    mask = list(hgb.is_categorical_)
    out_names = ([f for f, is_cat in zip(feature_names, mask) if is_cat]
                 + [f for f, is_cat in zip(feature_names, mask) if not is_cat])
    Xt = hgb._preprocessor.transform(X)
    if Xt.shape[1] != len(out_names):
        raise RuntimeError(
            f"preprocessor produced {Xt.shape[1]} columns but {len(out_names)} "
            "names were derived - the transformer layout has changed"
        )
    return Xt, out_names


# ---------------------------------------------------------------------------
# Clinician-facing labels
# ---------------------------------------------------------------------------

# concept -> (display name, why-if-LOW, why-if-HIGH, ref_low, ref_high, unit)
#
# Reference ranges are standard adult values. They exist so the explanation can
# follow the actual measurement: the previous single static string claimed
# "elevation signals renal impairment" even when the flagged creatinine was low,
# which is the kind of contradiction that makes a driver list untrustworthy.
_LAB_CONCEPTS = {
    "hba1c":       ("HbA1c", "unusually low long-term glucose, which can follow over-treatment",
                    "sustained hyperglycemia and poor long-term glycemic control", 4.0, 5.7, "%"),
    "glucose":     ("Blood glucose", "hypoglycemia, a common cause of early return to hospital",
                    "hyperglycemia; unstable glucose complicates recovery", 70, 140, " mg/dL"),
    "creatinine":  ("Creatinine", "low values usually reflect reduced muscle mass rather than better kidney function",
                    "impaired kidney function", 0.6, 1.3, " mg/dL"),
    "bun":         ("Blood urea nitrogen", "low values may reflect malnutrition or liver disease",
                    "dehydration, renal impairment or heart failure", 7, 20, " mg/dL"),
    "sodium":      ("Sodium", "hyponatremia, which reflects fluid overload and predicts instability",
                    "hypernatremia, usually reflecting dehydration", 135, 145, " mEq/L"),
    "potassium":   ("Potassium", "hypokalemia, which carries cardiac arrhythmia risk",
                    "hyperkalemia, which carries cardiac arrhythmia risk", 3.5, 5.1, " mEq/L"),
    "hemoglobin":  ("Hemoglobin", "anaemia or bleeding, both linked to readmission",
                    "polycythemia or haemoconcentration from dehydration", 12.0, 16.0, " g/dL"),
    "wbc":         ("White blood cell count", "immunosuppression, raising infection risk",
                    "ongoing infection or inflammation", 4.0, 11.0, " K/uL"),
    "platelets":   ("Platelet count", "thrombocytopenia, which raises bleeding risk",
                    "thrombocytosis, which raises clotting risk", 150, 400, " K/uL"),
    "albumin":     ("Albumin", "malnutrition and poor physiological reserve",
                    "haemoconcentration, usually from dehydration", 3.5, 5.0, " g/dL"),
    "bicarbonate": ("Bicarbonate", "metabolic acidosis",
                    "metabolic alkalosis or chronic CO2 retention", 22, 29, " mEq/L"),
    "inr":         ("INR", "below the expected range for a patient on anticoagulation",
                    "prolonged clotting time, which raises bleeding risk", 0.8, 1.2, ""),
}

_LAB_STATS = {
    "last": "last value before discharge",
    "min":  "lowest value during stay",
    "max":  "highest value during stay",
}

_LAB_COUNT_STAT = ("n_abn", "abnormal results during stay")

_CHARLSON_LABELS = {
    "myocardial_infarction":    "Prior myocardial infarction",
    "congestive_heart_failure": "Congestive heart failure",
    "peripheral_vascular":      "Peripheral vascular disease",
    "cerebrovascular":          "Cerebrovascular disease",
    "dementia":                 "Dementia",
    "chronic_pulmonary":        "Chronic pulmonary disease",
    "rheumatic":                "Rheumatic disease",
    "peptic_ulcer":             "Peptic ulcer disease",
    "mild_liver":               "Mild liver disease",
    "diabetes_uncomplicated":   "Diabetes without complications",
    "diabetes_complicated":     "Diabetes with organ damage",
    "hemiplegia":               "Hemiplegia or paraplegia",
    "renal_disease":            "Chronic kidney disease",
    "malignancy":               "Malignancy",
    "severe_liver":             "Severe liver disease",
    "metastatic_cancer":        "Metastatic solid tumour",
    "hiv_aids":                 "HIV / AIDS",
}

_CHARLSON_EXPLANATION = (
    "a Charlson comorbidity contributing to overall chronic disease burden"
)


# ---------------------------------------------------------------------------
# Value-aware explanations
# ---------------------------------------------------------------------------
# An explanation may be a plain string, or a callable taking the raw feature
# value and returning the string. Callables exist because a fixed sentence
# attached to a varying number produces statements that contradict the value
# shown next to them - e.g. "Patient age: 25 (advanced age reduces
# physiological reserve)". Explanations must not contain "(" : the driver
# string is rendered as "<label>: <value> (<explanation>)" and the API parses
# it back on the last " (".

def _as_float(raw):
    import pandas as pd

    if raw is None or (np.isscalar(raw) and pd.isna(raw)):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _fmt_num(v) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


def _lab_explainer(low_why, high_why, lo, hi, unit):
    band = f"{_fmt_num(lo)}-{_fmt_num(hi)}{unit}"

    def explain(raw):
        v = _as_float(raw)
        if v is None:
            return f"not recorded during this stay; normal range is {band}"
        if v < lo:
            return f"below the normal range of {band}, indicating {low_why}"
        if v > hi:
            return f"above the normal range of {band}, indicating {high_why}"
        return (f"within the normal range of {band}; the model weighted this "
                "value in combination with the patient's other factors")

    return explain


def _age_explain(raw):
    v = _as_float(raw)
    if v is None:
        return "age not recorded"
    if v >= 75:
        return "advanced age reduces physiological reserve and slows recovery"
    if v >= 65:
        return "older age is associated with slower recovery and more comorbidity"
    if v < 40:
        return ("a younger patient carrying this much risk usually reflects chronic "
                "disease or frequent use of care rather than age itself")
    return "middle age; weighted alongside the patient's other factors"


def _gap_explain(raw):
    """
    Explains days_since_prev: the gap between the patient's PREVIOUS discharge
    and the start of THIS admission. It is fixed when the admission opens and
    never changes afterwards.

    The wording deliberately avoids "since the last stay" and any phrasing that
    counts forward from a discharge. In the weekly monitoring cards this driver
    sits directly under a "7 days later" header, and the earlier wording read as
    "it has been 2 days since you were discharged" - a different quantity, and a
    contradiction of the header.
    """
    v = _as_float(raw)
    if v is None:
        return "no previous discharge on record"
    if v <= 30:
        return "this admission began soon after the previous discharge, which indicates unresolved illness"
    if v <= 90:
        return "the previous stay ended within three months of this admission"
    return ("the previous stay was well before this admission; the model weighted "
            "the fact of a prior admission rather than its recency")


def _los_explain(raw):
    v = _as_float(raw)
    if v is None:
        return "length of stay not recorded"
    if v <= 2:
        return "a short stay, which can leave problems unresolved at discharge"
    if v >= 8:
        return "a long stay reflects greater illness severity and complex recovery"
    return "a typical-length stay, weighted alongside the patient's other factors"


def _prior_adm_explain(raw):
    v = _as_float(raw)
    if v is None or v == 0:
        return "no prior admissions on record"
    if v <= 2:
        return "a small number of prior admissions raises baseline risk"
    return "repeat admissions signal ongoing clinical instability"

# feature -> (label, explanation, kind)
#   kind: "yesno" | "number" | "days" | "category"
_BASE_LABELS = {
    "anchor_age":       ("Patient age", _age_explain, "number"),
    "gender":           ("Gender", "demographic factor", "category"),
    "race":             ("Race", "demographic factor", "category"),
    "marital_status":   ("Marital status", "a proxy for available social support after discharge", "category"),
    "insurance":        ("Insurance", "a proxy for access to follow-up care", "category"),
    "admission_type":   ("Admission type", "emergency and urgent admissions indicate acute decompensation", "category"),

    "los_days":         ("Length of stay", _los_explain, "days"),
    "n_prior_adm":      ("Prior admissions on record", _prior_adm_explain, "number"),
    "prior_adm_flag":   ("Has prior admissions", "any prior admission raises baseline readmission risk", "yesno"),
    "days_since_prev":  ("Gap before this admission", _gap_explain, "days"),
    "readmit_history":  ("Readmitted within 30 days before", "prior rapid readmission is among the strongest predictors", "yesno"),
    "ed_visit":         ("Arrived via emergency department", "ED arrival indicates unplanned acute presentation", "yesno"),
    "ed_hours":         ("Hours spent in emergency department", "prolonged ED time reflects acuity and crowding", "number"),
    "is_emergency":     ("Emergency or urgent admission", "unplanned admission indicates acute decompensation", "yesno"),

    "charlson_score":   ("Comorbidity burden (Charlson)", "higher scores mean more chronic conditions and higher risk", "number"),
    "n_diagnoses":      ("Number of diagnoses recorded", "more coded diagnoses indicate greater clinical complexity", "number"),
    "drg_severity":     ("APR-DRG severity of illness", "graded 1-4; higher values indicate a sicker admission", "number"),
    "drg_mortality":    ("APR-DRG risk of mortality", "graded 1-4; higher values indicate greater mortality risk", "number"),
    "n_procedures":     ("Procedures during stay", "invasive procedures complicate recovery", "number"),

    "n_drug_orders":    ("Medication orders during stay", "high medication volume increases regimen complexity", "number"),
    "n_distinct_drugs": ("Distinct medications", "polypharmacy raises adherence burden and interaction risk", "number"),
    "med_insulin":      ("Insulin prescribed", "insulin requires careful titration; dosing error is a common readmission trigger", "yesno"),
    "med_anticoagulant":("Anticoagulant prescribed", "anticoagulation carries bleeding risk and needs monitoring", "yesno"),
    "med_opioid":       ("Opioid prescribed", "opioids carry sedation and dependency risk after discharge", "yesno"),
    "med_diuretic":     ("Diuretic prescribed", "diuretic therapy indicates fluid overload requiring follow-up", "yesno"),
    "med_antipsychotic":("Antipsychotic prescribed", "indicates behavioural health needs that complicate care plans", "yesno"),

    "disch_home":       ("Discharged home", "discharge home without support may leave needs unmet", "yesno"),
    "disch_snf":        ("Discharged to skilled nursing or rehab", "institutional discharge indicates inability to self-care", "yesno"),
    "disch_ama":        ("Left against medical advice", "incomplete treatment sharply raises readmission risk", "yesno"),
}


def _abnormal_count_explain(raw):
    v = _as_float(raw)
    if v is None:
        return "this test was not run during the stay"
    if v == 0:
        return "every result for this test was within the normal range"
    if v == 1:
        return "a single out-of-range result, weighted alongside the other factors"
    return "repeatedly out of range during the stay, indicating a persistent abnormality"


def _build_label_map() -> dict:
    m = dict(_BASE_LABELS)
    for feat, label in _CHARLSON_LABELS.items():
        m[feat] = (label, _CHARLSON_EXPLANATION, "yesno")

    for concept, (name, low_why, high_why, lo, hi, unit) in _LAB_CONCEPTS.items():
        # Comma, not parentheses: the driver string is rendered as
        # "<label>: <value> (<explanation>)" and a bracket inside the label
        # would collide with the explanation delimiter when parsed back.
        explain = _lab_explainer(low_why, high_why, lo, hi, unit)
        for stat, stat_text in _LAB_STATS.items():
            m[f"lab_{concept}_{stat}"] = (f"{name}, {stat_text}", explain, "number")

        # n_abn is a COUNT of out-of-range results, not a measurement, so the
        # reference-range explainer above would misread it - 0 abnormal results
        # is reassuring, but 0 mEq/L of sodium would read as critically low.
        count_stat, count_text = _LAB_COUNT_STAT
        m[f"lab_{concept}_{count_stat}"] = (
            f"{name}, {count_text}", _abnormal_count_explain, "number")
    return m


LABEL_MAP = _build_label_map()


def _format_value(raw, kind) -> str:
    # pd.isna covers None, float('nan'), np.float32 NaN and pd.NA alike;
    # isinstance(x, float) does NOT catch numpy scalar NaNs.
    import pandas as pd

    if raw is None or (np.isscalar(raw) and pd.isna(raw)):
        return "not recorded"
    if kind == "category":
        return str(raw)
    try:
        f = float(raw)
    except (TypeError, ValueError):
        return str(raw)
    if kind == "yesno":
        return "Yes" if f >= 0.5 else "No"
    if kind == "days":
        return f"{f:.0f} days"
    return str(int(f)) if f.is_integer() else f"{f:.1f}"


def format_driver(feature: str, value, label_map: dict = None) -> str:
    """
    Render one feature/value pair in the string format the dashboard parses.

    `label_map` lets a caller re-label features for a different context without
    mutating global state: post-discharge weekly monitoring re-reads
    `lab_*_last` as "most recent outpatient result", where the discharge-time
    wording "last value before discharge" would be plainly wrong.
    """
    label, explanation, kind = (label_map or LABEL_MAP).get(
        feature, (feature.replace("_", " ").capitalize(), "model input feature", "number")
    )
    # An explanation is either a fixed string or a callable that reads the value,
    # so that the sentence never contradicts the number printed beside it.
    if callable(explanation):
        explanation = explanation(value)
    return f"{label}: {_format_value(value, kind)} ({explanation})"


def top_drivers(shap_row, feature_names, feature_values, top_n=3,
                risk_increasing_only=True, label_map=None):
    """
    Turn one row of SHAP values into the top-N driver strings.

    Only features that pushed risk UP are reported by default: a clinician
    acting on a worklist needs the reasons a patient is flagged, not the
    protective factors offsetting them.
    """
    order = np.argsort(shap_row)[::-1]  # most risk-increasing first
    drivers = []
    for idx in order:
        if risk_increasing_only and shap_row[idx] <= 0:
            break
        drivers.append(format_driver(feature_names[idx], feature_values[idx], label_map))
        if len(drivers) == top_n:
            break

    while len(drivers) < top_n:
        drivers.append("No further risk-increasing factor identified.")
    return drivers


def post_discharge_label_map() -> dict:
    """
    LABEL_MAP re-worded for post-discharge weekly monitoring.

    Only the `lab_*_last` entries change meaning: during a stay that column is
    "last value before discharge", but in a weekly monitoring series it holds
    the most recent OUTPATIENT result. Every other feature is still a property
    of the index stay and keeps its wording.
    """
    m = dict(LABEL_MAP)
    for concept, (name, low_why, high_why, lo, hi, unit) in _LAB_CONCEPTS.items():
        key = f"lab_{concept}_last"
        if key in m:
            m[key] = (f"{name}, most recent outpatient result",
                      _lab_explainer(low_why, high_why, lo, hi, unit), "number")
    return m
