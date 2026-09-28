"""
Put every Readmissions patient in one hospital, and give some of them a login
so a demo can show what a patient sees.

WHAT IT DOES
------------
1. Every Readmissions patient - everyone on the worklist, and anyone with a
   care record - is placed in the hospital you name. A patient who was in
   another hospital is moved, and that hospital's doctor and nurses come off
   them: staff only ever look after their own hospital's patients
   (api/access.py).
2. A patient without a doctor gets one of the hospital's registered doctors,
   matched on the patient's condition the way alerts are routed; a patient
   without a nurse gets one of its nurses, in turn. Assignments already made
   are kept.
3. N patient logins, patient1@<hospital>.test to patientN@<hospital>.test,
   each linked to one patient on the current worklist - high, medium and low
   risk in turn, the fullest records first, across conditions. A patient login
   sees that record and nothing else, in Readmissions only.

All N logins get the password you type, including the demo patients
seed_hospital.py made (patient1, patient2), which keep their record. The
hospital must already exist; this never creates one. Re-running links nobody
twice.

    .venv/bin/python scripts/demo_patient_logins.py --hospital "Your Hospital Name" --dry-run
    .venv/bin/python scripts/demo_patient_logins.py --hospital "Your Hospital Name"
"""
from __future__ import annotations

import argparse
import getpass
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from pymongo import InsertOne, UpdateOne

from api import auth
from api.db_utils import get_db_name, get_latest_batch_date, get_mongo_client
from scripts.seed_hospital import stable_bucket

BANDS = ("High", "Medium", "Low")
CREATED_BY = "scripts/demo_patient_logins.py"


def find_hospital(hospitals, name: str):
    """By id, by the id its name would get, or by name in any case."""
    wanted = (name or "").strip()
    return (hospitals.find_one({"_id": wanted})
            or hospitals.find_one({"_id": auth.slugify_org(wanted)})
            or hospitals.find_one({"name": {"$regex": f"^{re.escape(wanted)}$", "$options": "i"}}))


def band_of(row: dict) -> str:
    return row.get("current_band") or row.get("risk_band") or "Low"


def pick_records(rows: list, n: int, taken: set) -> list:
    """n worklist rows for demo logins: high, medium and low risk in turn;
    within a band the fullest records first (a diagnosis, the most weeks of
    monitoring), one condition after another so the demo is not all heart
    failure."""
    rows = sorted((r for r in rows if str(r["patient_id"]) not in taken),
                  key=lambda r: (not r.get("primary_diagnosis"), -(r.get("weeks_tracked") or 0),
                                 str(r["patient_id"])))
    queues = []
    for band in BANDS + tuple(sorted({band_of(r) for r in rows} - set(BANDS))):
        by_group: dict = {}
        for r in rows:
            if band_of(r) == band:
                by_group.setdefault(r.get("clinical_group") or "", []).append(r)
        varied, groups = [], list(by_group.values())
        while any(groups):
            for g in groups:
                if g:
                    varied.append(g.pop(0))
        queues.append(varied)
    picked = []
    while len(picked) < n and any(queues):
        for q in queues:
            if q and len(picked) < n:
                picked.append(q.pop(0))
    return picked


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.strip().split("\n\n")[0])
    parser.add_argument("--hospital", required=True, help="hospital name or id (must exist)")
    parser.add_argument("--logins", type=int, default=20, help="how many patient logins (default 20)")
    parser.add_argument("--dry-run", action="store_true", help="report without writing anything")
    args = parser.parse_args()
    dry = args.dry_run
    tag = "[dry run] " if dry else ""

    load_dotenv()
    client = get_mongo_client(os.environ.get("MONGO_URI", "mongodb://localhost:27017"))
    readm = client[get_db_name()]
    identity = client[auth.IDENTITY_DB]
    users = auth.users(readm)

    hospital = find_hospital(identity["hospitals"], args.hospital)
    if not hospital:
        names = ", ".join(f'"{h.get("name", h["_id"])}"' for h in identity["hospitals"].find()) or "none"
        sys.exit(f"  No hospital called \"{args.hospital}\". Hospitals: {names}. Nothing changed.")
    hid = hospital["_id"]
    print(f"  Hospital: {hospital.get('name', hid)} ({hid})")

    password = "dry-run-password" if dry else getpass.getpass("Password for the patient logins (min 8): ")
    if len(password) < auth.MIN_PASSWORD_LENGTH:
        sys.exit("  Password too short; nothing changed.")

    # ---- 1. every patient into the hospital -----------------------------
    batch = get_latest_batch_date(readm, "patient_worklist")
    latest = list(readm["patient_worklist"].find(
        {"batch_date": batch} if batch else {},
        {"_id": 0, "patient_id": 1, "current_band": 1, "risk_band": 1, "weeks_tracked": 1,
         "clinical_group": 1, "group_label": 1, "primary_diagnosis": 1}))
    groups = {str(r["patient_id"]): r.get("clinical_group") for r in latest}
    # The stored form of each id (older rows hold numbers), so a new care record
    # matches the worklist exactly.
    on_worklist = {str(p): p for p in readm["patient_worklist"].distinct("patient_id")}
    care = list(readm["care_actions"].find(
        {}, {"patient_id": 1, "hospital_id": 1, "assigned_doctor_id": 1,
             "assigned_nurse_ids": 1, "patient_account_id": 1}))
    covered = {str(r["patient_id"]) for r in care}
    new_ids = sorted(set(on_worklist) - covered)
    care += [{"patient_id": on_worklist[pid], "notes": [], "coordinator_name": None,
              "assigned_at": None, "hospital_id": hid} for pid in new_ids]

    doctors = list(readm["doctors"].find({"hospital_id": hid},
                                         {"doctor_id": 1, "clinical_groups": 1, "active": 1}))
    its_doctors = {d["doctor_id"] for d in doctors}
    active_doctors = sorted((d for d in doctors if d.get("active", True)), key=lambda d: d["doctor_id"])
    nurses = list(users.find({"role": "nurse", "hospital_id": hid}, {"status": 1}))
    its_nurses = {str(u["_id"]) for u in nurses}
    active_nurses = sorted(str(u["_id"]) for u in nurses if u.get("status") == "active")

    def doctor_for(pid: str):
        group = groups.get(pid)
        for match in ([d for d in active_doctors if group and group in (d.get("clinical_groups") or [])],
                      [d for d in active_doctors if "general" in (d.get("clinical_groups") or [])],
                      active_doctors):
            if match:
                return match[stable_bucket(pid, len(match))]["doctor_id"]
        return None

    ops, moved_from, records = [], Counter(), {}
    counts = Counter(new=len(new_ids))
    for n, rec in enumerate(care):
        pid = str(rec["patient_id"])
        change: dict = {}
        if rec.get("hospital_id") != hid:
            moved_from[rec.get("hospital_id") or "no hospital"] += 1
            change["hospital_id"] = hid
            if rec.get("assigned_doctor_id") and rec["assigned_doctor_id"] not in its_doctors:
                change["assigned_doctor_id"] = None
            nurse_ids = [str(x) for x in rec.get("assigned_nurse_ids") or []]
            if [x for x in nurse_ids if x not in its_nurses]:
                change["assigned_nurse_ids"] = [x for x in nurse_ids if x in its_nurses]

        doctor = doctor_for(pid)
        if not change.get("assigned_doctor_id", rec.get("assigned_doctor_id")) and doctor:
            change["assigned_doctor_id"] = doctor
            counts["doctor"] += 1
        if not change.get("assigned_nurse_ids", rec.get("assigned_nurse_ids")) and active_nurses:
            change["assigned_nurse_ids"] = [active_nurses[n % len(active_nurses)]]
            counts["nurse"] += 1

        if "_id" not in rec:
            ops.append(InsertOne({**rec, **change}))
        elif change:
            ops.append(UpdateOne({"_id": rec["_id"]}, {"$set": change}))
        records[pid] = {**rec, **change}

    total = len(records)
    moved = ", ".join(f"{k}: {v:,}" for k, v in moved_from.most_common()) or "none"
    print(f"  {tag}Patients: {total:,} in {hid}; moved from another hospital - {moved}; "
          f"{counts['new']:,} had no care record")
    print(f"  {tag}Care team: {counts['doctor']:,} given a doctor ({len(active_doctors)} in the hospital), "
          f"{counts['nurse']:,} given a nurse ({len(active_nurses)} in the hospital)")
    if not dry:
        for i in range(0, len(ops), 1000):
            readm["care_actions"].bulk_write(ops[i:i + 1000], ordered=False)

    # ---- 2. the patient logins ------------------------------------------
    current = {str(r["patient_id"]) for r in latest}
    linked = {str(r["patient_account_id"]): pid for pid, r in records.items()
              if r.get("patient_account_id")}
    taken = set(linked.values())
    logins, accounts, i = [], [], 0
    while len(accounts) < args.logins and i < args.logins + 100:
        i += 1
        email = f"patient{i}@{hid}.test"
        account = users.find_one({"email": email})
        if account and account.get("role") != "patient":
            print(f"  {email} is a {account.get('role')} login; skipped")
            continue
        accounts.append((i, email, account))

    fresh = iter(pick_records(latest, args.logins, taken))
    for i, email, account in accounts:
        uid = str(account["_id"]) if account else None
        pid = linked.get(uid) if uid else None
        if pid and pid not in current:            # its record left the worklist
            if not dry:
                readm["care_actions"].update_one({"patient_id": records[pid]["patient_id"]},
                                                 {"$set": {"patient_account_id": None}})
            pid = None
        if pid is None:
            row = next(fresh, None)
            if row is None:
                print(f"  No unlinked patients left on the worklist; stopped at {len(logins)} logins")
                break
            pid = str(row["patient_id"])
        if dry:
            uid = uid or f"(new:{email})"
        elif account:
            users.update_one({"_id": account["_id"]}, {"$set": {
                "password_hash": auth.hash_password(password), "status": "active", "hospital_id": hid,
                "must_change_password": False, "updated_at": auth._now()}})
        else:
            uid = str(users.insert_one({
                "email": email, "password_hash": auth.hash_password(password), "name": f"Demo Patient {i}",
                "role": "patient", "status": "active", "hospital_id": hid, "insurer_id": None,
                "must_change_password": False, "app_access": ["readmissions"],
                "created_at": auth._now(), "created_by": CREATED_BY}).inserted_id)
        if not dry:
            readm["care_actions"].update_one({"patient_id": records[pid]["patient_id"]},
                                             {"$set": {"patient_account_id": uid}})
        logins.append((email, pid, "existing" if account else "new"))

    rows = {str(r["patient_id"]): r for r in latest}
    width = max([len(e) for e, _, _ in logins] + [5])
    print(f"\n  {tag}{len(logins)} patient logins - sign in at the Portal, open Readmissions:")
    print(f"    {'email'.ljust(width)}  {'record':<16}{'risk':<8}condition")
    for email, pid, state in logins:
        row = rows.get(pid, {})
        note = (f"  (already existed; password {'would be ' if dry else ''}updated)"
                if state == "existing" else "")
        print(f"    {email.ljust(width)}  {pid:<16}{band_of(row):<8}"
              f"{row.get('group_label') or row.get('primary_diagnosis') or ''}{note}")
    print(f"\n  {'Dry run: nothing written.' if dry else 'Done. Every login uses the password you typed.'}")


if __name__ == "__main__":
    main()
