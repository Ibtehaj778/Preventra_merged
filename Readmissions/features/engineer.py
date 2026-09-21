"""
features/engineer.py
--------------------
Derives all remaining NeuroShield MVP features from the cleaned DataFrame.
Each function takes and returns a DataFrame, following the Feature
Implementation Map defined in Section 2.1 of the project plan.

Features implemented here:
  - ip_admissions_365d_prior      (rename)
  - ed_visits_90d_prior           (rename)
  - medication_count_at_discharge (rename)
  - length_of_stay_days           (rename)
  - medication_change_flag        (binary encode)
  - admission_acuity_flag         (binary encode)
  - high_utilizer_flag            (threshold logic)
  - high_risk_medication_flag     (insulin check)
  - complex_discharge_flag        (multi-condition)
  - behavioral_health_flag        (ICD-9 range check)
  - frailty_proxy                 (age bracket parse)
  - no_show_proxy                 (no-show proxy from diabetes data)
  - probabilistic_no_show         (no-show probability via transfer learning)

CCI is handled separately in features/cci.py.
"""

import re
import pandas as pd

# ICD-9 codes 291-319 cover mental/behavioural health disorders
_BH_LOW  = 291
_BH_HIGH = 319


# ---------------------------------------------------------------------------
# Individual feature functions
# ---------------------------------------------------------------------------

def add_ip_admissions(df: pd.DataFrame) -> pd.DataFrame:
    """Rename number_inpatient -> ip_admissions_365d_prior."""
    df["ip_admissions_365d_prior"] = df["number_inpatient"].astype(int)
    return df


def add_ed_visits(df: pd.DataFrame) -> pd.DataFrame:
    """Rename number_emergency -> ed_visits_90d_prior (proxy window)."""
    df["ed_visits_90d_prior"] = df["number_emergency"].astype(int)
    return df


def add_medication_count(df: pd.DataFrame) -> pd.DataFrame:
    """Rename num_medications -> medication_count_at_discharge."""
    df["medication_count_at_discharge"] = df["num_medications"].astype(int)
    return df


def add_length_of_stay(df: pd.DataFrame) -> pd.DataFrame:
    """Rename time_in_hospital -> length_of_stay_days."""
    df["length_of_stay_days"] = df["time_in_hospital"].astype(int)
    return df


def add_medication_change_flag(df: pd.DataFrame) -> pd.DataFrame:
    """
    medication_change_flag:
      'Ch' (medication changed during stay) -> 1
      'No' (no change)                      -> 0
    """
    df["medication_change_flag"] = (df["change"] == "Ch").astype(int)
    return df


def add_admission_acuity_flag(df: pd.DataFrame) -> pd.DataFrame:
    """
    admission_acuity_flag:
      admission_type_id in {1, 2} (Emergency / Urgent) -> 1
      all others                                         -> 0
    """
    df["admission_acuity_flag"] = df["admission_type_id"].astype(str).isin(["1", "2"]).astype(int)
    return df


def add_high_utilizer_flag(df: pd.DataFrame) -> pd.DataFrame:
    """
    high_utilizer_flag:
      1 if number_inpatient >= 2 OR number_emergency >= 2; else 0
    """
    df["high_utilizer_flag"] = (
        (df["number_inpatient"].astype(int) >= 2) |
        (df["number_emergency"].astype(int) >= 2)
    ).astype(int)
    return df


def add_high_risk_medication_flag(df: pd.DataFrame) -> pd.DataFrame:
    """
    high_risk_medication_flag:
      1 if insulin column is anything other than 'No'; else 0
      (Partial proxy — insulin is used as the high-risk drug representative)
    """
    df["high_risk_medication_flag"] = (df["insulin"] != "No").astype(int)
    return df


def add_complex_discharge_flag(df: pd.DataFrame) -> pd.DataFrame:
    """
    complex_discharge_flag:
      1 if LOS > 7 AND num_medications > 10 AND number_diagnoses > 7
      else 0
    """
    df["complex_discharge_flag"] = (
        (df["time_in_hospital"].astype(int) > 7) &
        (df["num_medications"].astype(int) > 10) &
        (df["number_diagnoses"].astype(int) > 7)
    ).astype(int)
    return df


def _has_behavioral_health_code(row: pd.Series) -> int:
    """
    Return 1 if any of diag_1, diag_2, diag_3 falls in ICD-9 range 291-319.
    """
    for col in ("diag_1", "diag_2", "diag_3"):
        code = str(row.get(col, "")).strip().split(".")[0]
        try:
            numeric = int(code)
            if _BH_LOW <= numeric <= _BH_HIGH:
                return 1
        except ValueError:
            continue
    return 0


def add_behavioral_health_flag(df: pd.DataFrame) -> pd.DataFrame:
    """
    behavioral_health_flag:
      1 if any diagnosis column contains an ICD-9 code in range 291-319
      (mental/behavioural health disorders); else 0
    """
    df["behavioral_health_flag"] = df.apply(_has_behavioral_health_code, axis=1)
    return df


def _parse_age_lower_bound(age_str: str) -> int:
    """
    Parse a bracket age string like '[70-80)' and return the lower bound (70).
    Returns 0 if parsing fails.
    """
    if not isinstance(age_str, str):
        return 0
    match = re.search(r"\[(\d+)", age_str)
    if match:
        return int(match.group(1))
    return 0


def add_frailty_proxy(df: pd.DataFrame) -> pd.DataFrame:
    """
    frailty_proxy:
      Parse lower bound of the age bracket string.
      1 if lower bound >= 75; else 0
      (Partial proxy for frailty using age as surrogate)
    """
    df["_age_lower"] = df["age"].apply(_parse_age_lower_bound)
    df["frailty_proxy"] = (df["_age_lower"] >= 75).astype(int)
    df.drop(columns=["_age_lower"], inplace=True)
    return df


def add_no_show_proxy(df: pd.DataFrame) -> pd.DataFrame:
    """
    no_show_proxy:
      Proxy for no-show behavior derived from diabetes dataset alone.
      Combines three indicators:
      1. Emergency-to-outpatient ratio (high ratio suggests skipped appointments)
      2. Low engagement flag (severe disease but barely any visits)
      3. Visit gap proxy (inpatient without prior outpatient follow-up)

      Returns a combined score normalized to [0,1] range.
    """
    # Make a copy to avoid warnings
    df = df.copy()

    # Check if required columns exist, if not create with defaults
    required_cols = ["number_emergency", "number_outpatient", "number_inpatient", "number_diagnoses"]
    for col in required_cols:
        if col not in df.columns:
            df[col] = 0

    # 1. Emergency-to-outpatient ratio (avoid division by zero)
    df["_eo_ratio"] = df["number_emergency"] / (df["number_outpatient"] + 1)

    # 2. Low engagement flag: high disease severity but low visits
    # Using number of diagnoses as proxy for severity, outpatient visits for engagement
    # Only compute if we have enough data for quantiles
    if len(df) > 1:
        diagnosis_threshold = df["number_diagnoses"].quantile(0.7)
        outpatient_threshold = df["number_outpatient"].quantile(0.3)
    else:
        # For single row or empty df, use median values as thresholds
        diagnosis_threshold = df["number_diagnoses"].median() if len(df) > 0 else 0
        outpatient_threshold = df["number_outpatient"].median() if len(df) > 0 else 0

    df["_low_engagement"] = (
        (df["number_diagnoses"] >= diagnosis_threshold) &  # High severity
        (df["number_outpatient"] <= outpatient_threshold)   # Low engagement
    ).astype(int)

    # 3. Visit gap proxy: inpatient visits without prior outpatient follow-up
    # If someone has inpatient visits but very low outpatient, suggests missed follow-ups
    df["_visit_gap"] = (
        (df["number_inpatient"] > 0) &
        (df["number_outpatient"] == 0)
    ).astype(int)

    # Combine indicators into a normalized score
    # Normalize eo_ratio to [0,1] using 95th percentile to avoid outliers
    if len(df) > 1:
        eo_ratio_95 = df["_eo_ratio"].quantile(0.95)
    else:
        eo_ratio_95 = df["_eo_ratio"].max() if len(df) > 0 else 0

    if eo_ratio_95 > 0:
        df["_eo_ratio_norm"] = df["_eo_ratio"].clip(0, eo_ratio_95) / eo_ratio_95
    else:
        df["_eo_ratio_norm"] = 0

    # Combine all three indicators (equally weighted)
    df["no_show_proxy"] = (
        df["_eo_ratio_norm"] * 0.4 +
        df["_low_engagement"] * 0.3 +
        df["_visit_gap"] * 0.3
    )

    # Clean up temporary columns
    df.drop(columns=["_eo_ratio", "_eo_ratio_norm", "_low_engagement", "_visit_gap"], inplace=True)

    return df


def add_probabilistic_no_show(df: pd.DataFrame) -> pd.DataFrame:
    """
    probabilistic_no_show:
      No-show probability via transfer learning from noshow dataset.

      Steps:
      1. Load noshow dataset and identify shared features with diabetes dataset
      2. Train a logistic regression model on noshow data using only shared features
      3. Apply the trained model to diabetes dataset (shared features only)
      4. Output no-show probability scores [0,1]

      Shared features: age, gender, diabetes, hypertension
    """
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import LabelEncoder, StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score
    from sklearn.metrics import classification_report
    from collections import Counter



    # Load noshow dataset
    noshow_path = "data/reference/noshow.csv"
    try:
        noshow_df = pd.read_csv(noshow_path)
    except FileNotFoundError:
        # If noshow dataset not found, return zeros
        df["probabilistic_no_show"] = 0.0
        return df

    # Prepare shared features
    # Shared features between datasets: age, gender, diabetes, hypertension

    # Process noshow dataset
    noshow_processed = noshow_df.copy()

    # Encode gender: F->0, M->1 (consistent with common encoding)
    noshow_processed["gender_encoded"] = noshow_processed["Gender"].map({"F": 0, "M": 1})
    # Handle any unexpected values
    noshow_processed["gender_encoded"] = noshow_processed["gender_encoded"].fillna(0)

    # Use existing diabetes and hypertension columns (0/1 encoded)
    noshow_processed["diabetes"] = noshow_processed["Diabetes"]
    noshow_processed["hypertension"] = noshow_processed["Hipertension"]

    # Age is already numeric
    noshow_processed["age"] = noshow_processed["Age"]

    # Target: No-show (Yes->1, No->0)
    noshow_processed["no_show"] = (noshow_processed["No-show"] == "Yes").astype(int)

    # Select features for training
    feature_cols = ["age", "gender_encoded", "diabetes", "hypertension"]
    X_noshow = noshow_processed[feature_cols]
    y_noshow = noshow_processed["no_show"]

    # Process diabetes dataset similarly
    df_processed = df.copy()

    # Check if required columns exist, if not create with defaults
    required_cols = ["gender", "diag_1", "diag_2", "diag_3", "age"]
    for col in required_cols:
        if col not in df_processed.columns:
            if col == "gender":
                df_processed[col] = "Female"  # default
            elif col.startswith("diag_"):
                df_processed[col] = "0"  # default
            elif col == "age":
                df_processed[col] = "[40-50)"  # default

    # Encode gender: Female->0, Male->1 (map from diabetic_data values)
    gender_mapping = {"Female": 0, "Male": 1}
    df_processed["gender_encoded"] = df_processed["gender"].map(gender_mapping)
    # Handle any unexpected values
    df_processed["gender_encoded"] = df_processed["gender_encoded"].fillna(0)

    # For diabetes and hypertension, we need to extract from diagnosis columns
    # Since diabetic_data doesn't have explicit columns, we'll check diagnosis columns
    def has_condition(diag_str, condition_keywords):
        """Check if any diagnosis contains condition keywords"""
        if pd.isna(diag_str):
            return 0
        diag_str = str(diag_str).upper()
        return any(keyword in diag_str for keyword in condition_keywords)

    # Diabetes keywords: 250.xx range in ICD-9
    df_processed["diabetes"] = (
        df_processed["diag_1"].apply(lambda x: has_condition(x, ["250"])) |
        df_processed["diag_2"].apply(lambda x: has_condition(x, ["250"])) |
        df_processed["diag_3"].apply(lambda x: has_condition(x, ["250"]))
    ).astype(int)

    # Hypertension keywords: 401-405 range in ICD-9
    df_processed["hypertension"] = (
        df_processed["diag_1"].apply(lambda x: has_condition(x, ["401", "402", "403", "404", "405"])) |
        df_processed["diag_2"].apply(lambda x: has_condition(x, ["401", "402", "403", "404", "405"])) |
        df_processed["diag_3"].apply(lambda x: has_condition(x, ["401", "402", "403", "404", "405"]))
    ).astype(int)

    # Age: parse from bracket format to numeric (use lower bound)
    df_processed["age"] = df_processed["age"].apply(_parse_age_lower_bound)

    # Select features for prediction
    X_diabetes = df_processed[feature_cols]

    # Handle missing values
    X_noshow = X_noshow.fillna(0)
    X_diabetes = X_diabetes.fillna(0)

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X_noshow, y_noshow, test_size=0.2, random_state=42, stratify=y_noshow
    )

    # Scale
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    X_diabetes_scaled = scaler.transform(X_diabetes)

    # Train model
    model = LogisticRegression(
        random_state=42,
        max_iter=1000,
        class_weight="balanced"
    )
    model.fit(X_train_scaled, y_train)

    # Predictions
    y_train_pred = model.predict(X_train_scaled)
    y_test_pred = model.predict(X_test_scaled)

    # Accuracy
    train_acc = accuracy_score(y_train, y_train_pred)
    test_acc = accuracy_score(y_test, y_test_pred)

    # print(Counter(y_noshow))
    # print(f"[model] Logistic Regression Train Accuracy: {train_acc:.4f}")
    # print(f"[model] Logistic Regression Test Accuracy: {test_acc:.4f}\n")
    # print(classification_report(y_test, y_test_pred))
    # Final probabilities for your dataset
    df["probabilistic_no_show"] = model.predict_proba(X_diabetes_scaled)[:, 1]
    return df


def encode_and_drop_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    One-hot encode categorical columns, binary encode diabetesMed,
    and drop raw medication columns.
    """
    cols_to_encode = ['race', 'gender', 'max_glu_serum', 'A1Cresult']
    existing_cols = [c for c in cols_to_encode if c in df.columns]
    if existing_cols:
        df = pd.get_dummies(df, columns=existing_cols, dtype=int)
    
    if "diabetesMed" in df.columns:
        df["diabetesMed"] = df["diabetesMed"].map({"Yes": 1, "No": 0}).fillna(0).astype(int)
        
    med_cols = [
        'metformin', 'repaglinide', 'nateglinide', 'chlorpropamide',
        'glimepiride', 'acetohexamide', 'glipizide', 'glyburide',
        'tolbutamide', 'pioglitazone', 'rosiglitazone', 'acarbose',
        'miglitol', 'troglitazone', 'tolazamide', 'examide', 'citoglipton',
        'insulin', 'glyburide-metformin', 'glipizide-metformin',
        'glimepiride-pioglitazone', 'metformin-rosiglitazone',
        'metformin-pioglitazone'
    ]
    cols_to_drop = [c for c in med_cols if c in df.columns]
    if cols_to_drop:
        df.drop(columns=cols_to_drop, inplace=True)
    
    return df


# ---------------------------------------------------------------------------
# Master function: apply all feature engineering steps in order
# ---------------------------------------------------------------------------

FEATURE_PIPELINE = [
    add_ip_admissions,
    add_ed_visits,
    add_medication_count,
    add_length_of_stay,
    add_medication_change_flag,
    add_admission_acuity_flag,
    add_high_utilizer_flag,
    add_high_risk_medication_flag,
    add_complex_discharge_flag,
    add_behavioral_health_flag,
    add_frailty_proxy,
    add_no_show_proxy,
    add_probabilistic_no_show,
    encode_and_drop_features,
]


def run_feature_pipeline(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply every feature engineering step in sequence.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned DataFrame with label already attached.

    Returns
    -------
    pd.DataFrame
        DataFrame with all derived feature columns added.
    """
    for fn in FEATURE_PIPELINE:
        df = fn(df)
        print(f"[engineer] Applied: {fn.__name__}")
    return df


if __name__ == "__main__":
    from features.clean import load_and_clean
    from features.label import add_label
    from features.cci import add_cci_feature

    df = load_and_clean()
    df = add_label(df)
    df = add_cci_feature(df)
    df = run_feature_pipeline(df)
    print(df.head(2))