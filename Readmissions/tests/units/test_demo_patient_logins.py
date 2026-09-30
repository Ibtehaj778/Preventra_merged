"""scripts/demo_patient_logins.py: every patient ends up in the hospital with
its own staff, and each demo login sees exactly one current record."""
import os
import sys
from collections import Counter

import mongomock
import pytest
from fastapi.testclient import TestClient

from api import access, auth
from scripts import demo_patient_logins as script

HID, OTHER = "your-hospital-name", "other-hospital"
LATEST, PRIOR = "2026-04-29", "2026-04-22"
GROUPS = ["respiratory", "heart_failure", "diabetes", "general"]
BANDS = ["High", "Medium", "Low"]
LATEST_IDS = [f"MIMIC-{100 + i}" for i in range(36)]
GONE = "MIMIC-900"                                   # left the worklist
PASSWORD, OLD_PASSWORD = "demo-password-1", "seed-password-1"


def row(i, pid, batch):
    band = BANDS[i % 3]
    score = {"High": 80, "Medium": 50, "Low": 20}[band]
    return {"patient_id": pid, "batch_date": batch, "risk_score": score, "risk_band": band,
            "current_score": score, "current_band": band, "clinical_group": GROUPS[i % 4],
            "clinical_groups": [GROUPS[i % 4]], "group_label": GROUPS[i % 4].replace("_", " "),
            "primary_diagnosis": "Something treated", "weeks_tracked": i % 5 + 1,
            "discharge_date": "2026-04-10", "monitoring_status": "stable"}


@pytest.fixture
def client(monkeypatch):
    c = mongomock.MongoClient()
    readm, ident = c["neuroshield"], c["shared_identity"]
    ident.hospitals.insert_many([{"_id": HID, "name": "Your Hospital Name"},
                                 {"_id": OTHER, "name": "Other Hospital"}])
    for i, pid in enumerate(LATEST_IDS):
        readm.patient_worklist.insert_many([row(i, pid, LATEST), row(i, pid, PRIOR)])
    readm.patient_worklist.insert_one(row(0, GONE, PRIOR))

    readm.doctors.insert_many([
        {"doctor_id": "DR-YH-CARD", "hospital_id": HID, "clinical_groups": ["heart_failure"], "active": True},
        {"doctor_id": "DR-YH-MED", "hospital_id": HID, "clinical_groups": ["general"], "active": True},
        {"doctor_id": "DR-OTHER", "hospital_id": OTHER, "clinical_groups": ["heart_failure"], "active": True},
    ])
    users = ident.users
    nurse = lambda email, hosp: str(users.insert_one(
        {"email": email, "role": "nurse", "status": "active", "hospital_id": hosp}).inserted_id)
    ids = {"n1": nurse("n1@yh.test", HID), "n2": nurse("n2@yh.test", HID),
           "n_other": nurse("n@other.test", OTHER)}
    monkeypatch.setattr(auth, "BCRYPT_ROUNDS", 4)
    monkeypatch.setattr(auth, "SHARED_SECRET_KEY", "test-secret-not-the-real-one")
    for i in (1, 2):                                  # what seed_hospital.py made
        ids[f"patient{i}"] = str(users.insert_one(
            {"email": f"patient{i}@{HID}.test", "role": "patient", "status": "active",
             "hospital_id": HID, "password_hash": auth.hash_password(OLD_PASSWORD),
             "app_access": ["glp1", "readmissions"], "must_change_password": False,
             "created_by": "scripts/seed_hospital.py"}).inserted_id)

    readm.care_actions.insert_many([
        {"patient_id": "MIMIC-100", "hospital_id": HID, "assigned_doctor_id": "DR-YH-MED",
         "assigned_nurse_ids": [ids["n2"]]},
        {"patient_id": "MIMIC-101", "hospital_id": OTHER, "assigned_doctor_id": "DR-OTHER",
         "assigned_nurse_ids": [ids["n_other"]]},
        {"patient_id": "MIMIC-102", "hospital_id": None},
        {"patient_id": "MIMIC-104", "hospital_id": HID, "patient_account_id": ids["patient1"]},
        {"patient_id": GONE, "hospital_id": OTHER, "patient_account_id": ids["patient2"]},
    ])

    monkeypatch.setattr(script, "get_mongo_client", lambda uri: c)
    monkeypatch.setattr(script, "load_dotenv", lambda: None)
    monkeypatch.setattr(script.getpass, "getpass", lambda prompt="": PASSWORD)
    return {"client": c, "readm": readm, "ids": ids}


def run(*args, hospital="Your Hospital Name"):
    sys.argv = ["demo_patient_logins.py", "--hospital", hospital, *args]
    script.main()


def care(world, pid):
    return world["readm"].care_actions.find_one({"patient_id": pid})


def account(world, email):
    return auth.effective(world["client"]["shared_identity"].users.find_one({"email": email}))


def logins(world):
    """email -> the one record that login sees."""
    out = {}
    for u in world["client"]["shared_identity"].users.find({"role": "patient"}):
        scope = access.patient_scope(world["readm"], auth.effective(u))
        assert len(scope) == 1, (u["email"], scope)
        out[u["email"]] = scope[0]
    return out


# -------------------------------------------------------------- the hospital
def test_every_patient_ends_up_in_the_hospital_once(client):
    run()
    rows = list(client["readm"].care_actions.find())
    assert Counter(r["patient_id"] for r in rows) == Counter(LATEST_IDS + [GONE])
    assert {r["hospital_id"] for r in rows} == {HID}


def test_a_moved_patient_swaps_the_old_hospitals_staff_for_this_ones(client):
    run()
    moved = care(client, "MIMIC-101")                                  # heart failure
    assert moved["assigned_doctor_id"] == "DR-YH-CARD"
    assert moved["assigned_nurse_ids"] and set(moved["assigned_nurse_ids"]) <= \
        {client["ids"]["n1"], client["ids"]["n2"]}
    assert care(client, "MIMIC-102")["assigned_doctor_id"] == "DR-YH-MED"  # diabetes: no match


def test_assignments_already_made_are_kept(client):
    run()
    kept = care(client, "MIMIC-100")
    assert kept["assigned_doctor_id"] == "DR-YH-MED" and kept["assigned_nurse_ids"] == [client["ids"]["n2"]]


def test_the_hospitals_staff_now_see_its_patients(client):
    run()
    readm = client["readm"]
    nurse = auth.effective(readm.client["shared_identity"].users.find_one({"email": "n1@yh.test"}))
    admin = {"_id": "a", "role": "hospital_admin", "hospital_id": HID}
    assert set(access.patient_scope(readm, admin)) == set(LATEST_IDS + [GONE])
    assert access.patient_scope(readm, nurse)
    assert access.patient_scope(readm, {"_id": "b", "role": "hospital_admin", "hospital_id": OTHER}) == []


# ------------------------------------------------------------------- logins
def test_twenty_logins_each_see_their_own_current_record(client):
    run()
    seen = logins(client)
    assert sorted(seen) == sorted(f"patient{i}@{HID}.test" for i in range(1, 21))
    assert len(set(seen.values())) == 20 and set(seen.values()) <= set(LATEST_IDS)
    for email in seen:
        a = account(client, email)
        assert (a["status"], a["hospital_id"], a["must_change_password"]) == ("active", HID, False)
        assert auth.login(client["readm"], email, PASSWORD)["token"]


def test_new_logins_open_readmissions_only(client):
    run()
    assert account(client, f"patient3@{HID}.test")["app_access"] == ["readmissions"]
    assert account(client, f"patient1@{HID}.test")["app_access"] == ["glp1", "readmissions"]


def test_the_logins_cover_high_medium_and_low_risk(client):
    run()
    bands = Counter(BANDS[LATEST_IDS.index(pid) % 3] for pid in logins(client).values())
    assert set(bands) == set(BANDS) and min(bands.values()) >= 6


def test_the_seeded_demo_patient_keeps_its_record_and_gets_the_new_password(client):
    run()
    assert logins(client)[f"patient1@{HID}.test"] == "MIMIC-104"
    assert auth.login(client["readm"], f"patient1@{HID}.test", PASSWORD)["token"]
    with pytest.raises(Exception):
        auth.login(client["readm"], f"patient1@{HID}.test", OLD_PASSWORD)


def test_a_login_whose_record_left_the_worklist_gets_a_current_one(client):
    run()
    assert logins(client)[f"patient2@{HID}.test"] in LATEST_IDS
    assert not care(client, GONE).get("patient_account_id")


def test_rerunning_links_nobody_twice(client):
    run()
    first = logins(client)
    before = client["readm"].care_actions.count_documents({})
    run()
    assert logins(client) == first
    assert client["readm"].care_actions.count_documents({}) == before


def test_an_address_held_by_staff_is_skipped(client):
    client["client"]["shared_identity"].users.insert_one(
        {"email": f"patient5@{HID}.test", "role": "doctor", "status": "active", "hospital_id": HID})
    run("--logins", "6")
    assert sorted(logins(client)) == sorted(f"patient{i}@{HID}.test" for i in (1, 2, 3, 4, 6, 7))
    assert account(client, f"patient5@{HID}.test")["role"] == "doctor"


def test_a_dry_run_writes_nothing(client):
    before = list(client["readm"].care_actions.find({}, {"_id": 0}))
    run("--dry-run")
    assert list(client["readm"].care_actions.find({}, {"_id": 0})) == before
    assert client["client"]["shared_identity"].users.count_documents({"role": "patient"}) == 2


def test_an_unknown_hospital_changes_nothing(client):
    before = list(client["readm"].care_actions.find({}, {"_id": 0}))
    with pytest.raises(SystemExit):
        run(hospital="No Such Hospital")
    assert list(client["readm"].care_actions.find({}, {"_id": 0})) == before


def test_the_hospital_can_be_named_by_id(client):
    run("--logins", "1", hospital=HID)
    assert {r["hospital_id"] for r in client["readm"].care_actions.find()} == {HID}


# --------------------------------------------------------- through the API
@pytest.fixture
def service(client, monkeypatch):
    os.environ.setdefault("MONGO_URI", "mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=100")
    from api import main
    monkeypatch.setattr(main, "db", client["readm"])
    monkeypatch.setattr(main, "_cache", {})
    monkeypatch.setattr(main, "API_KEY", None)
    monkeypatch.setattr(auth, "SHARED_SECRET_KEY", "test-secret-not-the-real-one")
    return main


def test_my_record_finds_the_login_its_own_patient_and_no_other(client, service):
    run()
    email = f"patient3@{HID}.test"
    mine = logins(client)[email]
    token = auth.login(client["readm"], email, PASSWORD)["token"]
    api = TestClient(service.app, headers={"Authorization": f"Bearer {token}"},
                     raise_server_exceptions=False)
    body = api.get("/api/patients", params={"limit": 50}).json()
    assert [p["id"] for p in body["data"]] == [mine]
    other = next(pid for pid in LATEST_IDS if pid != mine)
    assert api.get(f"/api/patients/{other}").status_code == 404
