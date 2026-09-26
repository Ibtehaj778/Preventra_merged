"""Who may see which patients, and do what - decided here and nowhere else.

Ownership lives on each patient's `care_actions` record, the per-patient record
that already holds the assigned doctor and coordinator. It survives the
worklist being rebuilt by scripts/load_mimic_to_mongo.py, which the worklist
itself does not:

    hospital_id         the hospital the patient belongs to
    insurer_id          who pays for them
    assigned_doctor_id  a doctor_id in the `doctors` registry (unchanged)
    assigned_nurse_ids  shared_identity user ids
    patient_account_id  the patient's own login, if they have one

A doctor login is matched to its registry entry by email, the registry's
natural key, so no second id is introduced.

What each role sees:

    superadmin                    everything
    hospital_admin, case_manager  their hospital
    doctor                        their hospital's patients assigned to them
    nurse                         their hospital's patients assigned to them
    insurer                       their members, in any hospital
    patient                       their own record
    anyone without a placement    nothing

A patient with no ownership record is visible to the superadmin only; the seed
script and every create path write one.
"""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException

# Collections holding one or more rows per patient, keyed by patient_id. Reads
# through a ScopedDB are limited to the caller's patients on all of them.
PATIENT_COLLECTIONS = ("patient_worklist", "weekly_monitoring", "care_actions", "alerts",
                       "clinical_alerts", "risk_registry", "notifications")

# Which roles may do each kind of change. Reading is governed by the scope
# alone; insurers and patients are read-only.
ACTIONS = {
    "add_notes":      ("superadmin", "doctor", "nurse", "case_manager"),
    "edit_patients":  ("superadmin", "hospital_admin", "doctor", "nurse", "case_manager"),
    "assign":         ("superadmin", "hospital_admin", "case_manager"),
    "add_patients":   ("superadmin", "hospital_admin"),
    "manage_doctors": ("superadmin", "hospital_admin"),
    "respond_alerts": ("superadmin", "doctor", "nurse", "case_manager"),
    # A forecast sweep scans and writes alerts for the whole cohort, every
    # hospital at once, so it stays with our team until it can run per hospital.
    "run_sweeps":     ("superadmin",),
    "clear_cache":    ("superadmin",),
}


def require(user: dict, action: str) -> None:
    if user["role"] not in ACTIONS[action]:
        raise HTTPException(status_code=403, detail=f"A {user['role']} cannot {action.replace('_', ' ')}")


def _doctor_ids_for(db, user: dict) -> list:
    return [d["doctor_id"] for d in db["doctors"].find({"email": user.get("email", "")},
                                                       {"doctor_id": 1})]


def patient_scope(db, user: dict) -> Optional[list]:
    """The patient_ids this user may see, or None for no restriction."""
    role, hospital, uid = user["role"], user.get("hospital_id"), str(user["_id"])
    if role == "superadmin":
        return None
    if role in ("hospital_admin", "case_manager"):
        query = {"hospital_id": hospital} if hospital else None
    elif role == "doctor":
        doctor_ids = _doctor_ids_for(db, user)
        query = ({"hospital_id": hospital, "assigned_doctor_id": {"$in": doctor_ids}}
                 if hospital and doctor_ids else None)
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
    return [d["patient_id"] for d in db["care_actions"].find(query, {"patient_id": 1})]


def id_variants(ids) -> list:
    """Each id in both stored forms. Patient ids are strings ("MIMIC-12345"),
    but older data stored plain numbers, and a browser always sends strings."""
    out = []
    for pid in ids:
        out.append(pid)
        text = str(pid)
        if text.lstrip("-").isdigit():
            out.append(int(text) if isinstance(pid, str) else text)
    return out


def scope_query(scope: Optional[list], field: str = "patient_id") -> dict:
    return {} if scope is None else {field: {"$in": id_variants(scope)}}


def in_scope(scope: Optional[list], patient_id) -> bool:
    return scope is None or str(patient_id) in {str(p) for p in scope}


def require_patient(scope: Optional[list], patient_id) -> None:
    # 404, not 403: the same answer as for a patient that does not exist, so
    # nobody can find out which ids exist in another hospital.
    if not in_scope(scope, patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")


def doctor_query(user: dict) -> dict:
    """Which registry doctors this user may see: their hospital's."""
    if user["role"] == "superadmin":
        return {}
    return {"hospital_id": user.get("hospital_id") or "__none__"}


# ------------------------------------------------------------ scoped reads
def _and(query: Optional[dict], extra: dict) -> dict:
    if not extra:
        return query or {}
    return {"$and": [query or {}, extra]}


class ScopedCollection:
    """Read-only view of one collection, limited to the caller's patients.

    Writes are deliberately absent: an update or upsert through a filtered view
    would silently create a row for a patient the caller cannot see. Code that
    changes a patient checks it with require_patient() and writes to the real
    collection.
    """

    def __init__(self, collection, restriction: dict):
        self._c = collection
        self._r = restriction

    def find(self, filter=None, *args, **kwargs):
        return self._c.find(_and(filter, self._r), *args, **kwargs)

    def find_one(self, filter=None, *args, **kwargs):
        return self._c.find_one(_and(filter, self._r), *args, **kwargs)

    def count_documents(self, filter, *args, **kwargs):
        return self._c.count_documents(_and(filter, self._r), *args, **kwargs)

    def aggregate(self, pipeline, *args, **kwargs):
        stages = ([{"$match": self._r}] if self._r else []) + list(pipeline)
        return self._c.aggregate(stages, *args, **kwargs)

    def distinct(self, key, filter=None, *args, **kwargs):
        return self._c.distinct(key, _and(filter, self._r), *args, **kwargs)


class ScopedDB:
    """A database handle whose patient collections only show the caller's
    patients, and whose doctor registry only shows the caller's hospital.
    Everything else passes through untouched."""

    def __init__(self, db, user: dict, scope: Optional[list]):
        self._db = db
        self.user = user
        self.scope = scope
        self.client = db.client

    def __getitem__(self, name):
        if name in PATIENT_COLLECTIONS:
            return ScopedCollection(self._db[name], scope_query(self.scope))
        if name == "doctors":
            return ScopedCollection(self._db[name], doctor_query(self.user))
        return self._db[name]

    def __getattr__(self, name):
        return self[name]


def scoped(db, user: dict) -> ScopedDB:
    return ScopedDB(db, user, patient_scope(db, user))
