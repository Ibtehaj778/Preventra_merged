"""scripts/demo_patient_logins.py, over the real 7,566 patients in memory.

The point of these tests: the logins work, each one sees only its own record,
and the GLP-1 dataset is never changed.
"""
import copy
import time
from pathlib import Path

import bcrypt
import mongomock
import pytest
from fastapi.testclient import TestClient
from jose import jwt
from mongomock_motor import AsyncMongoMockClient

import main
from core import mongo
from core.config import settings
from scripts import demo_patient_logins as demo
from scripts import migrate_csv_to_mongo as mig

HID = "demo-hospital"


def snapshot(collection):
    return sorted((copy.deepcopy(d) for d in collection.find({}, {"_id": 0})),
                  key=lambda d: d.get("patient_idx", 0))


@pytest.fixture()
def world():
    store = mongomock.MongoClient()
    db = store[settings.mongodb_db_name]
    mig.migrate_patients(db, Path(settings.data_dir))
    ident = store[settings.shared_identity_db_name]
    ident.hospitals.insert_many([{"_id": HID, "name": "Demo Hospital"},
                                 {"_id": "other-hospital", "name": "Other Hospital"}])
    # The seed script's Readmissions-style demo patient, already linked to #0.
    seeded = str(ident.users.insert_one({"email": f"patient1@{HID}.test", "role": "patient",
                                         "status": "active", "hospital_id": HID}).inserted_id)
    idxs = [int(d["patient_idx"]) for d in db.patients.find({}, {"patient_idx": 1})]
    db.patient_access.insert_many(
        [{"patient_idx": i, "hospital_id": HID if i % 5 else "other-hospital",
          **({"patient_account_id": seeded} if i == 0 else {})} for i in idxs])
    return {"store": store, "db": db, "ident": ident, "seeded": seeded}


def test_dry_run_writes_nothing(world):
    users_before = world["ident"].users.count_documents({})
    access_before = snapshot(world["db"].patient_access)
    rows = demo.run(world["store"], "Demo Hospital", 20, "whatever", dry=True)
    assert len(rows) == 20
    assert world["ident"].users.count_documents({}) == users_before
    assert snapshot(world["db"].patient_access) == access_before


def test_logins_are_created_and_the_dataset_is_untouched(world):
    patients_before = snapshot(world["db"].patients)
    rows = demo.run(world["store"], "Demo Hospital", 20, "123123123", dry=False)

    # Talha's collection: byte-for-byte the same.
    assert snapshot(world["db"].patients) == patients_before

    assert len(rows) == 20
    assert {r[2] for r in rows} == {"Critical", "High", "Medium", "Low"}      # varied risk
    assert len({r[3] for r in rows}) >= 3                                        # varied segments
    for email, idx, *_ in rows:
        account = world["ident"].users.find_one({"email": email})
        assert account["role"] == "patient" and account["status"] == "active"
        assert account["hospital_id"] == HID and account["app_access"] == ["glp1"]
        assert bcrypt.checkpw(b"123123123", account["password_hash"].encode())
        rec = world["db"].patient_access.find_one({"patient_idx": idx})
        assert rec["hospital_id"] == HID                       # only this hospital's patients
        assert rec["patient_account_id"] == str(account["_id"])
    # One record per login, and the seeded patient1 keeps #0.
    assert len({r[1] for r in rows}) == 20 and 0 not in {r[1] for r in rows}
    assert world["db"].patient_access.find_one({"patient_idx": 0})["patient_account_id"] == world["seeded"]
    # Nothing else in patient_access changed: only 20 records gained a login.
    assert world["db"].patient_access.count_documents({"patient_account_id": {"$exists": True}}) == 21


def test_rerun_keeps_every_login_on_its_record(world):
    first = demo.run(world["store"], "Demo Hospital", 20, "123123123", dry=False)
    count = world["ident"].users.count_documents({})
    second = demo.run(world["store"], "Demo Hospital", 20, "new-password-9", dry=False)
    assert [(r[0], r[1]) for r in first] == [(r[0], r[1]) for r in second]
    assert all(r[4] == "existing" for r in second)
    assert world["ident"].users.count_documents({}) == count
    acc = world["ident"].users.find_one({"email": first[0][0]})
    assert bcrypt.checkpw(b"new-password-9", acc["password_hash"].encode())


def test_a_demo_patient_sees_only_their_own_record(world):
    rows = demo.run(world["store"], "Demo Hospital", 3, "123123123", dry=False)
    email, idx = rows[0][0], rows[0][1]
    uid = str(world["ident"].users.find_one({"email": email})["_id"])
    token = jwt.encode({"sub": uid, "exp": int(time.time()) + 3600},
                       settings.shared_secret_key, algorithm="HS256")
    previous = mongo._client
    mongo._client = AsyncMongoMockClient(mock_mongo_client=world["store"])
    try:
        c = TestClient(main.app, headers={"Authorization": f"Bearer {token}"}, raise_server_exceptions=False)
        listed = c.get("/api/patients", params={"page_size": 100}).json()
        assert [p["patient_idx"] for p in listed["patients"]] == [idx]
        assert c.get(f"/api/patients/{idx}").status_code == 200
        assert c.get(f"/api/patients/{rows[1][1]}").status_code == 404     # another demo patient
    finally:
        mongo._client = previous


def test_unknown_hospital_changes_nothing(world):
    with pytest.raises(SystemExit):
        demo.run(world["store"], "Nowhere General", 5, "123123123", dry=False)
    assert world["ident"].users.count_documents({}) == 1