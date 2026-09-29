"""
Give some GLP-1 patients a demo login, so a demo can show what a patient sees.

WHAT IT DOES
------------
Picks N patients (default 20) who are already placed in the hospital you name,
spread across the dropout-risk bands (critical, high, medium, low) and the four
segments, and gives each one a login:

    glp1.patient1@<hospital-id>.test ... glp1.patientN@<hospital-id>.test

A patient login opens GLP-1 only and sees its own record, nothing else
(core/access.py). These are separate from the Readmissions demo patients
(patient1@..., made by Readmissions/scripts), so no login mixes two datasets.

WHAT IT WRITES - and nothing else
---------------------------------
  shared_identity.users           the N patient accounts (active, GLP-1 only)
  glp1_analytics.patient_access   `patient_account_id` on the N chosen records

WHAT IT NEVER CHANGES
---------------------
The patients collection and every table built from the GLP-1 dataset. The
patients collection is only read, to see each patient's risk and segment. The
hospital must already exist and its patients must already be placed in it
(Readmissions/scripts/seed_hospital.py): nobody is moved, and no doctor, nurse,
insurer or pharmacy is changed.

Re-running is safe: an existing demo login keeps its record and gets the new
password, and no record is ever given two logins.

Run from GLP1/Backend, with its .env (MONGODB_URI, SHARED_IDENTITY_DB_NAME).
Needs bcrypt:  pip install bcrypt

    python -m scripts.demo_patient_logins --hospital "Your Hospital Name" --dry-run
    python -m scripts.demo_patient_logins --hospital "Your Hospital Name"
"""
from __future__ import annotations

import argparse
import getpass
import re
import sys
from datetime import datetime, timezone
from typing import Optional

from pymongo import MongoClient

from core.config import settings

CREATED_BY = "GLP1/Backend/scripts/demo_patient_logins.py"

# Must match Readmissions/api/auth.py, which checks these passwords at sign-in.
MIN_PASSWORD_LENGTH = 8
BCRYPT_ROUNDS = 12

# Same thresholds as the Patients page (PatientRiskPanel.jsx).
BANDS = (("Critical", 0.75), ("High", 0.50), ("Medium", 0.25), ("Low", 0.0))
SEGMENTS = ("Low Urgency Dropout", "Financial Barrier Dropout",
            "Low Friction Adherer", "Moderate Risk Adherer")


def band_of(prob) -> str:
    p = float(prob or 0)
    return next(name for name, floor in BANDS if p >= floor)


def segment_of(cluster) -> str:
    try:
        return SEGMENTS[int(cluster)]
    except (TypeError, ValueError, IndexError):
        return "Unknown"


def slugify(name: str) -> str:
    """As Readmissions/api/auth.py:slugify_org - "City Hospital" -> "city-hospital"."""
    return re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-") or "unaffiliated"


def now() -> str:
    """As Readmissions/api/auth.py:_now."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def hash_password(password: str) -> str:
    import bcrypt                        # only needed for a real run
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode()


def find_hospital(hospitals, name: str) -> Optional[dict]:
    """By id, by the id its name would get, or by name in any case."""
    wanted = (name or "").strip()
    return (hospitals.find_one({"_id": wanted})
            or hospitals.find_one({"_id": slugify(wanted)})
            or hospitals.find_one({"name": {"$regex": f"^{re.escape(wanted)}$", "$options": "i"}}))


def pick(candidates: list, n: int) -> list:
    """n patients: critical, high, medium and low risk in turn, and within each
    band one segment after another, so the demo shows a range of patients.
    Deterministic: the same data always gives the same picks."""
    queues = []
    for band, _ in BANDS:
        by_segment: dict = {}
        for p in sorted(candidates, key=lambda p: int(p["patient_idx"])):
            if band_of(p.get("dropout_prob")) == band:
                by_segment.setdefault(segment_of(p.get("cluster")), []).append(p)
        mixed, lists = [], [by_segment[k] for k in sorted(by_segment)]
        while any(lists):
            for lst in lists:
                if lst:
                    mixed.append(lst.pop(0))
        queues.append(mixed)
    picked = []
    while len(picked) < n and any(queues):
        for q in queues:
            if q and len(picked) < n:
                picked.append(q.pop(0))
    return picked


def run(client: MongoClient, hospital: str, logins: int, password: str, dry: bool) -> list:
    """Create or refresh the demo logins. Returns one row per login:
    (email, patient_idx, band, segment, "new" | "existing")."""
    identity = client[settings.shared_identity_db_name]
    glp1 = client[settings.mongodb_db_name]
    users, access = identity["users"], glp1["patient_access"]

    found = find_hospital(identity["hospitals"], hospital)
    if not found:
        names = ", ".join(f'"{h.get("name", h["_id"])}"' for h in identity["hospitals"].find()) or "none"
        sys.exit(f"  No hospital called \"{hospital}\". Hospitals: {names}. Nothing changed.")
    hid = found["_id"]

    placed = list(access.find({"hospital_id": hid}, {"_id": 0, "patient_idx": 1, "patient_account_id": 1}))
    if not placed:
        sys.exit(f"  No GLP-1 patients are placed in {hid} yet - run "
                 "Readmissions/scripts/seed_hospital.py first. Nothing changed.")
    linked = {str(a["patient_account_id"]): int(a["patient_idx"]) for a in placed if a.get("patient_account_id")}
    free = [int(a["patient_idx"]) for a in placed if not a.get("patient_account_id")]

    # Read-only: each free patient's risk and segment, to choose a varied set.
    risk = {int(p["patient_idx"]): p for p in glp1["patients"].find(
        {"patient_idx": {"$in": free}}, {"_id": 0, "patient_idx": 1, "dropout_prob": 1, "cluster": 1})}
    fresh = iter(pick(list(risk.values()), logins))
    password_hash = None if dry else hash_password(password)

    rows = []
    for i in range(1, logins + 1):
        email = f"glp1.patient{i}@{hid}.test"
        account = users.find_one({"email": email})
        if account and account.get("role") != "patient":
            print(f"  {email} is a {account.get('role')} login; skipped")
            continue
        uid = str(account["_id"]) if account else None
        idx = linked.get(uid) if uid else None
        if idx is None:
            chosen = next(fresh, None)
            if chosen is None:
                print(f"  No unlinked patients left in {hid}; stopped at {len(rows)} logins")
                break
            idx = int(chosen["patient_idx"])

        if not dry:
            if account:
                users.update_one({"_id": account["_id"]}, {"$set": {
                    "password_hash": password_hash, "status": "active", "hospital_id": hid,
                    "must_change_password": False, "updated_at": now()}})
            else:
                uid = str(users.insert_one({
                    "email": email, "password_hash": password_hash, "name": f"GLP-1 Demo Patient {i}",
                    "role": "patient", "status": "active", "hospital_id": hid, "insurer_id": None,
                    "must_change_password": False, "app_access": ["glp1"],
                    "created_at": now(), "created_by": CREATED_BY}).inserted_id)
            # Only a record with no login yet (or already this one) is linked.
            access.update_one({"patient_idx": idx, "hospital_id": hid,
                               "patient_account_id": {"$in": [None, uid]}},
                              {"$set": {"patient_account_id": uid}})

        p = risk.get(idx) or glp1["patients"].find_one({"patient_idx": idx},
                                                        {"_id": 0, "dropout_prob": 1, "cluster": 1}) or {}
        rows.append((email, idx, band_of(p.get("dropout_prob")), segment_of(p.get("cluster")),
                     "existing" if account else "new"))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.strip().split("\n\n")[0])
    parser.add_argument("--hospital", required=True, help="hospital name or id (must exist)")
    parser.add_argument("--logins", type=int, default=20, help="how many patient logins (default 20)")
    parser.add_argument("--dry-run", action="store_true", help="report without writing anything")
    args = parser.parse_args()
    dry = args.dry_run
    tag = "[dry run] " if dry else ""

    password = "dry-run-password" if dry else getpass.getpass("Password for the patient logins (min 8): ")
    if len(password) < MIN_PASSWORD_LENGTH:
        sys.exit("  Password too short; nothing changed.")

    rows = run(MongoClient(settings.mongodb_uri), args.hospital, args.logins, password, dry)
    width = max([len(r[0]) for r in rows] + [5])
    print(f"\n  {tag}{len(rows)} GLP-1 patient logins - sign in at the Portal, open GLP-1:")
    print(f"    {'email'.ljust(width)}  {'patient':<9}{'risk':<10}segment")
    for email, idx, band, segment, state in rows:
        note = (f"  (already existed; password {'would be ' if dry else ''}updated)"
                if state == "existing" else "")
        print(f"    {email.ljust(width)}  #{idx:<8}{band:<10}{segment}{note}")
    print(f"\n  {'Dry run: nothing written.' if dry else 'Done. Every login uses the password you typed.'}")


if __name__ == "__main__":
    main()