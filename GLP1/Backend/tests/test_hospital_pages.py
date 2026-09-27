"""The hospital pages and the two layers of detail, over the real data.

Same accounts and ownership as test_isolation.py. Mirrors
Readmissions/tests/units/test_hospital_pages.py.
"""
import asyncio

import pytest
from fastapi.routing import APIRoute

import main
from core import access, chatbot_tools
from core.access import patient_scope
from core.config import settings
from core.security import effective
from tests.test_isolation import A, ACCOUNTS, client, world  # noqa: F401

REASON_EMAILS = ("admin@a.test", "claims@acme.test")


@pytest.fixture(autouse=True)
def fresh(world):
    """Each test starts with an empty access log and the original care teams."""
    ident = world["store"][settings.shared_identity_db_name]
    saved = list(world["db"].patient_access.find({}, {"_id": 0}))
    ident.access_log.delete_many({})
    yield
    ident.access_log.delete_many({})
    world["db"].patient_access.delete_many({})
    world["db"].patient_access.insert_many(saved)


def log(world):
    return list(world["store"][settings.shared_identity_db_name].access_log.find({}, {"_id": 0}))


def listed(response) -> set:
    return {p["patient_idx"] for p in response.json()["patients"]}


def uid(world, email):
    return str(world["store"][settings.shared_identity_db_name].users.find_one({"email": email})["_id"])


# ------------------------------------------------------ two layers of detail
@pytest.mark.parametrize("email", REASON_EMAILS)
def test_reason_roles_get_the_overview_layer_in_the_list(world, email):
    body = client(world, email).get("/api/patients", params={"page_size": 100}).json()
    assert body["redacted"] is True and body["patients"]
    for row in body["patients"]:
        assert not access.CLINICAL_FIELDS & row.keys(), sorted(access.CLINICAL_FIELDS & row.keys())
        assert {"patient_idx", "dropout_prob", "prediction", "doctor", "nurses", "insurer"} <= row.keys()


def test_the_care_team_gets_the_whole_row_with_names(world):
    rows = {p["patient_idx"]: p for p in
            client(world, "doc@a.test").get("/api/patients").json()["patients"]}
    assert rows[0]["BMXBMI"] is not None and rows[0]["assigned_molecule"]
    assert rows[0]["doctor"]["email"] == "doc@a.test"
    assert [n["email"] for n in rows[0]["nurses"]] == ["nurse@a.test"]


@pytest.mark.parametrize("email", REASON_EMAILS)
def test_reason_roles_cannot_filter_their_way_to_the_clinical_layer(world, email):
    c = client(world, email)
    everyone = listed(c.get("/api/patients", params={"page_size": 100}))
    assert listed(c.get("/api/patients", params={"molecule": "SEMAGLUTIDE"})) == everyone
    assert listed(c.get("/api/patients", params={"financial_only": True})) == everyone
    assert listed(c.get("/api/patients", params={"search": "cost"})) == everyone


@pytest.mark.parametrize("email", REASON_EMAILS)
def test_detail_asks_for_a_reason_and_the_summary_says_so(world, email):
    c = client(world, email)
    for path in ("/api/patients/0", "/api/patients/0/pharmacy-view"):
        r = c.get(path)
        assert r.status_code == 403 and r.json()["detail"]["code"] == "reason_required", path
    summary = c.get("/api/patients/0/summary").json()
    assert summary["detail_access"] == "reason_required"
    assert {r["key"] for r in summary["reasons"]} == set(access.REASONS)
    assert not access.CLINICAL_FIELDS & summary.keys()


def test_a_reason_opens_one_patient_and_is_logged(world):
    c = client(world, "admin@a.test")
    assert c.post("/api/patients/0/open", json={"reason": "care_coordination"}).json() == \
        {"patient_idx": 0, "detail_access": "granted"}
    r = c.get("/api/patients/0")
    assert r.status_code == 200 and r.json()["shap_drivers"]
    assert c.get("/api/patients/1").status_code == 403
    c.post("/api/patients/0/open", json={"reason": "audit"})
    entries = log(world)
    assert len(entries) == 1
    e = entries[0]
    assert (e["email"], e["patient_id"], e["hospital_id"], e["reason"], e["app"]) == \
        ("admin@a.test", "0", "hosp-a", "care_coordination", "glp1")


def test_bad_reasons_and_other_hospitals_patients_are_refused(world):
    c = client(world, "admin@a.test")
    assert c.post("/api/patients/0/open", json={"reason": "why not"}).status_code == 422
    assert c.post("/api/patients/4/open", json={"reason": "audit"}).status_code == 404
    assert log(world) == []


def test_the_care_team_is_never_asked(world):
    for email in ("doc@a.test", "nurse@a.test", "cm@a.test"):
        c = client(world, email)
        assert c.get("/api/patients/0").status_code == 200
        assert c.get("/api/patients/0/summary").json()["detail_access"] == "open"
    assert log(world) == []


def test_the_superadmin_is_logged_once_without_being_asked(world):
    c = client(world, "ops@team.test")
    for _ in range(2):
        assert c.get("/api/patients/4").status_code == 200
    entries = log(world)
    assert len(entries) == 1 and entries[0]["reason"] == "superadmin"
    assert entries[0]["hospital_id"] == "hosp-b"


# ----------------------------------------------------------------- overview
def test_the_overview_counts_the_accounts_own_patients(world):
    body = client(world, "admin@a.test").get("/api/overview").json()
    assert body["total_patients"] == 4 and body["adherent"] + body["non_adherent"] == 4
    assert body["no_doctor"] == 2 and body["no_nurse"] == 1         # 2, 3 / 3
    assert {m["name"]: m["count"] for m in body["insurer_mix"]} == {"No insurer on file": 3, "acme": 1}
    assert sum(d["count"] for d in body["drug_mix"]) == 4
    assert body["drug_spend"]["annual"] > 0
    assert body["staff"] == {"doctors": 1, "nurses": 1}
    # Case managers have no cost screens, so no drug spend either.
    assert client(world, "cm@a.test").get("/api/overview").json()["drug_spend"] is None
    insurer = client(world, "claims@acme.test").get("/api/overview").json()
    assert insurer["total_patients"] == 2 and insurer["staff"] is None


@pytest.mark.parametrize("email", ["doc@a.test", "nurse@a.test", "me@patient.test"])
def test_doctors_nurses_and_patients_have_no_overview_or_staff(world, email):
    c = client(world, email)
    assert c.get("/api/overview").status_code == 403
    assert c.get("/api/staff").status_code == 403


def test_the_staff_page_counts_each_persons_patients(world):
    body = client(world, "cm@a.test").get("/api/staff").json()
    assert [(d["email"], d["patients"]) for d in body["doctors"]] == [("doc@a.test", 2)]
    assert [(n["email"], n["patients"]) for n in body["nurses"]] == [("nurse@a.test", 3)]
    assert body["no_doctor"] == 2 and body["no_nurse"] == 1
    assert client(world, "claims@acme.test").get("/api/staff").status_code == 403


def test_the_staff_drill_down_filters_the_patient_list(world):
    c = client(world, "admin@a.test")
    assert listed(c.get("/api/patients", params={"doctor": uid(world, "doc@a.test")})) == {0, 1}
    assert listed(c.get("/api/patients", params={"nurse": uid(world, "nurse@a.test")})) == {0, 1, 2}
    assert listed(c.get("/api/patients", params={"unassigned": "doctor"})) == {2, 3}
    assert listed(c.get("/api/patients", params={"unassigned": "nurse"})) == {3}


# ---------------------------------------------------------------- care teams
def test_assigning_takes_effect_at_once_and_never_crosses_hospitals(world):
    doctor, nurse = uid(world, "doc@a.test"), uid(world, "nurse@a.test")
    cm = client(world, "cm@a.test")
    r = cm.post("/api/care-team", json={"patient_ids": [2, 3], "doctor_id": doctor,
                                        "add_nurse_ids": [nurse]})
    assert r.status_code == 200 and r.json()["updated"] == 2
    assert listed(client(world, "doc@a.test").get("/api/patients")) == {0, 1, 2, 3}
    assert 3 in listed(client(world, "nurse@a.test").get("/api/patients"))

    before = list(world["db"].patient_access.find({}, {"_id": 0}))
    assert cm.post("/api/care-team", json={"patient_ids": [4], "doctor_id": doctor}).status_code == 404
    assert cm.post("/api/care-team", json={"patient_ids": [2, 5], "doctor_id": ""}).status_code == 404
    admin_b = uid(world, "admin@b.test")                            # not a doctor
    assert cm.post("/api/care-team", json={"patient_ids": [2], "doctor_id": admin_b}).status_code == 404
    ops = client(world, "ops@team.test")
    assert ops.post("/api/care-team", json={"patient_ids": [2, 4], "doctor_id": ""}).status_code == 409
    assert list(world["db"].patient_access.find({}, {"_id": 0})) == before


@pytest.mark.parametrize("email", ["doc@a.test", "nurse@a.test", "claims@acme.test", "me@patient.test"])
def test_only_admins_and_case_managers_assign(world, email):
    r = client(world, email).post("/api/care-team", json={"patient_ids": [0], "doctor_id": ""})
    assert r.status_code == 403


# ----------------------------------------------------------- hospital picker
def test_the_superadmin_can_look_at_one_hospital(world):
    c = client(world, "ops@team.test")
    picked = {"X-Hospital-Id": "hosp-b"}
    assert listed(c.get("/api/patients", headers=picked, params={"page_size": 100})) == {4, 5}
    assert c.get("/api/summary", headers=picked).json()["kpis"]["total_patients"] == 2
    assert c.get("/api/overview", headers=picked).json()["total_patients"] == 2
    assert c.get("/api/patients/0", headers=picked).status_code == 404
    admin = client(world, "admin@a.test")
    assert listed(admin.get("/api/patients", headers=picked)) == A


def test_every_new_route_needs_a_signed_in_user(world):
    from fastapi.testclient import TestClient
    anon = TestClient(main.app, raise_server_exceptions=False)
    for route in main.app.routes:
        if isinstance(route, APIRoute) and route.path in ("/api/overview", "/api/staff"):
            assert anon.get(route.path).status_code in (401, 403)
    assert anon.post("/api/care-team", json={"patient_ids": [0]}).status_code in (401, 403)


# ------------------------------------------------------------------ chatbot
def ctx_for(world, email, token_session="s1"):
    user = effective(world["store"][settings.shared_identity_db_name].users.find_one({"email": email}))
    user["session"] = token_session
    return chatbot_tools.ToolContext(user=user, scope=asyncio.run(patient_scope(user)))


def test_the_chatbot_keeps_to_the_layer(world):
    ctx = ctx_for(world, "admin@a.test")
    result, err = asyncio.run(chatbot_tools.dispatch_tool("get_patient", {"patient_idx": 0}, ctx))
    assert err and "give a reason" in err
    result, err = asyncio.run(chatbot_tools.dispatch_tool("search_patients", {"page_size": 50}, ctx))
    assert err is None and all(not access.CLINICAL_FIELDS & p.keys() for p in result["patients"])
    doctor = ctx_for(world, "doc@a.test")
    result, err = asyncio.run(chatbot_tools.dispatch_tool("get_patient", {"patient_idx": 0}, doctor))
    assert err is None and result["patient"]["BMXBMI"] is not None


def test_an_account_with_no_patients_gets_zeros_not_errors(world):
    """A new hospital or an insurer with no members yet is a normal state."""
    c = client(world, "floating@x.test")                           # placed nowhere
    ops = client(world, "ops@team.test")
    empty = {"X-Hospital-Id": "hosp-empty"}
    for path in ("/api/consequence/downstream-cost", "/api/consequence/rebound-risk"):
        r = ops.get(path, headers=empty)
        assert r.status_code == 200 and r.json()["n_patients_total"] == 0, path
    body = ops.get("/api/overview", headers=empty).json()
    assert body["total_patients"] == 0 and body["drug_mix"] == []
    assert c.get("/api/patients").json()["total"] == 0
