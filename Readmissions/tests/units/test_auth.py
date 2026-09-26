"""Shared login: password handling, token issue, and the rules around both.

Runs against mongomock, so the suite never touches the real identity collection
and never depends on the cluster being reachable.
"""
import time

import bcrypt
import jwt
import mongomock
import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from api import auth

SECRET = "test-secret-not-the-real-one"


@pytest.fixture
def db():
    """A stand-in for the product database. api.auth reaches the identity
    database through `db.client`, exactly as it does in production."""
    return mongomock.MongoClient()["neuroshield"]


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    monkeypatch.setattr(auth, "SHARED_SECRET_KEY", SECRET)
    monkeypatch.setattr(auth, "DEFAULT_APP_ACCESS", ["glp1", "readmissions"])
    monkeypatch.setattr(auth, "TOKEN_TTL_SECONDS", 3600)


def claims_of(result):
    return jwt.decode(result["token"], SECRET, algorithms=["HS256"])


def make_user(db, email="a@b.com", role="doctor", status="active",
              hospital_id="demo-hospital-a", **extra):
    """An account as an admin would create it, written straight to the store."""
    doc = {"email": email, "password_hash": auth.hash_password("correct-horse"),
           "role": role, "status": status, "hospital_id": hospital_id, **extra}
    doc["_id"] = auth.users(db).insert_one(doc).inserted_id
    return doc


def token_for(db, email="a@b.com"):
    return auth.login(db, email, "correct-horse")["token"]


# ------------------------------------------------------------------- signup
def test_signup_returns_a_token_carrying_the_agreed_claims(db):
    out = auth.signup(db, "New.User@Test.com", "correct-horse")
    c = claims_of(out)
    assert set(c) == {"sub", "email", "role", "status", "hospital_id", "app_access", "exp"}
    assert c["email"] == "new.user@test.com"          # normalised
    assert c["app_access"] == ["glp1", "readmissions"]


def test_a_self_signup_is_a_pending_case_manager_with_no_hospital(db):
    """Nobody picks their own role, and typing a hospital's name must not be
    enough to see its patients."""
    c = claims_of(auth.signup(db, "a@b.com", "correct-horse"))
    assert (c["role"], c["status"], c["hospital_id"]) == ("case_manager", "pending", None)
    stored = auth.users(db).find_one({"email": "a@b.com"})
    assert (stored["role"], stored["status"], stored["hospital_id"]) == \
        ("case_manager", "pending", None)


def test_signup_stores_a_bcrypt_hash_and_never_the_password(db):
    auth.signup(db, "a@b.com", "correct-horse")
    stored = auth.users(db).find_one({"email": "a@b.com"})
    assert stored["password_hash"].startswith("$2b$12$")
    assert len(stored["password_hash"]) == 60
    assert "correct-horse" not in str(stored)


def test_signup_refuses_a_duplicate_email(db):
    auth.ensure_indexes(db)
    auth.signup(db, "dup@test.com", "correct-horse")
    with pytest.raises(HTTPException) as e:
        auth.signup(db, "dup@test.com", "another-password")
    assert e.value.status_code == 409


@pytest.mark.parametrize("email", ["", "not-an-email", "a@b", "a b@c.com"])
def test_signup_refuses_a_malformed_email(db, email):
    with pytest.raises(HTTPException) as e:
        auth.signup(db, email, "correct-horse")
    assert e.value.status_code == 422


def test_signup_refuses_a_short_password(db):
    with pytest.raises(HTTPException) as e:
        auth.signup(db, "a@b.com", "short")
    assert e.value.status_code == 422


# -------------------------------------------------------------------- login
def test_login_succeeds_with_the_right_password(db):
    auth.signup(db, "a@b.com", "correct-horse")
    assert claims_of(auth.login(db, "a@b.com", "correct-horse"))["email"] == "a@b.com"


def test_login_carries_the_role_status_and_hospital_an_admin_assigned(db):
    make_user(db, role="nurse", hospital_id="demo-hospital-b")
    c = claims_of(auth.login(db, "a@b.com", "correct-horse"))
    assert (c["role"], c["status"], c["hospital_id"]) == ("nurse", "active", "demo-hospital-b")


def test_a_pending_account_can_still_sign_in(db):
    """So the portal can tell them they are waiting, rather than failing with
    a message that reads like a wrong password."""
    auth.signup(db, "a@b.com", "correct-horse")
    assert claims_of(auth.login(db, "a@b.com", "correct-horse"))["status"] == "pending"


def test_login_is_case_insensitive_on_the_email(db):
    auth.signup(db, "a@b.com", "correct-horse")
    assert auth.login(db, "  A@B.COM  ", "correct-horse")["token"]


def test_login_refuses_the_wrong_password(db):
    auth.signup(db, "a@b.com", "correct-horse")
    with pytest.raises(HTTPException) as e:
        auth.login(db, "a@b.com", "wrong-password")
    assert e.value.status_code == 401


def test_an_unknown_account_and_a_wrong_password_are_indistinguishable(db):
    """Different messages here would let anyone enumerate registered emails."""
    auth.signup(db, "a@b.com", "correct-horse")
    with pytest.raises(HTTPException) as wrong:
        auth.login(db, "a@b.com", "wrong-password")
    with pytest.raises(HTTPException) as unknown:
        auth.login(db, "nobody@test.com", "wrong-password")
    assert wrong.value.status_code == unknown.value.status_code == 401
    assert wrong.value.detail == unknown.value.detail


def test_an_account_created_elsewhere_with_the_same_bcrypt_scheme_can_log_in(db):
    """Accounts already in the collection were made by another codebase. They
    must keep working - nobody should have to reset a password for this."""
    auth.users(db).insert_one({
        "email": "doc@test.com", "role": "Doctor", "org_id": "city-hospital",
        "org_name": "City Hospital",
        "password_hash": bcrypt.hashpw(b"their-password", bcrypt.gensalt(rounds=12)).decode(),
    })
    assert auth.login(db, "doc@test.com", "their-password")["token"]


def test_an_older_account_with_no_app_access_field_gets_the_default(db):
    """Rather than being locked out of both products."""
    auth.users(db).insert_one({"email": "old@test.com", "role": "Doctor",
                               "password_hash": auth.hash_password("correct-horse")})
    assert claims_of(auth.login(db, "old@test.com", "correct-horse"))["app_access"] \
        == ["glp1", "readmissions"]


def test_a_corrupt_stored_hash_does_not_let_anyone_in(db):
    auth.users(db).insert_one({"email": "bad@test.com", "password_hash": "not-a-hash"})
    with pytest.raises(HTTPException) as e:
        auth.login(db, "bad@test.com", "anything-at-all")
    assert e.value.status_code == 401


# ---------------------------------------------------------- legacy accounts
@pytest.mark.parametrize("typed_role", ["Doctor", "Hospital", "superadmin", "hospital_admin"])
def test_a_role_typed_in_before_fixed_roles_is_never_trusted(db, typed_role):
    """The old signup stored any string, so an old record saying "superadmin"
    proves nothing. Legacy accounts are read as an active case_manager with no
    hospital - the same thing the backfill script writes."""
    auth.users(db).insert_one({"email": "old@test.com", "role": typed_role,
                               "org_id": "city-hospital",
                               "password_hash": auth.hash_password("correct-horse")})
    c = claims_of(auth.login(db, "old@test.com", "correct-horse"))
    assert (c["role"], c["status"], c["hospital_id"]) == ("case_manager", "active", None)


def test_a_role_outside_the_fixed_list_is_not_trusted_even_with_a_status(db):
    make_user(db, role="pharmacist")
    assert claims_of(auth.login(db, "a@b.com", "correct-horse"))["role"] == "case_manager"


# -------------------------------------------------------------- token shape
def test_the_token_expires_and_carries_the_configured_lifetime(db):
    out = auth.signup(db, "a@b.com", "correct-horse")
    assert out["expires_in"] == 3600
    assert 3500 < claims_of(out)["exp"] - time.time() <= 3600


def test_the_subject_is_the_account_id_so_each_product_can_look_the_user_up(db):
    out = auth.signup(db, "a@b.com", "correct-horse")
    assert claims_of(out)["sub"] == str(auth.users(db).find_one({"email": "a@b.com"})["_id"])


def test_the_response_never_carries_the_password_hash(db):
    out = auth.signup(db, "a@b.com", "correct-horse")
    assert "password" not in str(out).lower()


def test_tokens_cannot_be_issued_without_a_secret(db, monkeypatch):
    monkeypatch.setattr(auth, "SHARED_SECRET_KEY", "")
    with pytest.raises(HTTPException) as e:
        auth.signup(db, "a@b.com", "correct-horse")
    assert e.value.status_code == 500


# ------------------------------------------------------------------ decoding
def test_a_token_signed_with_another_secret_is_refused():
    token = jwt.encode({"sub": "x", "exp": int(time.time()) + 60}, "other", algorithm="HS256")
    with pytest.raises(HTTPException) as e:
        auth.decode_token(token)
    assert e.value.status_code == 401


def test_an_expired_token_is_refused():
    token = jwt.encode({"sub": "x", "exp": int(time.time()) - 1}, SECRET, algorithm="HS256")
    with pytest.raises(HTTPException) as e:
        auth.decode_token(token)
    assert e.value.status_code == 401
    assert "expired" in e.value.detail.lower()


def test_a_token_without_an_expiry_is_refused():
    with pytest.raises(HTTPException) as e:
        auth.decode_token(jwt.encode({"sub": "x"}, SECRET, algorithm="HS256"))
    assert e.value.status_code == 401


def test_the_alg_none_trick_is_refused():
    """Accepting the algorithm named in the token's own header is the classic
    JWT hole; decode is pinned to HS256."""
    token = jwt.encode({"sub": "x", "exp": int(time.time()) + 60}, key="", algorithm="none")
    with pytest.raises(HTTPException) as e:
        auth.decode_token(token)
    assert e.value.status_code == 401


# ------------------------------------------------------------------ accounts
def test_get_account_reads_the_current_record_not_the_token(db):
    make_user(db)
    sub = str(auth.users(db).find_one({"email": "a@b.com"})["_id"])
    auth.users(db).update_one({"email": "a@b.com"}, {"$set": {"role": "nurse"}})
    assert auth.public_view(auth.get_account(db, sub))["role"] == "nurse"


@pytest.mark.parametrize("sub", ["not-an-object-id", "", None])
def test_a_token_with_an_unusable_subject_is_refused(db, sub):
    with pytest.raises(HTTPException) as e:
        auth.get_account(db, sub)
    assert e.value.status_code == 401


def test_a_deleted_account_cannot_keep_using_its_token(db):
    auth.signup(db, "a@b.com", "correct-horse")
    sub = str(auth.users(db).find_one({"email": "a@b.com"})["_id"])
    auth.users(db).delete_one({"email": "a@b.com"})
    with pytest.raises(HTTPException) as e:
        auth.get_account(db, sub)
    assert e.value.status_code == 401


def test_public_view_never_exposes_the_hash(db):
    make_user(db)
    view = auth.public_view(auth.users(db).find_one({"email": "a@b.com"}))
    assert "password_hash" not in view
    assert set(view) == {"sub", "email", "role", "status", "hospital_id", "app_access"}


def test_auth_config_reports_state_without_leaking_the_secret():
    cfg = auth.auth_config()
    assert cfg["secret_configured"] is True
    assert SECRET not in str(cfg)
    assert cfg["roles"] == list(auth.ROLES)


# --------------------------------------------- authenticate: immediate effect
def test_authenticate_returns_the_current_account_for_an_active_user(db):
    make_user(db)
    account = auth.authenticate(db, token_for(db))
    assert (account["role"], account["hospital_id"]) == ("doctor", "demo-hospital-a")


def test_a_role_change_applies_to_the_very_next_request(db):
    """The token still says doctor; the database now says nurse. The database
    wins, without anyone signing in again."""
    make_user(db)
    token = token_for(db)
    auth.users(db).update_one({"email": "a@b.com"}, {"$set": {"role": "nurse"}})
    assert auth.authenticate(db, token)["role"] == "nurse"


def test_a_pending_account_is_refused_data(db):
    token = auth.signup(db, "a@b.com", "correct-horse")["token"]
    with pytest.raises(HTTPException) as e:
        auth.authenticate(db, token)
    assert e.value.status_code == 403


def test_approval_takes_effect_without_signing_in_again(db):
    token = auth.signup(db, "a@b.com", "correct-horse")["token"]
    auth.users(db).update_one({"email": "a@b.com"},
                              {"$set": {"status": "active", "hospital_id": "demo-hospital-a"}})
    assert auth.authenticate(db, token)["status"] == "active"


def test_moving_an_account_back_to_pending_cuts_it_off_immediately(db):
    make_user(db)
    token = token_for(db)
    auth.users(db).update_one({"email": "a@b.com"}, {"$set": {"status": "pending"}})
    with pytest.raises(HTTPException) as e:
        auth.authenticate(db, token)
    assert e.value.status_code == 403


def test_a_deleted_account_is_refused_even_with_an_unexpired_token(db):
    make_user(db)
    token = token_for(db)
    auth.users(db).delete_one({"email": "a@b.com"})
    with pytest.raises(HTTPException) as e:
        auth.authenticate(db, token)
    assert e.value.status_code == 401


def test_pending_accounts_may_ask_who_they_are(db):
    token = auth.signup(db, "a@b.com", "correct-horse")["token"]
    assert auth.authenticate(db, token, allow_pending=True)["status"] == "pending"


def test_an_account_without_access_to_the_app_is_refused(db):
    make_user(db, app_access=["glp1"])
    with pytest.raises(HTTPException) as e:
        auth.authenticate(db, token_for(db), app="readmissions")
    assert e.value.status_code == 403


@pytest.mark.parametrize("header", [None, "", "Bearer", "Bearer   ", "Basic abc", "token-only"])
def test_a_missing_or_malformed_authorization_header_is_refused(header):
    with pytest.raises(HTTPException) as e:
        auth.bearer_token(header)
    assert e.value.status_code == 401


# ------------------------------------------------------------------ refresh
def test_refresh_carries_the_current_claims_and_keeps_the_expiry(db):
    token = auth.signup(db, "a@b.com", "correct-horse")["token"]
    old_exp = jwt.decode(token, SECRET, algorithms=["HS256"])["exp"]
    auth.users(db).update_one({"email": "a@b.com"},
                              {"$set": {"status": "active", "role": "doctor",
                                        "hospital_id": "demo-hospital-a"}})
    c = claims_of(auth.refresh(db, token))
    assert (c["status"], c["role"], c["hospital_id"]) == ("active", "doctor", "demo-hospital-a")
    assert c["exp"] == old_exp                        # a refresh never extends a session


def test_refresh_refuses_a_deleted_account(db):
    make_user(db)
    token = token_for(db)
    auth.users(db).delete_one({"email": "a@b.com"})
    with pytest.raises(HTTPException) as e:
        auth.refresh(db, token)
    assert e.value.status_code == 401


# --------------------------------------------------- the /api/* request guard
@pytest.fixture
def client(db):
    """A minimal app guarded exactly as api.main guards every /api/* route."""
    app = FastAPI(dependencies=[Depends(auth.user_dependency(lambda: db, app="readmissions"))])

    @app.get("/api/patients")
    def patients():
        return {"ok": True}

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    return TestClient(app)


def test_the_guard_refuses_api_calls_without_a_token(client):
    assert client.get("/api/patients").status_code == 401


def test_the_guard_admits_an_active_user(db, client):
    make_user(db)
    r = client.get("/api/patients", headers={"Authorization": f"Bearer {token_for(db)}"})
    assert r.status_code == 200


def test_the_guard_refuses_a_pending_user(db, client):
    token = auth.signup(db, "a@b.com", "correct-horse")["token"]
    r = client.get("/api/patients", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_the_guard_leaves_paths_outside_api_alone(client):
    """Health checks answer without a user, or a platform restarts a healthy
    container."""
    assert client.get("/healthz").status_code == 200


# ------------------------------------------------------- superadmin bootstrap
def test_bootstrap_creates_an_active_superadmin_with_no_hospital(db):
    auth.bootstrap_superadmin(db, "Ops@Team.com", "correct-horse")
    c = claims_of(auth.login(db, "ops@team.com", "correct-horse"))
    assert (c["role"], c["status"], c["hospital_id"]) == ("superadmin", "active", None)


def test_bootstrap_promotes_an_existing_account_and_keeps_its_password(db):
    auth.signup(db, "a@b.com", "correct-horse")
    auth.bootstrap_superadmin(db, "a@b.com")
    assert claims_of(auth.login(db, "a@b.com", "correct-horse"))["role"] == "superadmin"


def test_bootstrap_needs_a_password_for_a_new_account(db):
    with pytest.raises(HTTPException):
        auth.bootstrap_superadmin(db, "new@team.com", None)
    assert auth.users(db).find_one({"email": "new@team.com"}) is None


# ---------------------------------------------------------------- backfill
def test_backfill_rewrites_legacy_accounts_and_leaves_current_ones_alone(db):
    auth.users(db).insert_many([
        {"email": "old1@test.com", "role": "Doctor", "password_hash": "x"},
        {"email": "old2@test.com", "role": "superadmin", "password_hash": "x"},
    ])
    make_user(db, email="new@test.com", role="nurse", hospital_id="demo-hospital-c")

    assert auth.backfill_users(db) == 2
    for email in ("old1@test.com", "old2@test.com"):
        doc = auth.users(db).find_one({"email": email})
        assert (doc["role"], doc["status"], doc["hospital_id"]) == \
            ("case_manager", "active", None)
    current = auth.users(db).find_one({"email": "new@test.com"})
    assert (current["role"], current["hospital_id"]) == ("nurse", "demo-hospital-c")


def test_backfill_is_idempotent(db):
    auth.users(db).insert_one({"email": "old@test.com", "role": "Doctor", "password_hash": "x"})
    auth.backfill_users(db)
    assert auth.backfill_users(db) == 0


def test_the_database_validator_allows_exactly_the_fixed_roles_and_statuses():
    props = auth.USERS_VALIDATOR["$jsonSchema"]["properties"]
    assert props["role"]["enum"] == list(auth.ROLES)
    assert props["status"]["enum"] == list(auth.STATUSES)
    assert {"role", "status"} <= set(auth.USERS_VALIDATOR["$jsonSchema"]["required"])
