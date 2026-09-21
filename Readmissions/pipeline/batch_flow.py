import os
import sys
import json
from pathlib import Path
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
from pymongo import DESCENDING

load_dotenv()

from prefect import flow, task, get_run_logger

# Ensure root paths are in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.db_utils import get_mongo_client

# ---------------------------------------------------------------------------
# MongoDB connection
# ---------------------------------------------------------------------------
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
_mongo_client = get_mongo_client(MONGO_URI)
_db = _mongo_client["neuroshield"]

from features.clean import load_and_clean
from features.label import add_balanced_label_with_importance
from features.cci import add_cci_feature
from features.engineer import run_feature_pipeline
from models.driver_extractor import load_model, extract_drivers_for_batch
import models.shap_utils as shap_utils

# Fields captured per-patient so a care provider can later reopen and edit
# this encounter (see api/main.py ManualPatientInput for the same shape).
RAW_INPUT_DEFAULTS = {
    "age": "[60-70)",
    "gender": "Female",
    "race": "Caucasian",
    "number_inpatient": 0,
    "number_emergency": 0,
    "num_medications": 10,
    "time_in_hospital": 3,
    "change": "No",
    "admission_type_id": 1,
    "insulin": "No",
    "A1Cresult": "None",
    "number_diagnoses": 5,
    "discharge_disposition_id": 1,
    "diabetesMed": "No",
    "max_glu_serum": "None",
}


def _extract_raw_inputs(raw_df: pd.DataFrame) -> list:
    records = []
    for _, row in raw_df.iterrows():
        record = {}
        for field, default in RAW_INPUT_DEFAULTS.items():
            val = row.get(field, default)
            if pd.isna(val):
                val = default
            record[field] = val
        records.append(record)
    return records


@task(name="1. Detect New Discharge CSV")
def detect_new_discharge_csv(input_dir: str) -> Path:
    logger = get_run_logger()
    logger.info(f"Scanning for new discharge CSVs in {input_dir}")
    
    input_path = Path(input_dir)
    input_path.mkdir(parents=True, exist_ok=True)
    
    csv_files = list(input_path.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {input_dir}")
        
    latest_file = max(csv_files, key=os.path.getmtime)
    logger.info(f"Detected batch file: {latest_file}")
    return latest_file

@task(name="2. Run Feature Engineering")
def run_feature_engineering_task(csv_path: Path):
    logger = get_run_logger()
    logger.info("Running feature engineering pipeline")
    
    df = load_and_clean(csv_path=str(csv_path))
    
    # Mock readmitted if missing to satisfy label functions logic
    if "readmitted" not in df.columns:
        df["readmitted"] = "NO"
        
    df = add_balanced_label_with_importance(df)
    df = add_cci_feature(df)
    df = run_feature_pipeline(df)
    
    # Extract identifiers directly from the raw batch file
    raw_df = pd.read_csv(csv_path)
    if 'patient_id' in raw_df.columns:
        patient_ids = raw_df['patient_id']
    elif 'patient_nbr' in raw_df.columns:
        patient_ids = raw_df['patient_nbr']
    else:
        patient_ids = pd.Series(range(len(raw_df)))
        
    if 'discharge_date' in raw_df.columns:
        discharge_dates = raw_df['discharge_date']
    else:
        discharge_dates = pd.Series([datetime.today().strftime('%Y-%m-%d')] * len(raw_df))

    raw_inputs = _extract_raw_inputs(raw_df)

    return df, patient_ids, discharge_dates, raw_inputs

@task(name="3. Load MLflow Model")
def load_mlflow_model(model_name: str):
    logger = get_run_logger()
    logger.info(f"Loading MLflow model: {model_name}")
    model = load_model(model_name=model_name)
    return model

@task(name="4. Score All Patients")
def score_all_patients(model, df: pd.DataFrame):
    logger = get_run_logger()
    logger.info("Computing predict_proba risk scores")
    
    feature_cols = model.feature_names_in_.tolist()
    missing_cols = [c for c in feature_cols if c not in df.columns]
    if missing_cols:
        logger.warning(f"Missing required model features: {missing_cols}. Imputing 0.")
        for c in missing_cols:
            df[c] = 0
            
    X = df[feature_cols]
    
    y_probs = model.predict_proba(X)[:, 1]
    risk_scores = (y_probs * 100).round(1)
    
    thresholds_path = Path("docs/diabetic/band_thresholds_balanced_importance.json")
    if thresholds_path.exists():
        with open(thresholds_path) as f:
            thresholds = json.load(f)
    else:
        logger.warning("Thresholds JSON not found, using defaults.")
        thresholds = {"high_score_threshold": 22.0, "low_score_threshold": 11.0}
        
    def get_risk_band(score, th):
        if score >= th.get("high_score_threshold", 22.0):
            return "High"
        elif score >= th.get("low_score_threshold", 11.0):
            return "Medium"
        else:
            return "Low"
            
    risk_bands = [get_risk_band(s, thresholds) for s in risk_scores]
    return X, risk_scores, risk_bands

@task(name="5. Extract Top-3 Drivers")
def extract_top_3_drivers(model, X: pd.DataFrame, model_name: str):
    logger = get_run_logger()
    logger.info("Extracting Top-3 drivers for every patient")
    
    feature_cols = model.feature_names_in_.tolist()
    if "xgb" in model_name.lower():
        explainer = shap_utils.build_shap_explainer(model)
        shap_vals = shap_utils.compute_shap_values(explainer, X)
        all_drivers = []
        for i in range(len(X)):
            row_vals = shap_vals[i]
            top_drivers = shap_utils.get_top_3_drivers(row_vals, feature_cols)
            human_text = shap_utils.format_human_readable_drivers(top_drivers)
            while len(human_text) < 3:
                human_text.append("No further drivers found")
            all_drivers.append({
                "driver_1": human_text[0],
                "driver_2": human_text[1],
                "driver_3": human_text[2]
            })
        drivers_df = pd.DataFrame(all_drivers)
    else:
        drivers_df = extract_drivers_for_batch(model=model, feature_names=feature_cols, X=X, n_drivers=3)
        
    return drivers_df

@task(name="6. Write Worklist and Summary")
def write_worklist_and_summary(patient_ids, risk_scores, risk_bands, discharge_dates, drivers_df, registry_csv: str, raw_inputs=None):
    logger = get_run_logger()
    logger.info("Writing Worklist and Executive Summary to MongoDB")

    worklist_df = pd.DataFrame({
        'patient_id': patient_ids,
        'risk_score': risk_scores,
        'risk_band': risk_bands,
        'discharge_date': discharge_dates,
        'raw_inputs': raw_inputs if raw_inputs is not None else [{}] * len(patient_ids),
    }).reset_index(drop=True)

    drivers_df = drivers_df.reset_index(drop=True)
    worklist_df = pd.concat([worklist_df, drivers_df], axis=1)

    final_columns = ['patient_id', 'risk_score', 'risk_band', 'driver_1', 'driver_2', 'driver_3', 'discharge_date', 'raw_inputs']
    worklist_df = worklist_df[final_columns]
    worklist_df = worklist_df.sort_values(by='risk_score', ascending=False)

    today_str = datetime.today().strftime('%Y-%m-%d')
    worklist_df['batch_date'] = today_str
    # Store as string so lookups by patient_id (a str path param in the API) match
    # regardless of whether the source CSV had numeric or string IDs.
    worklist_df['patient_id'] = worklist_df['patient_id'].astype(str)

    # Write patient worklist to MongoDB (replace this batch's records)
    patient_col = _db["patient_worklist"]
    patient_col.delete_many({"batch_date": today_str})
    records = worklist_df.to_dict(orient='records')
    for r in records:
        r['risk_score'] = float(r['risk_score'])
    patient_col.insert_many(records)
    logger.info(f"Worklist written to MongoDB patient_worklist collection ({len(records)} patients)")

    total_scored = len(worklist_df)
    counts = worklist_df['risk_band'].value_counts()
    high_count = int(counts.get('High', 0))
    medium_count = int(counts.get('Medium', 0))
    low_count = int(counts.get('Low', 0))
    pct_high = round((high_count / total_scored * 100), 2) if total_scored > 0 else 0.0

    # WoW change from MongoDB risk_registry
    wow_change = "N/A"
    try:
        registry_col = _db["risk_registry"]
        prev_doc = registry_col.find_one(
            {"batch_date": {"$lt": today_str}},
            sort=[("batch_date", DESCENDING)]
        )
        if prev_doc:
            prev_date = prev_doc["batch_date"]
            prev_high_count = registry_col.count_documents({"batch_date": prev_date, "risk_band": "High"})
            delta = high_count - prev_high_count
            wow_change = f"+{delta}" if delta > 0 else str(delta)
    except Exception as e:
        logger.warning(f"Could not compute WoW Change: {e}")

    # Write executive summary to MongoDB
    summary_doc = {
        "batch_date": today_str,
        "total_patients": total_scored,
        "high_count": high_count,
        "medium_count": medium_count,
        "low_count": low_count,
        "pct_high": pct_high,
        "wow_change": wow_change,
    }
    summary_col = _db["executive_summary"]
    summary_col.replace_one({"batch_date": today_str}, summary_doc, upsert=True)
    logger.info(f"Executive Summary written to MongoDB executive_summary collection")

    return worklist_df

@task(name="7. Append to Risk Registry")
def append_to_risk_registry(worklist_df: pd.DataFrame, model_name: str, registry_csv: str):
    logger = get_run_logger()
    logger.info("Appending to immutable Risk Registry in MongoDB")

    today_str = datetime.today().strftime('%Y-%m-%d')
    worklist_df = worklist_df.copy()
    worklist_df["model_version"] = model_name
    worklist_df["batch_date"] = today_str

    registry_cols = [
        "patient_id", "risk_score", "risk_band",
        "driver_1", "driver_2", "driver_3",
        "model_version", "batch_date"
    ]
    registry_df = worklist_df[registry_cols]

    records = registry_df.to_dict(orient='records')
    for r in records:
        r['risk_score'] = float(r['risk_score'])

    registry_col = _db["risk_registry"]
    # Remove any existing records for this batch_date to avoid duplicates on re-runs
    registry_col.delete_many({"batch_date": today_str})
    registry_col.insert_many(records)
    logger.info(f"Successfully appended {len(records)} rows to MongoDB risk_registry collection")

@flow(name="Daily Patient Risk Pipeline", log_prints=True)
def run_batch_pipeline(
    model_name="readmission-dt-balanced-importance",
    input_dir="data/input",
    registry_csv="data/runtime/risk_registry.csv",  # kept for backward compatibility, no longer used as a file path
):
    logger = get_run_logger()
    logger.info("Starting Daily Patient Risk Pipeline")
    
    # 1. Detect new discharge CSV
    csv_path = detect_new_discharge_csv(input_dir=input_dir)
    
    # 2. Run feature engineering
    df, patient_ids, discharge_dates, raw_inputs = run_feature_engineering_task(csv_path)

    # 3. Load MLflow model
    model = load_mlflow_model(model_name=model_name)

    # 4. Score patients
    X, risk_scores, risk_bands = score_all_patients(model, df)

    # 5. Extract Top-3 Drivers
    drivers_df = extract_top_3_drivers(model, X, model_name=model_name)

    # 6. Write Worklist and Summary
    worklist_df = write_worklist_and_summary(
        patient_ids, risk_scores, risk_bands, discharge_dates, drivers_df,
        registry_csv=registry_csv, raw_inputs=raw_inputs,
    )
    
    # 7. Append to Risk Registry
    append_to_risk_registry(
        worklist_df, model_name=model_name, registry_csv=registry_csv
    )
    
    logger.info("Daily Patient Risk Pipeline completed successfully.")

if __name__ == "__main__":
    run_batch_pipeline()
