"""User Management rules: who can create, see and change which accounts.

The point of these tests is the boundaries - a hospital admin must never reach
another hospital's people, nobody can mint a superadmin, and a temporary
password must not unlock data. Runs against mongomock.
"""
import mongomock
import pytest
from fastapi import HTTPException

from api import auth, user_admin as ua

SECRET = "test-secret-not-the-real-one"


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    monkeypatch.setattr(auth, "SHARED_SECRET_KEY", SECRET)
    monkeypatch.setattr(auth, "DEFAULT_APP_ACCESS", ["glp1", "readmissions"])


@pytest.fixture
def db():
    return mongomock.MongoClient()["neuroshield"]


def account(db, email, role, hospital_id=None, status="active", **extra):
    doc = {"email": email, "password_hash": auth.hash_password("correct-horse"),
           "role": role, "status": status, "hospital_id": hospital_id, **extra}
    doc["_id"] = auth.users(db).insert_one(doc).inserted_id
    return auth.effective(doc)


@pytest.fixture
def world(db):
    """Two hospitals, one insurer, our superadmin and each hospital's admin."""
    sa = account(db, "ops@team.com", "superadmin")
    ua.create_hospital(db, sa, "Demo Hospital A")
    ua.create_hospital(db, sa, "Demo Hospital B")
    ua.create_insurer(db, sa, "Acme Health")
    return {"sa": sa,
            "admin_a": account(db, "admin@a.org", "hospital_admin", "demo-hospital-a"),
            "admin_b": account(db, "admin@b.org", "hospital_admin", "demo-hospital-b")}


def refused(code, fn, *args, **kwargs):
    with pytest.raises(HTTPException) as e:
        fn(*args, **kwargs)
    assert e.value.status_code == code, e.value.detail
    return e.value


def token(db, email, password="correct-horse"):
    return auth.login(db, email, password)["token"]


# ------------------------------------------------------------ organisations
def test_the_superadmin_creates_hospitals_with_readable_ids(db, world):
    out = ua.create_hospital(db, world["sa"], "St. Mary's General")
    assert out == {"id": "st-mary-s-general", "name": "St. Mary's General"}


def test_a_hospital_cannot_be_created_twice(db, world):
    refused(409, ua.create_hospital, db, world["sa"], "Demo Hospital A")


def test_only_the_superadmin_creates_hospitals_and_insurers(db, world):
    refused(403, ua.create_hospital, db, world["admin_a"], "Rogue Hospital")
    refused(403, ua.create_insurer, db, world["admin_a"], "Rogue Insurer")


def test_a_hospital_admin_sees_only_its_own_hospital(db, world):
    assert [h["id"] for h in ua.list_hospitals(db, world["admin_a"])] == ["demo-hospital-a"]
    assert {h["id"] for h in ua.list_hospitals(db, world["sa"])} == \
        {"demo-hospital-a", "demo-hospital-b"}


@pytest.mark.parametrize("role", ["doctor", "nurse", "case_manager", "insurer", "patient"])
def test_non_managers_are_refused_user_management(db, world, role):
    user = account(db, f"{role}@a.org", role, "demo-hospital-a")
    refused(403, ua.list_users, db, user)
    refused(403, ua.create_user, db, user, "x@a.org", "doctor")
    refused(403, ua.list_hospitals, db, user)


# -------------------------------------------------------------- create user
def test_the_superadmin_creates_a_hospital_admin_with_a_temporary_password(db, world):
    out = ua.create_user(db, world["sa"], "new.admin@a.org", "hospital_admin",
                         "Dr Admin", hospital_id="demo-hospital-a")
    user = out["user"]
    assert (user["role"], user["hospital_id"], user["status"]) == \
        ("hospital_admin", "demo-hospital-a", "active")
    assert user["must_change_password"] is True
    assert len(out["temporary_password"]) == 12
    stored = auth.users(db).find_one({"email": "new.admin@a.org"})
    assert out["temporary_password"] not in str(stored)          # only the hash is kept


def test_a_hospital_admin_always_places_staff_in_its_own_hospital(db, world):
    """Whatever the request says. Naming another hospital is ignored, not obeyed."""
    out = ua.create_user(db, world["admin_a"], "doc@a.org", "doctor", hospital_id="demo-hospital-b")
    assert out["user"]["hospital_id"] == "demo-hospital-a"


@pytest.mark.parametrize("role", ["hospital_admin", "insurer", "superadmin"])
def test_a_hospital_admin_cannot_hand_out_roles_above_its_staff(db, world, role):
    refused(403, ua.create_user, db, world["admin_a"], "x@a.org", role,
            insurer_id="acme-health")


def test_nobody_can_create_a_superadmin_through_user_management(db, world):
    refused(403, ua.create_user, db, world["sa"], "x@team.com", "superadmin")


def test_a_hospital_role_needs_a_real_hospital(db, world):
    refused(422, ua.create_user, db, world["sa"], "x@a.org", "doctor")
    refused(422, ua.create_user, db, world["sa"], "x@a.org", "doctor", hospital_id="nowhere")


def test_an_insurer_account_belongs_to_an_insurer_not_a_hospital(db, world):
    refused(422, ua.create_user, db, world["sa"], "x@acme.com", "insurer")
    user = ua.create_user(db, world["sa"], "x@acme.com", "insurer", insurer_id="acme-health",
                          hospital_id="demo-hospital-a")["user"]
    assert (user["insurer_id"], user["hospital_id"]) == ("acme-health", None)


def test_an_active_email_cannot_be_added_again(db, world):
    ua.create_user(db, world["admin_a"], "doc@a.org", "doctor")
    refused(409, ua.create_user, db, world["admin_a"], "doc@a.org", "nurse")


@pytest.mark.parametrize("email", ["", "not-an-email", "a@b"])
def test_a_malformed_email_is_refused(db, world, email):
    refused(422, ua.create_user, db, world["admin_a"], email, "doctor")


# ------------------------------------------- temporary passwords lock data
def test_a_temporary_password_signs_in_but_unlocks_nothing(db, world):
    out = ua.create_user(db, world["admin_a"], "doc@a.org", "doctor")
    t = token(db, "doc@a.org", out["temporary_password"])
    refused(403, auth.authenticate, db, t)
    assert auth.authenticate(db, t, allow_password_change=True)["email"] == "doc@a.org"


def test_changing_the_temporary_password_unlocks_the_account(db, world):
    out = ua.create_user(db, world["admin_a"], "doc@a.org", "doctor")
    t = token(db, "doc@a.org", out["temporary_password"])
    fresh = ua.change_password(db, t, out["temporary_password"], "my-own-password")
    assert fresh["user"]["must_change_password"] is False
    assert auth.authenticate(db, fresh["token"])["role"] == "doctor"
    refused(401, auth.login, db, "doc@a.org", out["temporary_password"])   # old one is dead
    assert auth.login(db, "doc@a.org", "my-own-password")["token"]


def test_change_password_needs_the_current_one(db, world):
    t = token(db, "admin@a.org")
    refused(401, ua.change_password, db, t, "wrong-password", "my-own-password")


@pytest.mark.parametrize("new", ["short", "correct-horse"])
def test_change_password_refuses_a_weak_or_unchanged_password(db, world, new):
    refused(422, ua.change_password, db, token(db, "admin@a.org"), "correct-horse", new)


# ------------------------------------------------ approving self-signups
def test_adding_a_pending_signups_email_approves_it_instead_of_refusing(db, world):
    signup_token = auth.signup(db, "nurse@a.org", "their-own-password")["token"]
    refused(403, auth.authenticate, db, signup_token)

    out = ua.create_user(db, world["admin_a"], "nurse@a.org", "nurse", "Nurse Joy")
    assert out["approved_existing"] is True
    assert out["temporary_password"] is None                     # they keep their password
    me = auth.authenticate(db, signup_token)                      # same token, now works
    assert (me["role"], me["hospital_id"], me["status"]) == ("nurse", "demo-hospital-a", "active")


def test_an_admin_cannot_claim_a_pending_account_that_belongs_elsewhere(db, world):
    """A suspended account of hospital B looks pending too; A must not take it."""
    account(db, "doc@b.org", "doctor", "demo-hospital-b", status="pending")
    refused(409, ua.create_user, db, world["admin_a"], "doc@b.org", "doctor")


# ---------------------------------------------------------------- list users
def test_a_hospital_admin_lists_only_its_own_hospital(db, world):
    ua.create_user(db, world["admin_a"], "doc@a.org", "doctor")
    ua.create_user(db, world["admin_b"], "doc@b.org", "doctor")
    auth.signup(db, "stranger@x.org", "their-own-password")      # pending, unattached

    emails = {u["email"] for u in ua.list_users(db, world["admin_a"], hospital_id="demo-hospital-b")}
    assert emails == {"admin@a.org", "doc@a.org"}                # asking for B changes nothing


def test_the_superadmin_lists_everyone_and_can_filter(db, world):
    ua.create_user(db, world["admin_a"], "doc@a.org", "doctor")
    auth.signup(db, "stranger@x.org", "their-own-password")
    everyone = {u["email"] for u in ua.list_users(db, world["sa"])}
    assert {"doc@a.org", "stranger@x.org", "admin@b.org"} <= everyone
    assert [u["email"] for u in ua.list_users(db, world["sa"], status="pending")] == ["stranger@x.org"]
    assert {u["email"] for u in ua.list_users(db, world["sa"], hospital_id="demo-hospital-b")} \
        == {"admin@b.org"}


def test_listed_accounts_never_carry_a_password_hash(db, world):
    assert all("password_hash" not in u for u in ua.list_users(db, world["sa"]))


# --------------------------------------------------------------- update user
def uid(db, email):
    return str(auth.users(db).find_one({"email": email})["_id"])


def test_a_hospital_admin_changes_roles_within_its_staff(db, world):
    ua.create_user(db, world["admin_a"], "doc@a.org", "doctor")
    assert ua.update_user(db, world["admin_a"], uid(db, "doc@a.org"), role="nurse")["role"] == "nurse"


def test_another_hospitals_account_is_invisible_not_just_forbidden(db, world):
    """404, exactly as for an id that does not exist, so it cannot be probed."""
    ua.create_user(db, world["admin_b"], "doc@b.org", "doctor")
    refused(404, ua.update_user, db, world["admin_a"], uid(db, "doc@b.org"), role="nurse")


def test_a_hospital_admin_cannot_promote_anyone_to_admin(db, world):
    ua.create_user(db, world["admin_a"], "doc@a.org", "doctor")
    refused(403, ua.update_user, db, world["admin_a"], uid(db, "doc@a.org"), role="hospital_admin")


def test_a_hospital_admin_cannot_edit_a_fellow_admin(db, world):
    account(db, "admin2@a.org", "hospital_admin", "demo-hospital-a")
    refused(404, ua.update_user, db, world["admin_a"], uid(db, "admin2@a.org"), status="pending")


def test_nobody_edits_a_superadmin_or_themselves(db, world):
    account(db, "ops2@team.com", "superadmin")
    refused(404, ua.update_user, db, world["sa"], uid(db, "ops2@team.com"), role="doctor")
    refused(404, ua.update_user, db, world["sa"], uid(db, "ops@team.com"), status="pending")
    refused(404, ua.update_user, db, world["admin_a"], uid(db, "admin@a.org"), role="doctor")


def test_a_hospital_admin_cannot_move_staff_to_another_hospital(db, world):
    ua.create_user(db, world["admin_a"], "doc@a.org", "doctor")
    out = ua.update_user(db, world["admin_a"], uid(db, "doc@a.org"), hospital_id="demo-hospital-b")
    assert out["hospital_id"] == "demo-hospital-a"


def test_the_superadmin_approves_a_signup_into_a_hospital(db, world):
    signup_token = auth.signup(db, "stranger@x.org", "their-own-password")["token"]
    refused(422, ua.update_user, db, world["sa"], uid(db, "stranger@x.org"), status="active",
            role="doctor")                                        # a doctor needs a hospital
    ua.update_user(db, world["sa"], uid(db, "stranger@x.org"), status="active", role="doctor",
                   hospital_id="demo-hospital-b")
    assert auth.authenticate(db, signup_token)["hospital_id"] == "demo-hospital-b"


def test_suspending_an_account_cuts_off_its_token_immediately(db, world):
    account(db, "doc@a.org", "doctor", "demo-hospital-a")
    t = token(db, "doc@a.org")
    assert auth.authenticate(db, t)["status"] == "active"
    ua.update_user(db, world["admin_a"], uid(db, "doc@a.org"), status="pending")
    refused(403, auth.authenticate, db, t)


@pytest.mark.parametrize("user_id", ["not-an-id", "", "5f0000000000000000000000"])
def test_an_unusable_or_unknown_user_id_is_404(db, world, user_id):
    refused(404, ua.update_user, db, world["sa"], user_id, role="nurse")


def test_an_unknown_status_is_refused(db, world):
    ua.create_user(db, world["admin_a"], "doc@a.org", "doctor")
    refused(422, ua.update_user, db, world["admin_a"], uid(db, "doc@a.org"), status="deleted")


# ---------------------------------------------------------------- CSV import
def test_import_creates_good_rows_and_reports_bad_ones_by_line(db, world):
    csv_text = ("email,name,role\n"
                "doc1@a.org,Dr One,doctor\n"
                "nurse1@a.org,Nurse One,Nurse\n"               # role case is forgiven
                "boss@a.org,Boss,hospital_admin\n"             # not the admin's to give
                "not-an-email,Nobody,doctor\n")
    out = ua.import_users(db, world["admin_a"], csv_text)
    assert [c["user"]["email"] for c in out["created"]] == ["doc1@a.org", "nurse1@a.org"]
    assert [(f["line"], f["email"]) for f in out["failed"]] == \
        [(4, "boss@a.org"), (5, "not-an-email")]
    assert all(c["user"]["hospital_id"] == "demo-hospital-a" for c in out["created"])
    passwords = [c["temporary_password"] for c in out["created"]]
    assert len(set(passwords)) == len(passwords)


def test_import_needs_a_header_row(db, world):
    refused(422, ua.import_users, db, world["admin_a"], "doc1@a.org,Dr One,doctor\n")


def test_the_superadmin_imports_into_a_named_hospital(db, world):
    out = ua.import_users(db, world["sa"], "email,role\nx@b.org,nurse\n",
                          hospital_id="demo-hospital-b")
    assert out["created"][0]["user"]["hospital_id"] == "demo-hospital-b"
