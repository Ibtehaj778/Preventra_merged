"""
Who may see which GLP-1 patients, and which screens - decided here only.

Mirrors Readmissions/api/access.py. Ownership lives in `patient_access`, one
record per patient_idx, which scripts/migrate_csv_to_mongo.py never drops, so a
data reload does not orphan anyone:

    hospital_id         the hospital the patient belongs to
    insurer_id          who pays for them
    assigned_doctor_id  shared_identity user id of their doctor
    assigned_nurse_ids  shared_identity user ids of their nurses
    patient_account_id  the patient's own login, if they have one

    superadmin                    every patient
    hospital_admin, case_manager  their hospital
    doctor, nurse                 their hospital's patients assigned to them
    insurer                       their members, in any hospital
    patient                       their own record
    anyone without a placement    nobody

Model-wide outputs (survival curves, feature importance, segment profiles, model
info) describe the model rather than any patient and are not filtered. Cost and
ROI screens are for the roles that own the budget.
"""

from typing import Optional

from fastapi import Depends, HTTPException

from core.mongo import get_db
from core.security import current_user

COST_VIEW_ROLES = ("superadmin", "hospital_admin", "insurer")


async def patient_scope(user: dict) -> Optional[list]:
    """The patient_idx values this user may see, or None for no restriction."""
    role, hospital, uid = user["role"], user.get("hospital_id"), user["id"]
    if role == "superadmin":
        return None
    if role in ("hospital_admin", "case_manager"):
        query = {"hospital_id": hospital} if hospital else None
    elif role == "doctor":
        query = {"hospital_id": hospital, "assigned_doctor_id": uid} if hospital else None
    elif role == "nurse":
        query = {"hospital_id": hospital, "assigned_nurse_ids": uid} if hospital else None
    elif role == "insurer":
        query = {"insurer_id": user["insurer_id"]} if user.get("insurer_id") else None
    elif role == "patient":
        query = {"patient_account_id": uid}
    else:
        query = None
    if query is None:
        return []
    docs = await get_db().patient_access.find(query, {"_id": 0, "patient_idx": 1}).to_list(length=None)
    return [int(d["patient_idx"]) for d in docs]


async def scope_of(user: dict = Depends(current_user)) -> Optional[list]:
    """FastAPI dependency: the caller's scope, worked out once per request."""
    return await patient_scope(user)


def scope_query(scope: Optional[list], field: str = "patient_idx") -> dict:
    return {} if scope is None else {field: {"$in": list(scope)}}


def require_patient(scope: Optional[list], patient_idx: int) -> None:
    # 404, not 403: the same as for a patient that does not exist, so nobody
    # can find out which patients another hospital has.
    if scope is not None and int(patient_idx) not in set(scope):
        raise HTTPException(status_code=404, detail=f"Patient {patient_idx} not found")


def require_cost_view(user: dict = Depends(current_user)) -> dict:
    """FastAPI dependency for the cost and ROI screens."""
    if user["role"] not in COST_VIEW_ROLES:
        raise HTTPException(status_code=403,
                            detail="Cost and ROI views are for hospital administrators and insurers")
    return user
