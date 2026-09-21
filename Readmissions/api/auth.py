"""Shared login: the service that issues tokens for both products.

One account works across GLP-1 and Readmissions. This module owns the identity
side of that: it stores accounts in `shared_identity.users` on the shared
cluster, checks passwords, and signs a JWT that either product can verify on its
own with the same secret.

Issuing lives in exactly one place - here. Each product verifies independently
and never calls back, which is what keeps the two backends separately
deployable. A second service that also issued tokens would put us back to two
logins, which is the problem this replaces.

Compatibility matters: accounts already exist in that collection, created
elsewhere with bcrypt at cost 12 (`$2b$12$`, 60 chars). The hashing here matches,
so those accounts keep working and nobody has to reset a password.

Token claims, frozen by agreement between both products:

    {"sub": "<users._id as a string>", "email": ..., "role": ...,
     "org_id": ..., "app_access": ["glp1", "readmissions"], "exp": <unix>}
"""
from __future__ import annotations

import os
import re
import time
from datetime import datetime
from typing import Optional

import bcrypt
import jwt
from bson import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv
from fastapi import HTTPException

# Loaded here rather than left to the importer: api.main calls load_dotenv()
# after importing this module, so without this the secret below reads as empty
# on any machine that keeps it in .env rather than in real environment
# variables. Idempotent, so the duplicate call costs nothing - do not remove it.
load_dotenv()

# Shared with the other product. Symmetric (HS256): holding it means being able
# to MINT tokens, not merely check them, so it must never reach a browser bundle
# or a commit.
SHARED_SECRET_KEY = os.environ.get("SHARED_SECRET_KEY", "")
ALGORITHM = "HS256"

# 12 hours. Long enough that nobody is signed out mid-session, short enough that
# a token copied out of a URL or a chat log stops working the same day. There is
# no refresh flow yet, so this is also the hard session length.
TOKEN_TTL_SECONDS = int(os.environ.get("SHARED_AUTH_TOKEN_TTL", str(12 * 60 * 60)))

# Which applications a new account may use. Both, by default: the demo has no
# per-product entitlement model, and a user who cannot open either app is
# useless. The value is stored on the account so it can be narrowed per user
# later without changing this code.
DEFAULT_APP_ACCESS = [a.strip() for a in
                      os.environ.get("SHARED_AUTH_DEFAULT_APPS", "glp1,readmissions").split(",")
                      if a.strip()]

IDENTITY_DB = os.environ.get("SHARED_IDENTITY_DB", "shared_identity")
USERS_COLLECTION = "users"

BCRYPT_ROUNDS = 12
MIN_PASSWORD_LENGTH = 8
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Comparing against a real hash when no account exists keeps the failed-login
# path the same cost as the successful one, so response time does not quietly
# reveal which email addresses are registered.
_DUMMY_HASH = bcrypt.hashpw(b"timing-equaliser", bcrypt.gensalt(rounds=BCRYPT_ROUNDS))


def users(db):
    """The shared identity collection. Note this is NOT the product database -
    accounts are deliberately held apart from either product's own data."""
    return db.client[IDENTITY_DB][USERS_COLLECTION]


def ensure_indexes(db) -> None:
    """Guarantee a unique index on email, the account's natural key.

    The constraint has to live in the database, not in a check-then-insert in
    the signup handler: two simultaneous signups would both find nothing and
    both insert. Signup relies on the resulting duplicate-key error.

    An equivalent index may already exist under a different name - the identity
    collection is shared and was created by another codebase - so look before
    creating, or the create fails with a name conflict and the failure says
    nothing about whether the constraint is actually in place.
    """
    collection = users(db)
    try:
        for index in collection.list_indexes():
            if list(index["key"].items()) == [("email", 1)] and index.get("unique"):
                return                                    # already enforced, under any name
        collection.create_index("email", unique=True, name="email_unique")
    except Exception as exc:                              # noqa: BLE001
        # Runs at import: a cluster blip here must not stop the service booting.
        # Surfaced rather than swallowed, because without this index two accounts
        # can share an email and one of them silently becomes unreachable.
        print(f"WARNING: could not verify the unique index on "
              f"{IDENTITY_DB}.{USERS_COLLECTION}.email ({type(exc).__name__}: {exc}). "
              f"Duplicate signups may not be refused.")


# --------------------------------------------------------------------- helpers
def slugify_org(name: str) -> str:
    """"City Hospital" -> "city-hospital". Matches the org_id format already in
    the collection, so accounts created here group with the existing ones."""
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")
    return slug or "unaffiliated"


def normalise_email(email: str) -> str:
    return (email or "").strip().lower()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode()


def password_matches(password: str, stored_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), (stored_hash or "").encode("utf-8"))
    except (ValueError, TypeError):
        # A malformed or truncated hash in the database is not a reason to let
        # someone in.
        return False


def _require_secret() -> None:
    if not SHARED_SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="SHARED_SECRET_KEY is not configured; this service cannot issue tokens")


# ----------------------------------------------------------------- token issue
def issue_token(user: dict) -> dict:
    """Sign a token for an account and return it with the claims it carries."""
    _require_secret()
    claims = {
        "sub": str(user["_id"]),
        "email": user["email"],
        "role": user.get("role", ""),
        "org_id": user.get("org_id", ""),
        # Older accounts predate this field; treat them as having the default
        # rather than locking their owners out of both products.
        "app_access": user.get("app_access") or list(DEFAULT_APP_ACCESS),
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
    }
    return {"token": jwt.encode(claims, SHARED_SECRET_KEY, algorithm=ALGORITHM),
            "token_type": "bearer",
            "expires_in": TOKEN_TTL_SECONDS,
            "user": {"sub": claims["sub"], "email": claims["email"], "role": claims["role"],
                     "org_id": claims["org_id"], "org_name": user.get("org_name", ""),
                     "app_access": claims["app_access"]}}


def decode_token(token: str) -> dict:
    """Verify a token and return its claims. Used by /auth/me; each product does
    the same thing independently with its own copy of this logic."""
    _require_secret()
    try:
        return jwt.decode(token, SHARED_SECRET_KEY, algorithms=[ALGORITHM],
                          options={"require": ["exp"]})
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired; sign in again")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc


# ----------------------------------------------------------------------- signup
def signup(db, email: str, password: str, role: str, org_name: str,
           app_access: Optional[list] = None) -> dict:
    """Create an account and return a signed token for it.

    No email verification and no domain checks, by decision: the demo needs
    someone to be able to sign up and be inside the product seconds later.
    """
    email = normalise_email(email)
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="A valid email address is required")
    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise HTTPException(status_code=422,
                            detail=f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    if not (role or "").strip():
        raise HTTPException(status_code=422, detail="Role is required")

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    doc = {"email": email,
           "password_hash": hash_password(password),
           "role": role.strip(),
           "org_name": (org_name or "").strip(),
           "org_id": slugify_org(org_name),
           "app_access": list(app_access) if app_access else list(DEFAULT_APP_ACCESS),
           "created_at": now,
           "updated_at": now}
    try:
        doc["_id"] = users(db).insert_one(doc).inserted_id
    except Exception as exc:
        if "duplicate key" in str(exc).lower() or "E11000" in str(exc):
            raise HTTPException(status_code=409,
                                detail="An account with that email already exists") from exc
        raise
    return issue_token(doc)


# ------------------------------------------------------------------------ login
def login(db, email: str, password: str) -> dict:
    """Check a password and return a signed token.

    The same message and the same amount of work for an unknown address as for a
    wrong password: distinguishing them tells an attacker which accounts exist.
    """
    account = users(db).find_one({"email": normalise_email(email)})
    stored = account.get("password_hash") if account else _DUMMY_HASH.decode()
    if not password_matches(password or "", stored) or account is None:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return issue_token(account)


def get_account(db, sub: str) -> dict:
    """Look up the account a token refers to, so /auth/me reflects the database
    rather than whatever the token said when it was signed."""
    try:
        account = users(db).find_one({"_id": ObjectId(sub)})
    except (InvalidId, TypeError):
        raise HTTPException(status_code=401, detail="Invalid token subject")
    if not account:
        raise HTTPException(status_code=401, detail="Account no longer exists")
    return account


def public_view(account: dict) -> dict:
    """An account as the portal may see it. Never includes the password hash."""
    return {"sub": str(account["_id"]), "email": account.get("email", ""),
            "role": account.get("role", ""), "org_id": account.get("org_id", ""),
            "org_name": account.get("org_name", ""),
            "app_access": account.get("app_access") or list(DEFAULT_APP_ACCESS)}


def auth_config() -> dict:
    """What this service is configured to do. Reports whether a secret is set,
    never the secret itself, so a broken deploy can be diagnosed over HTTP."""
    return {"secret_configured": bool(SHARED_SECRET_KEY), "algorithm": ALGORITHM,
            "identity_database": IDENTITY_DB, "token_ttl_seconds": TOKEN_TTL_SECONDS,
            "default_app_access": list(DEFAULT_APP_ACCESS)}
