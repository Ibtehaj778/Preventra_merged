"""Shared login: password handling, token issue, and the rules around both.

Runs against mongomock, so the suite never touches the real identity collection
and never depends on the cluster being reachable.
"""
import time

import bcrypt
import jwt
import mongomock
import pytest
from fastapi import HTTPException

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


# ------------------------------------------------------------------- signup
def test_signup_returns_a_token_carrying_the_agreed_claims(db):
    out = auth.signup(db, "New.User@Test.com", "correct-horse", "Doctor", "City Hospital")
    c = claims_of(out)
    assert set(c) == {"sub", "email", "role", "org_id", "app_access", "exp"}
    assert c["email"] == "new.user@test.com"          # normalised
    assert c["role"] == "Doctor"
    assert c["org_id"] == "city-hospital"             # slugified to match existing data
    assert c["app_access"] == ["glp1", "readmissions"]


def test_signup_stores_a_bcrypt_hash_and_never_the_password(db):
    auth.signup(db, "a@b.com", "correct-horse", "Nurse", "St Mary")
    stored = auth.users(db).find_one({"email": "a@b.com"})
    assert stored["password_hash"].startswith("$2b$12$")
    assert len(stored["password_hash"]) == 60
    assert "correct-horse" not in str(stored)


def test_signup_refuses_a_duplicate_email(db):
    auth.ensure_indexes(db)
    auth.signup(db, "dup@test.com", "correct-horse", "Doctor", "X")
    with pytest.raises(HTTPException) as e:
        auth.signup(db, "dup@test.com", "another-password", "Nurse", "Y")
    assert e.value.status_code == 409


@pytest.mark.parametrize("email", ["", "not-an-email", "a@b", "a b@c.com"])
def test_signup_refuses_a_malformed_email(db, email):
    with pytest.raises(HTTPException) as e:
        auth.signup(db, email, "correct-horse", "Doctor", "X")
    assert e.value.status_code == 422


def test_signup_refuses_a_short_password(db):
    with pytest.raises(HTTPException) as e:
        auth.signup(db, "a@b.com", "short", "Doctor", "X")
    assert e.value.status_code == 422


def test_signup_refuses_a_blank_role(db):
    with pytest.raises(HTTPException) as e:
        auth.signup(db, "a@b.com", "correct-horse", "   ", "X")
    assert e.value.status_code == 422


def test_an_organisation_with_no_name_still_gets_a_usable_org_id(db):
    assert claims_of(auth.signup(db, "a@b.com", "correct-horse", "Doctor", ""))["org_id"] \
        == "unaffiliated"


# -------------------------------------------------------------------- login
def test_login_succeeds_with_the_right_password(db):
    auth.signup(db, "a@b.com", "correct-horse", "Doctor", "City Hospital")
    assert claims_of(auth.login(db, "a@b.com", "correct-horse"))["email"] == "a@b.com"


def test_login_is_case_insensitive_on_the_email(db):
    auth.signup(db, "a@b.com", "correct-horse", "Doctor", "X")
    assert auth.login(db, "  A@B.COM  ", "correct-horse")["token"]


def test_login_refuses_the_wrong_password(db):
    auth.signup(db, "a@b.com", "correct-horse", "Doctor", "X")
    with pytest.raises(HTTPException) as e:
        auth.login(db, "a@b.com", "wrong-password")
    assert e.value.status_code == 401


def test_an_unknown_account_and_a_wrong_password_are_indistinguishable(db):
    """Different messages here would let anyone enumerate registered emails."""
    auth.signup(db, "a@b.com", "correct-horse", "Doctor", "X")
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
    assert claims_of(auth.login(db, "doc@test.com", "their-password"))["role"] == "Doctor"


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


# -------------------------------------------------------------- token shape
def test_the_token_expires_and_carries_the_configured_lifetime(db):
    out = auth.signup(db, "a@b.com", "correct-horse", "Doctor", "X")
    assert out["expires_in"] == 3600
    assert 3500 < claims_of(out)["exp"] - time.time() <= 3600


def test_the_subject_is_the_account_id_so_each_product_can_look_the_user_up(db):
    out = auth.signup(db, "a@b.com", "correct-horse", "Doctor", "X")
    assert claims_of(out)["sub"] == str(auth.users(db).find_one({"email": "a@b.com"})["_id"])


def test_the_response_never_carries_the_password_hash(db):
    out = auth.signup(db, "a@b.com", "correct-horse", "Doctor", "X")
    assert "password" not in str(out).lower()


def test_tokens_cannot_be_issued_without_a_secret(db, monkeypatch):
    monkeypatch.setattr(auth, "SHARED_SECRET_KEY", "")
    with pytest.raises(HTTPException) as e:
        auth.signup(db, "a@b.com", "correct-horse", "Doctor", "X")
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
    auth.signup(db, "a@b.com", "correct-horse", "Doctor", "X")
    sub = str(auth.users(db).find_one({"email": "a@b.com"})["_id"])
    auth.users(db).update_one({"email": "a@b.com"}, {"$set": {"role": "Nurse"}})
    assert auth.public_view(auth.get_account(db, sub))["role"] == "Nurse"


@pytest.mark.parametrize("sub", ["not-an-object-id", "", None])
def test_a_token_with_an_unusable_subject_is_refused(db, sub):
    with pytest.raises(HTTPException) as e:
        auth.get_account(db, sub)
    assert e.value.status_code == 401


def test_a_deleted_account_cannot_keep_using_its_token(db):
    auth.signup(db, "a@b.com", "correct-horse", "Doctor", "X")
    sub = str(auth.users(db).find_one({"email": "a@b.com"})["_id"])
    auth.users(db).delete_one({"email": "a@b.com"})
    with pytest.raises(HTTPException) as e:
        auth.get_account(db, sub)
    assert e.value.status_code == 401


def test_public_view_never_exposes_the_hash(db):
    auth.signup(db, "a@b.com", "correct-horse", "Doctor", "City Hospital")
    view = auth.public_view(auth.users(db).find_one({"email": "a@b.com"}))
    assert "password_hash" not in view
    assert set(view) == {"sub", "email", "role", "org_id", "org_name", "app_access"}


def test_auth_config_reports_state_without_leaking_the_secret():
    cfg = auth.auth_config()
    assert cfg["secret_configured"] is True
    assert SECRET not in str(cfg)
