"""
One-shot migration: CSV / npy / pickle  →  MongoDB Atlas.

Run from the Backend/ directory:
    python -m scripts.migrate_csv_to_mongo

Idempotent: each target collection is dropped and re-inserted on every run,
so re-running after a notebook re-export always produces a clean snapshot.

Collections created in DB `glp1_analytics` (configurable via env):
    patients              ← GLP1_FINAL_WITH_SURVIVAL.csv ⨝ shap_patient_drivers.csv
    segment_profiles      ← computed from patients
    cost_effectiveness    ← cost_effectiveness.csv ⨝ icer_by_segment.csv (pivoted)
    survival_checkpoints  ← survival_checkpoints.csv
    survival_curves       ← Kaplan–Meier fit on patients
    progression_cost      ← progression_cost.csv      (Consequence Model Phase 1)
    rebound_risk          ← rebound_risk.csv          (Consequence Model Phase 2 — per patient)
    rebound_trajectory    ← rebound_trajectory.csv    (Consequence Model Phase 2 — line chart)
    rebound_sensitivity   ← rebound_sensitivity.csv   (Consequence Model Phase 2 — sensitivity)
    payer_roi             ← payer_roi.csv             (Consequence Model Phase 3 — per cluster)
    payer_roi_yearly      ← payer_roi_yearly.csv      (Consequence Model Phase 3 — per cluster × year)
    model_meta            ← hardcoded notebook metrics
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from pymongo import ASCENDING, MongoClient

from core.config import settings


SEGMENT_LABELS = [
    "Low Urgency Dropout Risk",
    "Financial Barrier Dropout Risk",
    "Low Friction Strong Adherer",
    "Moderate Risk Moderate Adherer",
]
SEGMENT_SHORT = [
    "Low Urgency Dropout",
    "Financial Barrier Dropout",
    "Low Friction Adherer",
    "Moderate Risk Adherer",
]
SEGMENT_COLORS = ["#EF5350", "#FF7043", "#43A047", "#1E88E5"]


def _clean(value):
    """Convert pandas/numpy scalars + NaN to Mongo-safe Python primitives."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        v = float(value)
        return None if math.isnan(v) else v
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def _doc(row: pd.Series) -> dict:
    return {k: _clean(v) for k, v in row.items()}


def _replace_collection(db, name: str, docs: list[dict]) -> None:
    db.drop_collection(name)
    if docs:
        db[name].insert_many(docs)
    print(f"  ✅  {name}: {len(docs):,}")


# ── patients ─────────────────────────────────────────────────────────────────
def migrate_patients(db, data_dir: Path) -> pd.DataFrame:
    main_path = data_dir / "GLP1_FINAL_WITH_SURVIVAL.csv"
    shap_path = data_dir / "shap_patient_drivers.csv"

    df_main = pd.read_csv(main_path)
    df_main = df_main.reset_index(drop=True)
    df_main.insert(0, "patient_idx", df_main.index)

    if shap_path.exists():
        df_shap = pd.read_csv(shap_path)
        # `dropout_prob` comes from shap (test set); main has `dropout_proba`
        df_merged = df_main.merge(df_shap, on="patient_idx", how="left", suffixes=("", "_shap"))
    else:
        df_merged = df_main

    docs = [_doc(row) for _, row in df_merged.iterrows()]
    _replace_collection(db, "patients", docs)

    db.patients.create_index([("patient_idx", ASCENDING)], unique=True)
    db.patients.create_index([("cluster", ASCENDING)])
    db.patients.create_index([("dropout_prob", ASCENDING)])
    db.patients.create_index([("assigned_molecule", ASCENDING)])
    return df_merged


# ── cost_effectiveness (CEA + ICER pivot) ────────────────────────────────────
def migrate_cost_effectiveness(db, data_dir: Path) -> None:
    cea = pd.read_csv(data_dir / "cost_effectiveness.csv")
    icer = pd.read_csv(data_dir / "icer_by_segment.csv")

    # Pivot ICER long → wide: one row per cluster, two columns per comparator
    pivot = icer.pivot_table(
        index="cluster",
        columns="comparator",
        values=["icer_weight", "icer_hba1c"],
        aggfunc="first",
    )
    # Flatten MultiIndex columns: ("icer_weight", "insulin_glargine") → "icer_insulin_weight"
    pivot.columns = [f"icer_{comp.split('_')[0]}_{metric.split('_')[1]}"
                     for metric, comp in pivot.columns]
    pivot = pivot.reset_index()

    merged = cea.merge(pivot, on="cluster", how="left")

    docs = []
    for _, row in merged.iterrows():
        i = int(row["cluster"])
        docs.append({
            "cluster":             i,
            "label":               SEGMENT_SHORT[i],
            "segment":             str(row.get("segment", SEGMENT_LABELS[i])),
            "n":                   int(row["n"]),
            "adherence_rate":      _clean(row.get("adherence_rate")),
            "annual_cost":         _clean(row.get("avg_annual_cost")),
            "avg_oop_cost":        _clean(row.get("avg_oop_cost")),
            "weight_loss":         _clean(row.get("avg_weight_loss_pct")),
            "hba1c_reduction":     _clean(row.get("avg_hba1c_reduction")),
            "cost_per_weight":     _clean(row.get("cost_per_weight_pct")),
            "cost_per_hba1c":      _clean(row.get("cost_per_hba1c_pt")),
            "wasted_spend_per_pt": _clean(row.get("wasted_spend_per_pt")),
            "total_annual_spend":  _clean(row.get("total_annual_spend")),
            "icer_insulin_weight": _clean(row.get("icer_insulin_weight")),
            "icer_insulin_hba1c":  _clean(row.get("icer_insulin_hba1c")),
            "icer_sglt2_weight":   _clean(row.get("icer_sglt2_weight")),
            "icer_sglt2_hba1c":    _clean(row.get("icer_sglt2_hba1c")),
        })

    _replace_collection(db, "cost_effectiveness", docs)
    db.cost_effectiveness.create_index([("cluster", ASCENDING)], unique=True)


# ── segment_profiles (computed from patients) ────────────────────────────────
def migrate_segment_profiles(db, df_patients: pd.DataFrame, cea_docs: list[dict]) -> None:
    cea_by_cluster = {d["cluster"]: d for d in cea_docs}
    docs = []
    for i in range(4):
        sub = df_patients[df_patients["cluster"] == i]
        if sub.empty:
            continue
        adh = float(sub["is_adherent"].mean()) if "is_adherent" in sub.columns else 0.0
        cea = cea_by_cluster.get(i, {})
        annual_cost = cea.get("annual_cost") or 10603.0
        docs.append({
            "cluster":         i,
            "label":           SEGMENT_LABELS[i],
            "short":           SEGMENT_SHORT[i],
            "color":           SEGMENT_COLORS[i],
            "n":               int(len(sub)),
            "adherence":       round(adh, 4),
            "age":             round(float(sub["RIDAGEYR"].mean()), 1),
            "bmi":             round(float(sub["BMXBMI"].mean()), 1),
            "hba1c":           round(float(sub["LBXGH"].mean()), 2),
            "oop_cost":        round(float(sub["avg_oop_cost"].mean()), 2),
            "cost_pressure":   round(float(sub["income_cost_pressure"].mean()), 1),
            "bio_friction":    round(float(sub["bio_friction"].mean()), 3),
            "refill_score":    round(float(sub["system_refill_score"].mean()), 4),
            "comorbidity":     round(float(sub["comorbidity_score"].mean()), 2),
            "wasted_per_pt":   round(annual_cost * (1 - adh)),
            "cost_per_hba1c":  _clean(cea.get("cost_per_hba1c")),
            "cost_per_weight": _clean(cea.get("cost_per_weight")),
        })
    _replace_collection(db, "segment_profiles", docs)
    db.segment_profiles.create_index([("cluster", ASCENDING)], unique=True)


# ── survival_checkpoints ─────────────────────────────────────────────────────
def migrate_survival_checkpoints(db, data_dir: Path) -> None:
    df = pd.read_csv(data_dir / "survival_checkpoints.csv")
    name_to_cluster = {label: i for i, label in enumerate(SEGMENT_LABELS)}

    docs = []
    for _, row in df.iterrows():
        seg = str(row["segment"])
        cluster = name_to_cluster.get(seg)
        if cluster is None:
            continue
        docs.append({
            "cluster": cluster,
            "segment": seg,
            "day30":   _clean(row.get("day_30")),
            "day60":   _clean(row.get("day_60")),
            "day90":   _clean(row.get("day_90")),
            "day180":  _clean(row.get("day_180")),
        })
    _replace_collection(db, "survival_checkpoints", docs)
    db.survival_checkpoints.create_index([("cluster", ASCENDING)], unique=True)


# ── survival_curves (KM fit, computed) ───────────────────────────────────────
def migrate_survival_curves(db, df_patients: pd.DataFrame) -> None:
    try:
        from lifelines import KaplanMeierFitter
    except ImportError:
        print("  ⚠️   lifelines not installed — skipping survival_curves collection")
        return

    required = {"cluster", "time_to_dropout", "event_occurred"}
    if not required.issubset(df_patients.columns):
        print(f"  ⚠️   missing columns {required - set(df_patients.columns)} — skipping survival_curves")
        return

    timeline = list(range(0, 181, 5))
    docs = []
    for i in range(4):
        sub = df_patients[df_patients["cluster"] == i]
        if sub.empty:
            continue
        kmf = KaplanMeierFitter()
        kmf.fit(sub["time_to_dropout"], event_observed=sub["event_occurred"])
        sf = kmf.survival_function_at_times(timeline)
        adh = float(sub["is_adherent"].mean()) if "is_adherent" in sub.columns else 0.5
        docs.append({
            "cluster":   i,
            "label":     SEGMENT_LABELS[i],
            "color":     SEGMENT_COLORS[i],
            "adherence": round(adh, 4),
            "data":      [{"day": int(d), "survival": round(float(sf.iloc[j]), 4)}
                          for j, d in enumerate(timeline)],
        })
    _replace_collection(db, "survival_curves", docs)
    db.survival_curves.create_index([("cluster", ASCENDING)], unique=True)


# ── progression_cost (Phase 1 of the Consequence Model) ──────────────────────
def migrate_progression_cost(db, data_dir: Path) -> None:
    path = data_dir / "progression_cost.csv"
    if not path.exists():
        print("  ⚠️   progression_cost.csv not found — skipping. Run "
              "`python -m Model.consequence.downstream_cost` from the project root.")
        return

    df = pd.read_csv(path)
    docs = [_doc(row) for _, row in df.iterrows()]
    _replace_collection(db, "progression_cost", docs)
    db.progression_cost.create_index([("cluster", ASCENDING)])
    db.progression_cost.create_index([("patient_idx", ASCENDING)], unique=True)


# ── rebound (Consequence Model Phase 2) ──────────────────────────────────────
def migrate_rebound_risk(db, data_dir: Path) -> None:
    path = data_dir / "rebound_risk.csv"
    if not path.exists():
        print("  ⚠️   rebound_risk.csv not found — skipping. Run "
              "`python -m Model.consequence.rebound_risk` from the project root.")
        return

    df = pd.read_csv(path)
    docs = [_doc(row) for _, row in df.iterrows()]
    _replace_collection(db, "rebound_risk", docs)
    db.rebound_risk.create_index([("cluster", ASCENDING)])
    db.rebound_risk.create_index([("patient_idx", ASCENDING)], unique=True)


def migrate_rebound_trajectory(db, data_dir: Path) -> None:
    path = data_dir / "rebound_trajectory.csv"
    if not path.exists():
        print("  ⚠️   rebound_trajectory.csv not found — skipping.")
        return

    df = pd.read_csv(path)
    docs = [_doc(row) for _, row in df.iterrows()]
    _replace_collection(db, "rebound_trajectory", docs)
    db.rebound_trajectory.create_index([("cluster", ASCENDING), ("scenario", ASCENDING)])


def migrate_rebound_sensitivity(db, data_dir: Path) -> None:
    path = data_dir / "rebound_sensitivity.csv"
    if not path.exists():
        print("  ⚠️   rebound_sensitivity.csv not found — skipping.")
        return

    df = pd.read_csv(path)
    docs = [_doc(row) for _, row in df.iterrows()]
    _replace_collection(db, "rebound_sensitivity", docs)
    db.rebound_sensitivity.create_index(
        [("cluster", ASCENDING), ("scenario", ASCENDING)], unique=True
    )


# ── payer_roi (Consequence Model Phase 3, multi-scenario) ────────────────────
def migrate_payer_roi(db, data_dir: Path) -> None:
    path = data_dir / "payer_roi.csv"
    if not path.exists():
        print("  ⚠️   payer_roi.csv not found — skipping. Run "
              "`python -m Model.consequence.payer_roi` from the project root.")
        return

    df = pd.read_csv(path)
    if "payer_type" not in df.columns:
        df["payer_type"] = "current"  # backwards compat with older CSVs
    docs = [_doc(row) for _, row in df.iterrows()]
    _replace_collection(db, "payer_roi", docs)
    # Compound unique index — one row per (payer_type, cluster).
    db.payer_roi.create_index(
        [("payer_type", ASCENDING), ("cluster", ASCENDING)], unique=True
    )


def migrate_payer_roi_yearly(db, data_dir: Path) -> None:
    path = data_dir / "payer_roi_yearly.csv"
    if not path.exists():
        print("  ⚠️   payer_roi_yearly.csv not found — skipping.")
        return

    df = pd.read_csv(path)
    if "payer_type" not in df.columns:
        df["payer_type"] = "current"
    docs = [_doc(row) for _, row in df.iterrows()]
    _replace_collection(db, "payer_roi_yearly", docs)
    db.payer_roi_yearly.create_index(
        [("payer_type", ASCENDING), ("cluster", ASCENDING), ("horizon_years", ASCENDING)],
        unique=True,
    )


# ── model_meta (hardcoded notebook metrics) ──────────────────────────────────
def migrate_model_meta(db) -> None:
    doc = {
        "_id":           "current",
        "name":          "GradientBoostingClassifier v2",
        "params":        "n_estimators=200, lr=0.05, max_depth=4, max_features=sqrt",
        "threshold":     0.48,
        "train_size":    6052,
        "test_size":     1514,
        "metrics": {
            "accuracy":  0.791,
            "precision": 0.876,
            "recall":    0.646,
            "f1":        0.744,
            "auc_roc":   0.879,
        },
        "last_trained":  "May 2026",
        "feature_count": 17,
    }
    db.drop_collection("model_meta")
    db.model_meta.insert_one(doc)
    print("  ✅  model_meta: 1")


# ── entry point ──────────────────────────────────────────────────────────────
def main() -> int:
    data_dir = Path(settings.data_dir).resolve()
    if not data_dir.exists():
        print(f"❌  Data dir not found: {data_dir}")
        return 1

    print(f"📂  Reading CSVs from: {data_dir}")
    print(f"🔌  Connecting to:     {settings.mongodb_db_name} on Atlas\n")

    client = MongoClient(settings.mongodb_uri)
    try:
        client.admin.command("ping")
    except Exception as exc:
        print(f"❌  Atlas connection failed: {exc}")
        return 1

    db = client[settings.mongodb_db_name]

    print("🚚  Migrating…")
    df_patients = migrate_patients(db, data_dir)
    migrate_cost_effectiveness(db, data_dir)
    cea_docs = list(db.cost_effectiveness.find())
    migrate_segment_profiles(db, df_patients, cea_docs)
    migrate_survival_checkpoints(db, data_dir)
    migrate_survival_curves(db, df_patients)
    migrate_progression_cost(db, data_dir)
    migrate_rebound_risk(db, data_dir)
    migrate_rebound_trajectory(db, data_dir)
    migrate_rebound_sensitivity(db, data_dir)
    migrate_payer_roi(db, data_dir)
    migrate_payer_roi_yearly(db, data_dir)
    migrate_model_meta(db)

    print("\n✅  Migration complete.")
    client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
