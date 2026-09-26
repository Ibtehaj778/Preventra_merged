"""
Patient list + detail endpoints — live MongoDB queries.

Filter/sort/paginate all happen server-side via Mongo. The merged
patient documents (created by the migration script) already contain
both the clinical fields and the SHAP driver columns.
"""

import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends

import core.model as model
from core.mongo import get_db
from core.security import current_user
from core.access import require_patient, scope_of, scope_query
from schemas.patient_views import PatientPharmacyView

router = APIRouter()

_FINANCIAL_REGEX = "financial|out-of-pocket|cost|income"
_HIGH_RISK_THRESHOLD = 0.75


def _build_match(
    segment: Optional[int],
    molecule: Optional[str],
    min_risk: Optional[float],
    prediction: Optional[str],
    financial_only: bool,
    search: Optional[str],
) -> dict:
    match: dict = {}
    if segment is not None:
        match["cluster"] = segment
    if molecule:
        match["assigned_molecule"] = molecule.upper()
    if min_risk is not None:
        match["dropout_prob"] = {"$gte": min_risk}
    if prediction:
        match["prediction"] = prediction
    if financial_only:
        match["driver_1"] = {"$regex": _FINANCIAL_REGEX, "$options": "i"}
    if search:
        clauses = [{"driver_1": {"$regex": search, "$options": "i"}}]
        try:
            clauses.append({"patient_idx": int(search)})
        except ValueError:
            pass
        match["$or"] = clauses
    return match


def _shape_patient(doc: dict) -> dict:
    cluster = int(doc.get("cluster") or 0)
    return {
        "patient_idx":          int(doc.get("patient_idx", 0)),
        "dropout_prob":         round(float(doc.get("dropout_prob") or doc.get("dropout_proba") or 0.5), 4),
        "prediction":           str(doc.get("prediction") or "Unknown"),
        "cluster":              cluster,
        "segment":              model.SEGMENT_SHORT[cluster] if cluster < 4 else "Unknown",
        "assigned_molecule":    str(doc.get("assigned_molecule") or "UNKNOWN"),
        "avg_oop_cost":         round(float(doc.get("avg_oop_cost") or 0.0), 2),
        "driver_1":             str(doc.get("driver_1") or ""),
        "driver_1_direction":   str(doc.get("driver_1_direction") or ""),
        "driver_1_shap":        doc.get("driver_1_shap"),
        "driver_2":             doc.get("driver_2"),
        "driver_2_direction":   doc.get("driver_2_direction"),
        "driver_2_shap":        doc.get("driver_2_shap"),
        "driver_3":             doc.get("driver_3"),
        "driver_3_direction":   doc.get("driver_3_direction"),
        "driver_3_shap":        doc.get("driver_3_shap"),
        "BMXBMI":               doc.get("BMXBMI"),
        "RIDAGEYR":             int(doc["RIDAGEYR"]) if doc.get("RIDAGEYR") is not None else None,
        "LBXGH":                doc.get("LBXGH"),
        "comorbidity_score":    int(doc["comorbidity_score"]) if doc.get("comorbidity_score") is not None else None,
        "bio_friction":         doc.get("bio_friction"),
        "income_cost_pressure": doc.get("income_cost_pressure"),
        "system_refill_score":  doc.get("system_refill_score"),
        "drug_generation":      int(doc["drug_generation"]) if doc.get("drug_generation") is not None else None,
        "time_to_dropout":      int(doc["time_to_dropout"]) if doc.get("time_to_dropout") is not None else None,
    }


@router.get("/patients")
async def get_patients(
    page:           int   = Query(0, ge=0),
    page_size:      int   = Query(20, ge=1, le=10000),
    segment:        Optional[int]   = Query(None),
    molecule:       Optional[str]   = Query(None),
    min_risk:       Optional[float] = Query(None, ge=0.0, le=1.0),
    prediction:     Optional[str]   = Query(None),
    financial_only: bool            = Query(False),
    sort_by:        str             = Query("dropout_prob"),
    sort_dir:       str             = Query("desc"),
    search:         Optional[str]   = Query(None),
    user:           dict            = Depends(current_user),
    scope:          Optional[list]  = Depends(scope_of),
):
    db = get_db()
    # Only the caller's patients: a top-level condition, so the counts below
    # (which extend `match`) are limited the same way as the page.
    match = {**_build_match(segment, molecule, min_risk, prediction, financial_only, search),
             **scope_query(scope)}
    direction = -1 if sort_dir.lower() == "desc" else 1

    high_risk_filter = {**match, "dropout_prob": {"$gte": _HIGH_RISK_THRESHOLD}}
    if "dropout_prob" in match and isinstance(match["dropout_prob"], dict):
        merged = {**match["dropout_prob"], "$gte": max(match["dropout_prob"].get("$gte", 0), _HIGH_RISK_THRESHOLD)}
        high_risk_filter = {**match, "dropout_prob": merged}

    financial_filter = {**match, "driver_1": {"$regex": _FINANCIAL_REGEX, "$options": "i"}}

    total, high_risk, financial_cnt, page_docs = await asyncio.gather(
        db.patients.count_documents(match),
        db.patients.count_documents(high_risk_filter),
        db.patients.count_documents(financial_filter),
        db.patients.find(match, {"_id": 0})
                   .sort(sort_by, direction)
                   .skip(page * page_size)
                   .limit(page_size)
                   .to_list(length=page_size),
    )

    return {
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "patients":  [_shape_patient(d) for d in page_docs],
        "summary":   {"high_risk_count": high_risk, "financial_barrier_count": financial_cnt},
    }


@router.get("/patients/{patient_idx}")
async def get_patient(patient_idx: int, user: dict = Depends(current_user),
                      scope: Optional[list] = Depends(scope_of)):
    require_patient(scope, patient_idx)
    db = get_db()
    doc = await db.patients.find_one({"patient_idx": patient_idx}, {"_id": 0})
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Patient {patient_idx} not found")

    patient = _shape_patient(doc)

    shap_drivers = None
    if doc.get("driver_1") is not None:
        shap_drivers = []
        for rank, (feat_col, dir_col, shap_col) in enumerate([
            ("driver_1", "driver_1_direction", "driver_1_shap"),
            ("driver_2", "driver_2_direction", "driver_2_shap"),
            ("driver_3", "driver_3_direction", "driver_3_shap"),
        ], start=1):
            feat = doc.get(feat_col)
            if feat is None:
                break
            shap_drivers.append({
                "rank":       rank,
                "feature":    str(feat),
                "direction":  str(doc.get(dir_col) or ""),
                "shap_value": round(float(doc.get(shap_col) or 0.0), 4),
            })

    cluster  = int(doc.get("cluster") or 0)
    checkpts = (model.survival_cache or {}).get("checkpoints", [])
    seg_surv = next((c for c in checkpts if c.get("cluster") == cluster), None)

    return {
        "patient":          patient,
        "shap_drivers":     shap_drivers,
        "segment_survival": seg_surv,
    }
    
@router.get("/patients/{patient_idx}/pharmacy-view", response_model=PatientPharmacyView)
async def get_patient_pharmacy_view(patient_idx: int, user: dict = Depends(current_user),
                                    scope: Optional[list] = Depends(scope_of)):
    require_patient(scope, patient_idx)
    db = get_db()
    doc = await db.patients.find_one({"patient_idx": patient_idx}, {"_id": 0})
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Patient {patient_idx} not found")

    return PatientPharmacyView(
        patient_idx=int(doc.get("patient_idx", 0)),
        assigned_molecule=str(doc.get("assigned_molecule") or "UNKNOWN"),
        drug_generation=doc.get("drug_generation"),
        system_refill_score=doc.get("system_refill_score"),
    )