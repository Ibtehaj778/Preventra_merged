"""
The hospital pages: Overview, Staff, and who looks after each patient.

Mirrors Readmissions/api/hospital.py. All of it is the overview layer (see
core/access.py) - counts, names and assignments - so no reason is asked, and
all of it is limited to the caller's patients by the same scope as every other
route. Doctors and nurses are assigned by their shared_identity account id.
"""

from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException

from core.access import COST_VIEW_ROLES, hospital_of, require_patient, scope_query
from core.mongo import get_db, get_shared_identity_db

HIGH_RISK = 0.75
MAX_BATCH_ASSIGN = 500
_ACCESS_FIELDS = {"_id": 0, "patient_idx": 1, "hospital_id": 1, "insurer_id": 1,
                  "assigned_doctor_id": 1, "assigned_nurse_ids": 1}


def _object_ids(ids) -> list:
    out = []
    for i in ids:
        try:
            out.append(ObjectId(str(i)))
        except (InvalidId, TypeError):
            continue
    return out


def _person(account: dict) -> dict:
    return {"id": str(account["_id"]), "name": account.get("name") or account.get("email", ""),
            "email": account.get("email", "")}


async def _hospital_name(hospital_id: Optional[str]) -> Optional[dict]:
    if not hospital_id:
        return None
    h = await get_shared_identity_db().hospitals.find_one({"_id": hospital_id})
    return {"id": hospital_id, "name": h["name"] if h else hospital_id}


# ------------------------------------------------------------ care teams
async def owners(idxs) -> dict:
    """patient_idx -> its patient_access record."""
    query = {} if idxs is None else {"patient_idx": {"$in": [int(i) for i in idxs]}}
    docs = await get_db().patient_access.find(query, {**_ACCESS_FIELDS, "pharmacy": 1}).to_list(length=None)
    return {int(d["patient_idx"]): d for d in docs}


async def care_teams(idxs) -> dict:
    """patient_idx -> {"doctor", "nurses", "insurer", "pharmacy", "hospital_id"}, with
    names. Three queries however many patients - the list loads all of them."""
    own = await owners(idxs)
    people_ids = {o["assigned_doctor_id"] for o in own.values() if o.get("assigned_doctor_id")}
    people_ids |= {n for o in own.values() for n in (o.get("assigned_nurse_ids") or [])}
    insurer_ids = {o["insurer_id"] for o in own.values() if o.get("insurer_id")}
    ident = get_shared_identity_db()
    people = {str(u["_id"]): _person(u) for u in await ident.users.find(
        {"_id": {"$in": _object_ids(people_ids)}}, {"email": 1, "name": 1}).to_list(length=None)}
    insurers = {i["_id"]: {"id": i["_id"], "name": i.get("name", i["_id"])}
                for i in await ident.insurers.find({"_id": {"$in": list(insurer_ids)}}).to_list(length=None)}
    out = {}
    for idx in idxs:
        o = own.get(int(idx), {})
        out[int(idx)] = {
            "hospital_id": o.get("hospital_id"),
            "doctor": people.get(o.get("assigned_doctor_id")) if o.get("assigned_doctor_id") else None,
            "nurses": [people[n] for n in (o.get("assigned_nurse_ids") or []) if n in people],
            "insurer": insurers.get(o.get("insurer_id")) if o.get("insurer_id") else None,
            "pharmacy": o.get("pharmacy"),
        }
    return out


async def care_filter(scope: Optional[list], doctor: Optional[str] = None,
                      nurse: Optional[str] = None, unassigned: Optional[str] = None) -> Optional[list]:
    """patient_idx values matching a care-team filter, within the scope; None
    when no filter was asked for."""
    if not (doctor or nurse or unassigned):
        return None
    if unassigned in ("doctor", "nurse"):
        # A patient with no patient_access record has nobody either, so this
        # is worked out as "in scope, minus those who have one".
        has_one = ({"assigned_doctor_id": {"$nin": [None, ""]}} if unassigned == "doctor"
                   else {"assigned_nurse_ids.0": {"$exists": True}})
        has = {int(d["patient_idx"]) for d in await get_db().patient_access.find(
            {**scope_query(scope), **has_one}, {"_id": 0, "patient_idx": 1}).to_list(length=None)}
        everyone = scope if scope is not None else [
            int(d["patient_idx"]) for d in await get_db().patients.find(
                {}, {"_id": 0, "patient_idx": 1}).to_list(length=None)]
        return [i for i in everyone if int(i) not in has]
    query = dict(scope_query(scope))
    if doctor:
        query["assigned_doctor_id"] = doctor
    if nurse:
        query["assigned_nurse_ids"] = nurse
    docs = await get_db().patient_access.find(query, {"_id": 0, "patient_idx": 1}).to_list(length=None)
    return [int(d["patient_idx"]) for d in docs]


async def assign(user: dict, scope: Optional[list], patient_idxs: list,
                 doctor_id: Optional[str] = None, nurse_ids: Optional[list] = None,
                 add_nurse_ids: Optional[list] = None) -> dict:
    """Set the doctor and nurses of one or more patients - the same rules as
    Readmissions/api/hospital.assign: None leaves a field, "" clears the
    doctor, every person must be an active account of the patients' hospital,
    and nothing is written unless everything checks out."""
    idxs = list(dict.fromkeys(int(i) for i in (patient_idxs or [])))
    if not idxs:
        raise HTTPException(status_code=422, detail="Choose at least one patient")
    if len(idxs) > MAX_BATCH_ASSIGN:
        raise HTTPException(status_code=422, detail=f"At most {MAX_BATCH_ASSIGN} patients at a time")
    if doctor_id is None and nurse_ids is None and not add_nurse_ids:
        raise HTTPException(status_code=422, detail="Nothing to change")
    for idx in idxs:
        require_patient(scope, idx)

    own = await owners(idxs)
    hospitals = set()
    for idx in idxs:
        hospital = own.get(idx, {}).get("hospital_id")
        if not hospital:
            raise HTTPException(status_code=409, detail=f"Patient {idx} is not in any hospital yet")
        hospitals.add(hospital)
    if len(hospitals) > 1:
        raise HTTPException(status_code=409, detail="Assign one hospital's patients at a time")
    hospital = hospitals.pop()

    users = get_shared_identity_db().users
    doctor_id = doctor_id.strip() if isinstance(doctor_id, str) else doctor_id
    if doctor_id:
        found = await users.find_one({"_id": {"$in": _object_ids([doctor_id])}, "role": "doctor",
                                      "status": "active", "hospital_id": hospital}, {"_id": 1})
        if not found:
            raise HTTPException(status_code=404, detail="Doctor not found in this hospital")
    wanted = [str(n) for n in (nurse_ids or []) + (add_nurse_ids or [])]
    if wanted:
        found = {str(u["_id"]) for u in await users.find(
            {"_id": {"$in": _object_ids(wanted)}, "role": "nurse", "status": "active",
             "hospital_id": hospital}, {"_id": 1}).to_list(length=None)}
        if any(n not in found for n in wanted):
            raise HTTPException(status_code=404, detail="Nurse not found in this hospital")

    update: dict = {"$set": {"care_team_updated_at": datetime.now(timezone.utc),
                             "care_team_updated_by": user.get("email", "")}}
    if doctor_id is not None:
        update["$set"]["assigned_doctor_id"] = doctor_id or None
    if nurse_ids is not None:
        update["$set"]["assigned_nurse_ids"] = list(dict.fromkeys(str(n) for n in nurse_ids))
    elif add_nurse_ids:
        update["$addToSet"] = {"assigned_nurse_ids": {"$each": [str(n) for n in add_nurse_ids]}}
    result = await get_db().patient_access.update_many({"patient_idx": {"$in": idxs}}, update)
    return {"updated": result.matched_count, "patient_ids": idxs}


# --------------------------------------------------------------- overview
async def overview(user: dict, scope: Optional[list]) -> dict:
    """How is my hospital doing - or, for an insurer, how are my members."""
    db = get_db()
    mine = scope_query(scope)
    rows = await db.patients.find(mine, {"_id": 0, "patient_idx": 1, "is_adherent": 1,
                                         "dropout_prob": 1, "assigned_molecule": 1,
                                         "cluster": 1}).to_list(length=None)
    total = len(rows)
    adherent = sum(1 for r in rows if int(r.get("is_adherent") or 0) == 1)
    high_risk = sum(1 for r in rows if float(r.get("dropout_prob") or 0) >= HIGH_RISK)

    drugs: dict = {}
    per_cluster: dict = {}
    for r in rows:
        drug = str(r.get("assigned_molecule") or "UNKNOWN")
        drugs[drug] = drugs.get(drug, 0) + 1
        c = int(r.get("cluster") or 0)
        per_cluster[c] = per_cluster.get(c, 0) + 1
    drug_mix = sorted(({"drug": k, "count": v} for k, v in drugs.items()), key=lambda d: -d["count"])

    own = await owners([r["patient_idx"] for r in rows])
    no_doctor = sum(1 for r in rows if not own.get(int(r["patient_idx"]), {}).get("assigned_doctor_id"))
    no_nurse = sum(1 for r in rows if not own.get(int(r["patient_idx"]), {}).get("assigned_nurse_ids"))
    mix: dict = {}
    for r in rows:
        key = own.get(int(r["patient_idx"]), {}).get("insurer_id")
        mix[key] = mix.get(key, 0) + 1
    names = {i["_id"]: i.get("name", i["_id"]) for i in await get_shared_identity_db().insurers.find(
        {"_id": {"$in": [k for k in mix if k]}}).to_list(length=None)}
    insurer_mix = sorted(({"id": k, "name": names.get(k, k) if k else "No insurer on file",
                           "count": n} for k, n in mix.items()), key=lambda x: -x["count"])

    # Drug spend is a cost figure, so only the roles with the cost screens get
    # it. Per-patient segment economics times this caller's own counts, as the
    # summary does.
    spend = None
    if user["role"] in COST_VIEW_ROLES:
        cea = await db.cost_effectiveness.find({}, {"_id": 0}).to_list(length=None)
        spend = {
            "annual": round(sum(float(d.get("annual_cost") or 0) * per_cluster.get(int(d["cluster"]), 0)
                                for d in cea)),
            "wasted": round(sum(float(d.get("wasted_spend_per_pt") or 0) * per_cluster.get(int(d["cluster"]), 0)
                                for d in cea)),
        }

    hospital = hospital_of(user)
    staff = None
    if user["role"] != "insurer":
        q = {"status": "active"}
        if hospital:
            q["hospital_id"] = hospital
        users = get_shared_identity_db().users
        staff = {"doctors": await users.count_documents({**q, "role": "doctor"}),
                 "nurses": await users.count_documents({**q, "role": "nurse"})}

    return {
        "hospital": await _hospital_name(hospital),
        "total_patients": total,
        "adherent": adherent,
        "non_adherent": total - adherent,
        "high_risk": high_risk,
        "high_risk_threshold": HIGH_RISK,
        "drug_mix": drug_mix,
        "drug_spend": spend,
        "no_doctor": no_doctor,
        "no_nurse": no_nurse,
        "insurer_mix": insurer_mix,
        "staff": staff,
    }


# ------------------------------------------------------------------ staff
async def staff(user: dict, scope: Optional[list]) -> dict:
    """Doctors and nurses with their patient and non-adherent counts."""
    db = get_db()
    hospital = hospital_of(user)
    q = {"status": "active"}
    if hospital:
        q["hospital_id"] = hospital

    rows = await db.patients.find(scope_query(scope), {"_id": 0, "patient_idx": 1, "is_adherent": 1,
                                                       "dropout_prob": 1}).to_list(length=None)
    non_adherent = {int(r["patient_idx"]) for r in rows if int(r.get("is_adherent") or 0) == 0}
    high = {int(r["patient_idx"]) for r in rows if float(r.get("dropout_prob") or 0) >= HIGH_RISK}
    everyone = {int(r["patient_idx"]) for r in rows}

    by_doctor: dict = {}
    by_nurse: dict = {}
    for o in (await owners([r["patient_idx"] for r in rows])).values():
        idx = int(o["patient_idx"])
        if o.get("assigned_doctor_id"):
            by_doctor.setdefault(o["assigned_doctor_id"], set()).add(idx)
        for n in o.get("assigned_nurse_ids") or []:
            by_nurse.setdefault(str(n), set()).add(idx)

    def counts(idxs: set) -> dict:
        return {"patients": len(idxs), "non_adherent": len(idxs & non_adherent),
                "high_risk": len(idxs & high)}

    users = get_shared_identity_db().users
    doctors = [{**_person(a), "hospital_id": a.get("hospital_id"),
                **counts(by_doctor.get(str(a["_id"]), set()))}
               for a in await users.find({**q, "role": "doctor"}).sort("email", 1).to_list(length=None)]
    nurses = [{**_person(a), "hospital_id": a.get("hospital_id"),
               **counts(by_nurse.get(str(a["_id"]), set()))}
              for a in await users.find({**q, "role": "nurse"}).sort("email", 1).to_list(length=None)]
    with_doctor = {i for s in by_doctor.values() for i in s}
    with_nurse = {i for s in by_nurse.values() for i in s}
    return {
        "hospital": await _hospital_name(hospital),
        "doctors": doctors,
        "nurses": nurses,
        "no_doctor": len(everyone - with_doctor),
        "no_nurse": len(everyone - with_nurse),
    }
