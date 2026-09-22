#!/usr/bin/env python3
"""
Load MIMIC-IV-scored patients into MongoDB in the schema the Preventra
dashboard already reads.

Writes three collections:
  patient_worklist   one row per patient - their most recent admission
  risk_registry      EVERY admission, giving a real per-admission score series
  executive_summary  band counts per batch_date

Two things worth knowing about the data handling:

DATES. MIMIC-IV shifts every patient's dates ~100 years into the future for
de-identification (this extract runs 2105-2214), which would look broken in the
UI. The Phase 1 notebook now exports `phase1_timeline.parquet` carrying real,
DE-SHIFTED admit/discharge timestamps, recovered using each patient's
`anchor_year_group` - the true 3-year range their shifted `anchor_year`
corresponds to. This loader reads those dates directly, joined on hadm_id.

That is a genuine recovery, not the invention it replaces: an earlier version of
this script had no timestamps at all and rebuilt a plausible calendar from
interval columns at a random per-patient offset. Measured on the export, the
de-shift preserves every within-patient interval to 0.0 seconds and puts 99.25%
of admissions inside the real 2008-2022 collection window.

Honesty bound: anchor_year_group resolves only to a 3-year bucket, so a
recovered date is the right year +/- ~1.5 and the day-of-year is still the
shifted one. Treat it as a real date to within a year, not an exact calendar
fact about a patient.

DIAGNOSES. `phase1_diagnoses.parquet` carries the principal ICD diagnosis
(seq_num == 1) and up to three secondaries per admission, titles already
resolved. 100% of admissions in the export have a principal diagnosis and no
code went unmapped.

DRIVERS. Per-patient attribution uses SHAP against the inner
HistGradientBoosting estimator. shap's support for that estimator is
approximate (~8% additivity error against the model margin, and top-3 driver
agreement of 2.45/3 versus interventional SHAP), so these are indicative
explanations rather than exact Shapley values. They are still a large
improvement on the previous engine, which cannot run on this model at all.

Usage
-----
    python scripts/load_mimic_to_mongo.py --limit 2000 --dry-run
    python scripts/load_mimic_to_mongo.py --limit 2000
    python scripts/load_mimic_to_mongo.py --limit 0        # everything
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.icd_groups import classify as classify_group  # noqa: E402
from models.icd_groups import classify_all as classify_group_all  # noqa: E402
from models.mimic_drivers import (inner_estimator, load_bundle,  # noqa: E402
                                  preprocess_for_shap, top_drivers)

_RESULTS = "data/mimic/model/results"
DEFAULT_BUNDLE = f"{_RESULTS}/phase1_model.joblib"
DEFAULT_MATRIX = f"{_RESULTS}/phase1_matrix.parquet"
DEFAULT_TIMELINE = f"{_RESULTS}/phase1_timeline.parquet"
DEFAULT_DIAGNOSES = f"{_RESULTS}/phase1_diagnoses.parquet"
THRESHOLDS_OUT = "docs/mimic/band_thresholds_mimic.json"
MODEL_VERSION = "mimic-hgb-calibrated-v1"

# Real MIMIC-IV collection window. The de-identified dates in the source sit at
# 2110-2201; rebuilt timelines are placed in here so the UI shows a plausible
# calendar. The widest single patient history in the matrix is ~5,355 days and
# the window is 5,478, so every patient fits.
WINDOW_START = datetime(2008, 1, 1)
WINDOW_END = datetime(2022, 12, 31)


# ---------------------------------------------------------------------------
# Timeline reconstruction
# ---------------------------------------------------------------------------

def attach_real_dates(df: pd.DataFrame, timeline_path: str) -> pd.DataFrame:
    """
    Join the de-shifted admit/discharge dates exported by the Phase 1 notebook.

    Joined on hadm_id, which the matrix now carries. `admit_real`/`disch_real`
    are the recovered calendar dates; the raw `admittime`/`dischtime` in the
    same file are the 22nd-century de-identified originals and are deliberately
    not used.

    Rows with no timeline match keep NaT and are reported rather than silently
    filled - a fabricated date is worse than a visibly missing one.
    """
    tl = pd.read_parquet(timeline_path,
                         columns=["hadm_id", "admit_real", "disch_real", "shift_years"])
    before = len(df)
    df = df.merge(tl, on="hadm_id", how="left")
    assert len(df) == before, "timeline join duplicated rows - hadm_id is not unique"

    missing = int(df.disch_real.isna().sum())
    if missing:
        print(f"  warning: {missing:,} admissions have no timeline row and no date")

    df["admit_dt"] = df["admit_real"]
    df["discharge_dt"] = df["disch_real"]
    df["admit_date"] = df.admit_dt.dt.strftime("%Y-%m-%d")
    df["discharge_date"] = df.discharge_dt.dt.strftime("%Y-%m-%d")
    df["batch_date"] = df.discharge_date
    return df


def attach_diagnoses(df: pd.DataFrame, diagnoses_path: str) -> pd.DataFrame:
    """
    Join the principal + secondary ICD diagnoses exported by the Phase 1
    notebook, so a risk score can be shown beside the condition it belongs to.

    An admission with no diagnosis row keeps an explicit "not coded" string
    rather than an empty cell, which on a clinical screen reads as "nothing
    wrong" instead of "nothing recorded".
    """
    dx = pd.read_parquet(diagnoses_path)
    before = len(df)
    df = df.merge(dx, on="hadm_id", how="left")
    assert len(df) == before, "diagnosis join duplicated rows - hadm_id is not unique"

    matched = df.primary_diagnosis.notna().mean()
    print(f"  diagnoses matched: {matched:.2%} of admissions")

    df["primary_diagnosis"] = df.primary_diagnosis.fillna("Diagnosis not coded")
    df["primary_icd_code"] = df.primary_icd_code.fillna("")
    df["secondary_diagnoses"] = df.secondary_diagnoses.apply(
        lambda v: list(v) if isinstance(v, (list, np.ndarray)) else [])
    df["n_diagnoses_coded"] = df.n_diagnoses_coded.fillna(0).astype(int)
    return df


# ---------------------------------------------------------------------------
# Bands
# ---------------------------------------------------------------------------

# Bands are FIXED, not derived from the score distribution.
#
# They used to be: High was the model's 60%-recall operating point and Medium
# the median predicted risk. That is defensible statistically and unusable in
# practice - the numbers were 22.43% and 16.51%, they meant nothing to anyone
# reading the screen, and they moved every time the model was retrained, so a
# patient could change band without anything about them changing.
LOW_BAND_FLOOR = 20.0
HIGH_BAND_FLOOR = 40.0


def compute_bands(scores: np.ndarray, high_cut: float) -> dict:
    """Fixed product bands. `scores` and `high_cut` are ignored by design."""
    return {
        "high_score_threshold": HIGH_BAND_FLOOR,
        "low_score_threshold": LOW_BAND_FLOOR,
        "source": "fixed product bands",
        "note": ("Low below 20%, Medium 20% to under 40%, High 40% and above. "
                 "Round, explainable numbers that do not move when the model "
                 "is retrained."),
    }


def band_of(score_pct: float, t: dict) -> str:
    if score_pct >= t["high_score_threshold"]:
        return "High"
    if score_pct >= t["low_score_threshold"]:
        return "Medium"
    return "Low"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", default=DEFAULT_BUNDLE)
    ap.add_argument("--matrix", default=DEFAULT_MATRIX)
    ap.add_argument("--timeline", default=DEFAULT_TIMELINE)
    ap.add_argument("--diagnoses", default=DEFAULT_DIAGNOSES)
    ap.add_argument("--limit", type=int, default=2000,
                    help="number of PATIENTS to load (0 = all)")
    ap.add_argument("--preserve-existing", action="store_true",
                    help="keep every patient already in patient_worklist and top up "
                         "to --limit with new ones. Without this a larger --limit "
                         "draws a fresh sample, which would orphan any patient "
                         "account linked to a patient_id that fell out.")
    ap.add_argument("--dry-run", action="store_true",
                    help="compute everything, print a preview, write nothing to Mongo")
    ap.add_argument("--shap-batch", type=int, default=20000)
    a = ap.parse_args()

    print("=" * 74)
    print("LOADING MODEL AND MATRIX")
    print("=" * 74)
    b = load_bundle(a.bundle)
    model, FEATURES = b["model"], b["features"]
    hgb = inner_estimator(model)
    threshold = float(b["threshold"])
    print(f"  model      : {type(model).__name__} -> {type(hgb).__name__}")
    print(f"  features   : {len(FEATURES)}   operating threshold: {threshold:.4f}")

    M = pd.read_parquet(a.matrix)
    print(f"  matrix     : {len(M):,} admissions, {M.subject_id.nunique():,} patients")

    if a.limit:
        existing = set()
        if a.preserve_existing:
            load_dotenv()
            from api.db_utils import get_db_name, get_mongo_client
            _db = get_mongo_client(os.environ.get("MONGO_URI", "mongodb://localhost:27017"))[get_db_name()]
            existing = {int(str(d["patient_id"]).replace("MIMIC-", ""))
                        for d in _db["patient_worklist"].find(
                            {"source": "mimic"}, {"_id": 0, "patient_id": 1})
                        if str(d.get("patient_id", "")).startswith("MIMIC-")}
            print(f"  existing   : {len(existing):,} patients already loaded, kept")

        pool = M.subject_id.drop_duplicates()
        existing = existing & set(pool)
        need = max(a.limit - len(existing), 0)
        extra = (pool[~pool.isin(existing)]
                 .sample(min(need, (~pool.isin(existing)).sum()), random_state=42))
        keep = existing | set(extra)
        M = M[M.subject_id.isin(keep)].copy()
        print(f"  subset     : {len(M):,} admissions, {M.subject_id.nunique():,} patients"
              + (f"  ({len(extra):,} newly added)" if a.preserve_existing else ""))

    # --- score ------------------------------------------------------------
    print("\nscoring ...")
    proba = model.predict_proba(M[FEATURES])[:, 1]
    M["risk_score"] = np.round(proba * 100, 1)

    thresholds = compute_bands(proba, threshold)
    M["risk_band"] = [band_of(s, thresholds) for s in M.risk_score]
    print(f"  bands      : High>={thresholds['high_score_threshold']}%  "
          f"Medium>={thresholds['low_score_threshold']}%")
    print("  " + M.risk_band.value_counts().to_dict().__str__())

    # --- drivers ----------------------------------------------------------
    print("\ncomputing SHAP drivers ...")
    import shap
    explainer = shap.TreeExplainer(hgb)
    d1, d2, d3 = [], [], []
    for start in range(0, len(M), a.shap_batch):
        chunk = M.iloc[start:start + a.shap_batch]
        Xt, names = preprocess_for_shap(hgb, chunk[FEATURES], FEATURES)
        sv = np.array(explainer.shap_values(Xt))
        # display the RAW values (category labels, not ordinal codes), aligned
        # to the reordered SHAP column names
        raw = chunk[FEATURES].reindex(columns=names)
        for i in range(len(chunk)):
            a1, a2, a3 = top_drivers(sv[i], names, raw.iloc[i].values, top_n=3)
            d1.append(a1); d2.append(a2); d3.append(a3)
        print(f"    {min(start + a.shap_batch, len(M)):>7,} / {len(M):,}")
    M["driver_1"], M["driver_2"], M["driver_3"] = d1, d2, d3

    # --- real dates + diagnoses -------------------------------------------
    print("\nattaching de-shifted dates ...")
    M = attach_real_dates(M, a.timeline)
    print(f"  admit dates     span {M.admit_date.min()} -> {M.admit_date.max()}")
    print(f"  discharge dates span {M.discharge_date.min()} -> {M.discharge_date.max()}")

    print("\nattaching diagnoses ...")
    M = attach_diagnoses(M, a.diagnoses)

    M["patient_id"] = "MIMIC-" + M.subject_id.astype(str)

    # --- shape the documents ---------------------------------------------
    # admit_date/discharge_date are the clinical dates; batch_date stays the
    # per-admission key the trend series is ordered by.
    registry_docs = M[["patient_id", "risk_score", "risk_band",
                       "driver_1", "driver_2", "driver_3", "batch_date",
                       "admit_date", "discharge_date",
                       "primary_diagnosis", "primary_icd_code",
                       "n_diagnoses_coded"]].copy()
    # astype(float) before rounding: los_days is float32 in the matrix, and
    # rounding it in float32 still serialises as 9.199999809265137 in BSON.
    registry_docs["los_days"] = (M["los_days"].astype(float)
                                 .fillna(1.0).clip(lower=0).round(1))
    registry_docs["n_prior_adm"] = M["n_prior_adm"].fillna(0).astype(int)
    registry_docs["model_version"] = MODEL_VERSION
    registry_docs = registry_docs.to_dict("records")

    latest = (M.sort_values(["subject_id", "n_prior_adm"])
                .groupby("subject_id", as_index=False).tail(1).copy())

    # The worklist batch_date is an OPERATIONAL field: get_latest_batch_date()
    # scopes the dashboard to the newest one, so it stays the run date rather
    # than a clinical date. The 2008-2022 dates the UI shows are
    # admit_date/discharge_date.
    worklist_batch = datetime.now().strftime("%Y-%m-%d")
    worklist_docs = []
    for _, r in latest.iterrows():
        # Resolved once, at load time, so the dashboard can filter by condition
        # with an indexed equality match instead of classifying 4,000 rows on
        # every request.
        grp = classify_group(r.primary_icd_code, r.primary_diagnosis,
                             list(r.secondary_diagnoses))
        # Every condition the patient has, not just the one they are monitored
        # under. The dashboard filters on this, so someone with heart failure
        # AND diabetes appears under both rather than only the higher priority
        # one. classify_all[0] is the same pick classify() makes.
        matches = classify_group_all(r.primary_icd_code, r.primary_diagnosis,
                                     list(r.secondary_diagnoses))
        worklist_docs.append({
            "patient_id": r.patient_id,
            "batch_date": worklist_batch,
            "risk_score": float(r.risk_score),
            "risk_band": r.risk_band,
            "admit_date": r.admit_date,
            "discharge_date": r.discharge_date,
            "los_days": round(float(r.los_days), 1) if pd.notna(r.los_days) else None,
            "n_prior_adm": int(r.n_prior_adm) if pd.notna(r.n_prior_adm) else 0,
            "driver_1": r.driver_1, "driver_2": r.driver_2, "driver_3": r.driver_3,
            "primary_diagnosis": r.primary_diagnosis,
            "primary_icd_code": r.primary_icd_code,
            "secondary_diagnoses": list(r.secondary_diagnoses),
            "n_diagnoses_coded": int(r.n_diagnoses_coded),
            "clinical_group": grp["group"],
            "clinical_groups": [m["group"] for m in matches] or ["general"],
            "group_matches": matches,
            "group_label": grp["label"],
            "group_evidence": grp["evidence"],
            "group_confidence": grp["confidence"],
            "source": "mimic",
            "raw_inputs": {},
        })

    counts = latest.risk_band.value_counts()
    summary_doc = {
        "batch_date": worklist_batch,
        "total_patients": int(len(latest)),
        "high_count": int(counts.get("High", 0)),
        "medium_count": int(counts.get("Medium", 0)),
        "low_count": int(counts.get("Low", 0)),
        "pct_high": round(float(counts.get("High", 0)) / max(len(latest), 1) * 100, 2),
        "wow_change": "N/A",
    }

    print("\n" + "=" * 74)
    print("PREVIEW")
    print("=" * 74)
    print(f"  patient_worklist : {len(worklist_docs):,} docs (batch {worklist_batch})")
    print(f"  risk_registry    : {len(registry_docs):,} docs across "
          f"{M.batch_date.nunique():,} distinct batch_dates")
    print(f"  executive_summary: {summary_doc}")
    multi = latest[latest.n_prior_adm > 0]
    print(f"\n  patients with real multi-admission history: "
          f"{len(multi):,} / {len(latest):,} ({len(multi)/max(len(latest),1):.1%})")
    ex = worklist_docs[int(np.argmax([d['risk_score'] for d in worklist_docs]))]
    print(f"\n  highest-risk example: {ex['patient_id']}  "
          f"{ex['risk_score']}%  {ex['risk_band']}  disch {ex['discharge_date']}")
    print(f"    dx: {ex['primary_diagnosis']}  [{ex['primary_icd_code']}]")
    for k in ("driver_1", "driver_2", "driver_3"):
        print(f"    - {ex[k]}")

    if a.dry_run:
        print("\n  DRY RUN - nothing written")
        return

    # --- write ------------------------------------------------------------
    load_dotenv()
    from api.db_utils import get_db_name, get_mongo_client
    uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    db = get_mongo_client(uri)[get_db_name()]

    print("\nwriting to MongoDB ...")
    db["patient_worklist"].delete_many({"source": "mimic"})
    db["patient_worklist"].delete_many({"batch_date": worklist_batch})
    for i in range(0, len(worklist_docs), 2000):
        db["patient_worklist"].insert_many(worklist_docs[i:i + 2000])
    print(f"  patient_worklist  <- {len(worklist_docs):,}")

    # Indexes the dashboard actually queries on. Without them every worklist
    # request is a collection scan, which is most of why it took 27 seconds.
    db["patient_worklist"].create_index([("batch_date", 1), ("risk_score", -1)])
    db["patient_worklist"].create_index([("batch_date", 1), ("clinical_group", 1)])
    # Multikey: MongoDB indexes each array element, so the condition filter is
    # an index scan even when several conditions are selected at once.
    db["patient_worklist"].create_index([("batch_date", 1), ("clinical_groups", 1)])
    db["patient_worklist"].create_index([("patient_id", 1)])
    print("  patient_worklist  indexes ensured")

    db["risk_registry"].delete_many({"model_version": MODEL_VERSION})
    for i in range(0, len(registry_docs), 10000):
        db["risk_registry"].insert_many(registry_docs[i:i + 10000])
    print(f"  risk_registry     <- {len(registry_docs):,}")

    db["executive_summary"].replace_one({"batch_date": worklist_batch},
                                        summary_doc, upsert=True)
    print(f"  executive_summary <- 1")

    os.makedirs(os.path.dirname(THRESHOLDS_OUT), exist_ok=True)
    with open(THRESHOLDS_OUT, "w") as f:
        json.dump(thresholds, f, indent=2)
    print(f"  {THRESHOLDS_OUT} written")
    print("\ndone")


if __name__ == "__main__":
    main()
