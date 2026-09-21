#!/usr/bin/env python3
"""
External-transfer test: score the MIMIC-IV-trained Phase 1 model on the UCI
Diabetes 130-US Hospitals dataset.

This is NOT a validation of the model. It is a transferability probe with three
sources of degradation deliberately separated:

  1. MISSING FEATURES  - UCI carries no labs, no DRG severity, no marital
                         status. ~55 of the model's 94 features are unavailable.
  2. DOMAIN SHIFT      - different hospitals, era (1999-2008 vs 2008-2022),
                         and a diabetes-only population.
  3. LABEL SHIFT       - UCI "<30" counts ALL readmissions inside 30 days;
                         the MIMIC label excluded elective returns.

To tell (1) apart from (2)+(3), the script also re-scores the model's own MIMIC
test fold with the same features masked to NaN. The gap between that and the
full MIMIC score is the cost of missing features alone; whatever remains when
scoring UCI is domain plus label shift.

Usage
-----
    python scripts/test_mimic_model_on_diabetes.py \
        --bundle "data/mimic/model/results/phase1_model.joblib" \
        --matrix "data/mimic/model/results/phase1_matrix.parquet" \
        --diabetes data/diabetic/diabetic_data.csv
"""

import argparse
import json
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss,
                             confusion_matrix, roc_auc_score)
from sklearn.model_selection import GroupShuffleSplit

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# ICD-9 Charlson patterns (identical to the training notebook's ICD-9 side).
# UCI diag_1/2/3 are ICD-9, so only that half of the mapping applies.
# ---------------------------------------------------------------------------
CHARLSON9 = {
    "myocardial_infarction":    (1, r"^(410|412)"),
    "congestive_heart_failure": (1, r"^(39891|402(01|11|91)|404(01|03|11|13|91|93)|425[456789]|428)"),
    "peripheral_vascular":      (1, r"^(0930|437[34]|440|441|443[123456789]|4471|5571|5579|V434)"),
    "cerebrovascular":          (1, r"^(36234|43[0-8])"),
    "dementia":                 (1, r"^(290|2941|3312)"),
    "chronic_pulmonary":        (1, r"^(4168|4169|49[0-6]|50[0-5]|5064|5081|5088)"),
    "rheumatic":                (1, r"^(4465|710[0-4]|714[0128]|725)"),
    "peptic_ulcer":             (1, r"^(53[1-4])"),
    "mild_liver":               (1, r"^(070[23][23]|070[45]4|0706|0709|57[01]|5733|5734|5738|5739|V427)"),
    "diabetes_uncomplicated":   (1, r"^(250[0-3]|2508|2509)"),
    "diabetes_complicated":     (2, r"^(250[4-7])"),
    "hemiplegia":               (2, r"^(3341|342|343|344[0-6]|3449)"),
    "renal_disease":            (2, r"^(40301|40311|40391|40402|40403|40412|40413|40492|40493|58[26]|5830[0-7]|585|586|5880|V420|V451|V56)"),
    "malignancy":               (2, r"^(1[4-9][0-9]|20[0-8]|2386)"),
    "severe_liver":             (3, r"^(456[012]|572[2-8])"),
    "metastatic_cancer":        (6, r"^(19[6-9])"),
    "hiv_aids":                 (6, r"^(04[2-4])"),
}

# UCI discharge_disposition_id semantics
DISP_EXPIRED = {11, 19, 20, 21}
DISP_HOSPICE = {13, 14}
DISP_HOME    = {1}
DISP_SNF     = {3, 4, 5, 22, 23, 24}
DISP_AMA     = {7}

# UCI admission_type_id -> MIMIC admission_type
ADM_TYPE_MAP = {1: "EW EMER.", 2: "URGENT", 3: "ELECTIVE", 7: "EW EMER."}

RACE_MAP = {
    "Caucasian": "WHITE",
    "AfricanAmerican": "BLACK/AFRICAN AMERICAN",
    "Hispanic": "HISPANIC OR LATINO",
    "Asian": "ASIAN",
    "Other": "OTHER",
}

PAYER_MAP = {
    "MC": "Medicare", "MD": "Medicaid",
    "BC": "Private", "HM": "Private", "CP": "Private", "CM": "Private",
    "UN": "Private", "OG": "Private", "PO": "Private", "DM": "Private",
    "SP": "Other", "SI": "Other", "CH": "Other", "WC": "Other",
    "FR": "Other", "MP": "Other", "OT": "Other",
}

# Crude ordinal -> numeric for the only two labs UCI carries
A1C_MAP = {">8": 9.0, ">7": 7.5, "Norm": 5.5}
GLU_MAP = {">300": 350.0, ">200": 250.0, "Norm": 100.0}


def build_diabetes_features(path, feature_names, categoricals, train_categories):
    """Map UCI Diabetes columns onto the MIMIC model's feature contract."""
    d = pd.read_csv(path, low_memory=False, na_values=["?"])
    n_raw = len(d)

    # --- align the cohort with the MIMIC exclusions -------------------------
    expired = d.discharge_disposition_id.isin(DISP_EXPIRED)
    hospice = d.discharge_disposition_id.isin(DISP_HOSPICE)
    d = d[~(expired | hospice)].copy()
    print(f"  raw encounters              : {n_raw:,}")
    print(f"  excluded expired            : {int(expired.sum()):,}")
    print(f"  excluded hospice            : {int(hospice.sum()):,}")
    print(f"  -> eligible encounters      : {len(d):,}")

    out = pd.DataFrame(index=d.index)

    # --- demographics -------------------------------------------------------
    out["anchor_age"] = (d.age.str.extract(r"\[(\d+)-")[0].astype(float) + 5)
    out["gender"] = d.gender.map({"Female": "F", "Male": "M"})
    out["race"] = d.race.map(RACE_MAP).fillna("UNKNOWN")
    out["marital_status"] = "UNKNOWN"                      # absent in UCI
    out["insurance"] = d.payer_code.map(PAYER_MAP).fillna("UNKNOWN")
    out["admission_type"] = d.admission_type_id.map(ADM_TYPE_MAP).fillna("UNKNOWN")

    # --- utilisation / stay -------------------------------------------------
    out["los_days"] = d.time_in_hospital.astype(float)
    out["n_prior_adm"] = d.number_inpatient.astype(float)
    out["prior_adm_flag"] = (d.number_inpatient > 0).astype(float)
    out["days_since_prev"] = np.nan                        # no timing in UCI
    out["readmit_history"] = np.nan                        # no timing in UCI
    out["ed_visit"] = ((d.admission_source_id == 7) | (d.number_emergency > 0)).astype(float)
    out["ed_hours"] = np.nan
    out["is_emergency"] = d.admission_type_id.isin([1, 2, 7]).astype(float)
    out["n_procedures"] = d.num_procedures.astype(float)
    out["n_diagnoses"] = d.number_diagnoses.astype(float)

    # --- medications --------------------------------------------------------
    # UCI only enumerates diabetes drugs, so num_medications proxies both the
    # order count and the distinct-drug count, and only insulin is knowable.
    out["n_drug_orders"] = d.num_medications.astype(float)
    out["n_distinct_drugs"] = d.num_medications.astype(float)
    out["med_insulin"] = (d.insulin != "No").astype(float)
    for m in ("med_anticoagulant", "med_opioid", "med_diuretic", "med_antipsychotic"):
        out[m] = np.nan

    # --- discharge destination ---------------------------------------------
    out["disch_home"] = d.discharge_disposition_id.isin(DISP_HOME).astype(float)
    out["disch_snf"]  = d.discharge_disposition_id.isin(DISP_SNF).astype(float)
    out["disch_ama"]  = d.discharge_disposition_id.isin(DISP_AMA).astype(float)

    # --- Charlson from diag_1/2/3 (ICD-9) -----------------------------------
    codes = (d[["diag_1", "diag_2", "diag_3"]]
             .astype(str).apply(lambda s: s.str.upper().str.replace(".", "", regex=False)))
    score = np.zeros(len(d))
    for cond, (w, pat) in CHARLSON9.items():
        hit = np.zeros(len(d), dtype=bool)
        for c in ("diag_1", "diag_2", "diag_3"):
            hit |= codes[c].str.match(pat, na=False).values
        out[cond] = hit.astype(float)
    # Charlson hierarchy, mirroring the training notebook
    out.loc[out.diabetes_complicated == 1, "diabetes_uncomplicated"] = 0
    out.loc[out.severe_liver == 1, "mild_liver"] = 0
    out.loc[out.metastatic_cancer == 1, "malignancy"] = 0
    for cond, (w, _) in CHARLSON9.items():
        score += out[cond].values * w
    out["charlson_score"] = score

    # --- the two labs UCI carries, as crude ordinals ------------------------
    out["lab_hba1c_last"]   = d.A1Cresult.map(A1C_MAP)
    out["lab_glucose_last"] = d.max_glu_serum.map(GLU_MAP)

    # --- everything else the model expects but UCI lacks --------------------
    for f in feature_names:
        if f not in out.columns:
            out[f] = np.nan

    # --- impose the exact training categories -------------------------------
    # Unseen levels become NaN, which HistGradientBoosting routes to its
    # learned missing-value branch rather than silently mis-encoding.
    for c in categoricals:
        out[c] = pd.Categorical(out[c], categories=train_categories[c])

    y = (d.readmitted == "<30").astype(int).values
    groups = d.patient_nbr.values
    return out[feature_names], y, groups


def metrics(y, p, label):
    return {
        "cohort": label,
        "n": len(y),
        "prevalence": y.mean(),
        "AUC-ROC": roc_auc_score(y, p),
        "AUC-PR": average_precision_score(y, p),
        "Brier": brier_score_loss(y, p),
        "mean_pred": p.mean(),
        "calib_ratio": p.mean() / y.mean(),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", required=True)
    ap.add_argument("--matrix", required=True)
    ap.add_argument("--diabetes", required=True)
    a = ap.parse_args()

    print("=" * 78)
    print("LOADING MODEL")
    print("=" * 78)
    b = joblib.load(a.bundle)
    model, FEATURES, CATEGORICALS = b["model"], b["features"], b["categoricals"]
    thr = b["threshold"]
    print(f"  features={len(FEATURES)}  categoricals={CATEGORICALS}  threshold={thr:.4f}")

    M = pd.read_parquet(a.matrix)
    train_categories = {c: list(M[c].cat.categories) for c in CATEGORICALS}

    # Reproduce the notebook's exact test fold so the reference number is the
    # model's real held-out performance, not a training-contaminated one.
    y_all = M.readmit_30d.values
    g_all = M.subject_id.values
    Xa = M[FEATURES]
    gss = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=42)
    trainval_idx, test_idx = next(gss.split(Xa, y_all, g_all))
    Xte, yte = Xa.iloc[test_idx], y_all[test_idx]
    p_mimic = model.predict_proba(Xte)[:, 1]

    rows = [metrics(yte, p_mimic, "MIMIC test fold (all 94 features)")]

    print("\n" + "=" * 78)
    print("MAPPING UCI DIABETES ONTO THE MODEL'S FEATURE CONTRACT")
    print("=" * 78)
    Xd, yd, gd = build_diabetes_features(a.diabetes, FEATURES, CATEGORICALS, train_categories)

    avail = [f for f in FEATURES if Xd[f].notna().any()]
    missing = [f for f in FEATURES if f not in avail]
    print(f"\n  features populated from UCI : {len(avail)} / {len(FEATURES)}")
    print(f"  features left as NaN        : {len(missing)}")
    print(f"  30-day readmission rate     : {yd.mean():.2%} "
          f"(vs {yte.mean():.2%} in MIMIC)")

    # --- ablation: MIMIC test fold with the SAME features masked -----------
    # Isolates "cost of missing features" from "cost of domain/label shift".
    Xte_masked = Xte.copy()
    for f in missing:
        Xte_masked[f] = np.nan
    p_masked = model.predict_proba(Xte_masked)[:, 1]
    rows.append(metrics(yte, p_masked, "MIMIC test fold (UCI features only)"))

    # --- the actual transfer test ------------------------------------------
    p_diab = model.predict_proba(Xd)[:, 1]
    rows.append(metrics(yd, p_diab, "UCI Diabetes (transfer, as-is)"))

    # --- can a local recalibration rescue it? ------------------------------
    # Discrimination and calibration fail independently. If ranking transfers
    # but probabilities don't, refitting only the calibration layer on a small
    # local sample fixes it without retraining the model.
    gss2 = GroupShuffleSplit(n_splits=1, test_size=0.5, random_state=0)
    cal_idx, hold_idx = next(gss2.split(Xd, yd, gd))
    platt = LogisticRegression(max_iter=1000)
    platt.fit(p_diab[cal_idx].reshape(-1, 1), yd[cal_idx])
    p_recal = platt.predict_proba(p_diab[hold_idx].reshape(-1, 1))[:, 1]
    rows.append(metrics(yd[hold_idx], p_recal, "UCI Diabetes (recalibrated)"))

    print("\n" + "=" * 78)
    print("RESULTS")
    print("=" * 78)
    res = pd.DataFrame(rows).set_index("cohort")
    print(res.round(4).to_string())

    base = rows[0]["AUC-ROC"]
    print(f"\n  AUC-ROC decomposition")
    print(f"    full MIMIC model                     : {rows[0]['AUC-ROC']:.4f}")
    print(f"    - cost of dropping unavailable feats : "
          f"{rows[1]['AUC-ROC'] - rows[0]['AUC-ROC']:+.4f}  -> {rows[1]['AUC-ROC']:.4f}")
    print(f"    - cost of domain + label shift       : "
          f"{rows[2]['AUC-ROC'] - rows[1]['AUC-ROC']:+.4f}  -> {rows[2]['AUC-ROC']:.4f}")

    # --- operating point on UCI at the shipped threshold -------------------
    pred = (p_diab >= thr).astype(int)
    tn, fp, fn, tp = confusion_matrix(yd, pred).ravel()
    print(f"\n  At the shipped threshold {thr:.4f} on UCI:")
    print(f"    flagged   : {tp+fp:,} / {len(yd):,} ({(tp+fp)/len(yd):.1%} of discharges)")
    print(f"    precision : {tp/(tp+fp):.1%}" if (tp + fp) else "    precision : n/a")
    print(f"    recall    : {tp/(tp+fn):.1%}" if (tp + fn) else "    recall    : n/a")

    out = {
        "results": [{k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
                     for k, v in r.items()} for r in rows],
        "features_populated": len(avail),
        "features_missing": len(missing),
        "missing_features": missing,
    }
    with open("data/mimic/transfer_test_results.json", "w") as f:
        json.dump(out, f, indent=2)
    print("\n  written: data/mimic/transfer_test_results.json")


if __name__ == "__main__":
    main()
