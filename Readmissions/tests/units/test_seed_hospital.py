"""scripts/seed_hospital.py: every patient gets an owner, demo accounts see
exactly their own patients, and re-running never overwrites anything."""
import sys

import mongomock
import pytest

from api import access, auth
from scripts import seed_hospital as seed

GROUPS = {"MIMIC-1": "heart_failure", "MIMIC-2": "respiratory", "MIMIC-3": "diabetes",
          "MIMIC-4": "renal", "MIMIC-5": "heart_failure", "MIMIC-6": "general"}


@pytest.fixture
def client(monkeypatch):
    c = mongomock.MongoClient()
    readm = c["neuroshield"]
    for pid, group in GROUPS.items():
        readm["patient_worklist"].insert_one({"patient_id": pid, "batch_date": "2026-04-29",
                                              "clinical_group": group})
    c["glp1_analytics"]["patients"].insert_many(
        [{"patient_idx": i, "RIDAGEYR": 70 if i == 0 else 40} for i in range(8)])

    monkeypatch.setattr(seed, "get_mongo_client", lambda uri: c)
    monkeypatch.setattr(seed, "load_dotenv", lambda: None)
    monkeypatch.setattr(seed, "mimic_insurance",
                        lambda: {"MIMIC-1": "medicare", "MIMIC-2": "private", "MIMIC-3": "medicaid"})
    monkeypatch.setattr(seed.getpass, "getpass", lambda prompt="": "demo-password-1")
    monkeypatch.setattr(auth, "BCRYPT_ROUNDS", 4)
    return c


def run(*args):
    sys.argv = ["seed_hospital.py", "--hospital", "Demo Hospital", *args]
    seed.main()


def owner(c, pid):
    return c["neuroshield"]["care_actions"].find_one({"patient_id": pid})


def account(c, email):
    return auth.effective(c["shared_identity"]["users"].find_one({"email": email}))


def test_every_patient_gets_the_hospital_and_its_insurer(client):
    run()
    assert client["shared_identity"]["hospitals"].find_one({"_id": "demo-hospital"})
    assert {i["_id"] for i in client["shared_identity"]["insurers"].find()} == \
        {"medicare", "medicaid", "private", "other"}
    for pid in GROUPS:
        assert owner(client, pid)["hospital_id"] == "demo-hospital"
    assert owner(client, "MIMIC-1")["insurer_id"] == "medicare"
    assert owner(client, "MIMIC-4").get("insurer_id") is None       # nothing on file
    glp1 = {d["patient_idx"]: d for d in client["glp1_analytics"]["patient_access"].find()}
    assert len(glp1) == 8 and all(d["hospital_id"] == "demo-hospital" for d in glp1.values())
    assert glp1[0]["insurer_id"] == "medicare"                       # 65 and over
    assert all(d["pharmacy"] in seed.PHARMACIES for d in glp1.values())


def test_without_the_flag_no_accounts_are_created(client):
    run()
    assert client["shared_identity"]["users"].count_documents({}) == 0


def test_a_dry_run_writes_nothing(client):
    run("--dry-run", "--with-demo-accounts")
    assert client["neuroshield"]["care_actions"].count_documents({}) == 0
    assert client["shared_identity"]["users"].count_documents({}) == 0


def test_demo_doctors_get_their_specialtys_patients(client):
    run("--with-demo-accounts")
    readm = client["neuroshield"]
    cardiology = account(client, "cardiology@demo-hospital.test")
    assert set(access.patient_scope(readm, cardiology)) == {"MIMIC-1", "MIMIC-5"}
    medicine = account(client, "medicine@demo-hospital.test")
    assert set(access.patient_scope(readm, medicine)) == {"MIMIC-4", "MIMIC-6"}  # unmatched -> medicine
    assert readm["doctors"].find_one({"email": "cardiology@demo-hospital.test"})["hospital_id"] \
        == "demo-hospital"


def test_demo_roles_see_what_the_rules_say(client):
    run("--with-demo-accounts")
    readm = client["neuroshield"]
    admin = account(client, "admin@demo-hospital.test")
    assert set(access.patient_scope(readm, admin)) == set(GROUPS)
    nurses = [set(access.patient_scope(readm, account(client, f"nurse{i}@demo-hospital.test")))
              for i in (1, 2)]
    assert nurses[0] | nurses[1] == set(GROUPS) and not nurses[0] & nurses[1]
    medicare = account(client, "claims@medicare.test")
    assert set(access.patient_scope(readm, medicare)) == {"MIMIC-1"}
    patient = account(client, "patient1@demo-hospital.test")
    assert access.patient_scope(readm, patient) == ["MIMIC-1"]
    assert admin["must_change_password"] is False                    # demo logins work at once


def test_rerunning_changes_nothing_and_never_overwrites(client):
    run("--with-demo-accounts")
    readm = client["neuroshield"]
    readm["care_actions"].update_one({"patient_id": "MIMIC-1"},
                                     {"$set": {"assigned_doctor_id": "DR-someone-real",
                                               "hospital_id": "real-hospital"}})
    before = list(readm["care_actions"].find({}, {"_id": 0}))
    run("--with-demo-accounts")
    assert list(readm["care_actions"].find({}, {"_id": 0})) == before
    assert client["shared_identity"]["users"].count_documents({"email": "admin@demo-hospital.test"}) == 1


def test_most_common_insurance_wins(tmp_path, monkeypatch):
    pd = pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    path = tmp_path / "matrix.parquet"
    pd.DataFrame({"subject_id": [7, 7, 7, 8, 9],
                  "insurance": ["Medicare", "Private", "Medicare", "UNKNOWN", "Medicaid"]}
                 ).to_parquet(path)
    monkeypatch.setattr(seed, "MATRIX", str(path))
    assert seed.mimic_insurance() == {"MIMIC-7": "medicare", "MIMIC-9": "medicaid"}
