"""User Management: hospitals, insurers, and the accounts that work for them.

Accounts are shared by both products, so this lives once, here in the shared
auth service, and both apps' Settings pages call it.

Who may do what - enforced here, never only in a frontend:

    superadmin      creates hospitals, insurers and hospital admins; manages
                    every account except other superadmins
    hospital_admin  manages doctors, nurses, case managers and patients in its
                    own hospital, and nothing outside it

No path here can create a superadmin or promote anyone to one; that is
scripts/create_superadmin.py, run by someone with direct cluster access.

Approving a self-signup: a hospital admin adds the person by email. If that
email is a pending account not yet attached anywhere, it is attached and
activated instead of being refused as a duplicate. So hospital admins approve
their own people without ever seeing a list of other hospitals' signups; only
the superadmin sees every pending account.
"""
from __future__ import annotations

import csv
import io
import secrets
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException

from api import auth

HOSPITALS = "hospitals"
INSURERS = "insurers"

MANAGER_ROLES = ("superadmin", "hospital_admin")

# Which roles each manager may hand out. superadmin is absent from both on
# purpose: it is never assignable through this module.
ASSIGNABLE = {
    "superadmin": tuple(r for r in auth.ROLES if r != "superadmin"),
    "hospital_admin": ("doctor", "nurse", "case_manager", "patient"),
}

MAX_IMPORT_ROWS = 1000

# No 0/O or 1/l/I: the admin reads this out or types it into a message.
_TEMP_ALPHABET = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _identity(db):
    return db.client[auth.IDENTITY_DB]


def hospitals(db):
    return _identity(db)[HOSPITALS]


def insurers(db):
    return _identity(db)[INSURERS]


def temporary_password() -> str:
    return "".join(secrets.choice(_TEMP_ALPHABET) for _ in range(12))


def _forbidden(detail: str):
    return HTTPException(status_code=403, detail=detail)


def require_manager(actor: dict) -> None:
    if actor["role"] not in MANAGER_ROLES:
        raise _forbidden("Only a superadmin or a hospital admin can manage users")


def _require_superadmin(actor: dict) -> None:
    if actor["role"] != "superadmin":
        raise _forbidden("Only a superadmin can do this")


def admin_view(account: dict) -> dict:
    """An account as it appears in User Management. Never the password hash."""
    account = auth.effective(account)
    return {**auth.public_view(account),
            "name": account.get("name", ""),
            "insurer_id": account.get("insurer_id"),
            "must_change_password": bool(account.get("must_change_password")),
            "created_at": account.get("created_at", "")}


# ------------------------------------------------------- organisations
def _create_org(collection, actor: dict, name: str) -> dict:
    name = (name or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="A name is required")
    doc = {"_id": auth.slugify_org(name), "name": name,
           "created_at": auth._now(), "created_by": actor["email"]}
    if collection.find_one({"_id": doc["_id"]}):
        raise HTTPException(status_code=409, detail=f"'{doc['_id']}' already exists")
    collection.insert_one(doc)
    return {"id": doc["_id"], "name": name}


def create_hospital(db, actor: dict, name: str) -> dict:
    _require_superadmin(actor)
    return _create_org(hospitals(db), actor, name)


def create_insurer(db, actor: dict, name: str) -> dict:
    _require_superadmin(actor)
    return _create_org(insurers(db), actor, name)


def list_hospitals(db, actor: dict) -> list:
    """Every hospital for the superadmin; only its own for a hospital admin."""
    require_manager(actor)
    query = {} if actor["role"] == "superadmin" else {"_id": actor["hospital_id"]}
    return [{"id": h["_id"], "name": h["name"]}
            for h in hospitals(db).find(query).sort("name", 1)]


def list_insurers(db, actor: dict) -> list:
    require_manager(actor)
    return [{"id": i["_id"], "name": i["name"]} for i in insurers(db).find().sort("name", 1)]


# ------------------------------------------------------------ rules
def _check_assignable(actor: dict, role: str) -> None:
    if role not in auth.ROLES:
        raise HTTPException(status_code=422, detail=f"Unknown role '{role}'")
    if role not in ASSIGNABLE[actor["role"]]:
        raise _forbidden(f"A {actor['role']} cannot assign the role '{role}'")


def _placement(db, actor: dict, role: str, hospital_id: Optional[str],
               insurer_id: Optional[str]) -> dict:
    """Where an account with this role belongs, checked against what exists and
    what the actor may touch. A hospital admin can only ever place people in
    its own hospital, whatever the request says."""
    if role in auth.HOSPITAL_ROLES:
        if actor["role"] == "hospital_admin":
            hospital_id = actor["hospital_id"]
        if not hospital_id:
            raise HTTPException(status_code=422, detail=f"A {role} must belong to a hospital")
        if not hospitals(db).find_one({"_id": hospital_id}):
            raise HTTPException(status_code=422, detail=f"No hospital '{hospital_id}'")
        return {"hospital_id": hospital_id, "insurer_id": None}
    if role == "insurer":
        if not insurer_id:
            raise HTTPException(status_code=422, detail="An insurer account must belong to an insurer")
        if not insurers(db).find_one({"_id": insurer_id}):
            raise HTTPException(status_code=422, detail=f"No insurer '{insurer_id}'")
        return {"hospital_id": None, "insurer_id": insurer_id}
    return {"hospital_id": None, "insurer_id": None}


def _load_target(db, actor: dict, user_id: str) -> dict:
    try:
        target = auth.users(db).find_one({"_id": ObjectId(user_id)})
    except (InvalidId, TypeError):
        target = None
    # The same answer for "does not exist" and "not yours", so a hospital admin
    # cannot probe for accounts in other hospitals.
    if not target or not _may_manage(actor, auth.effective(target)):
        raise HTTPException(status_code=404, detail="No such user")
    return target


def _may_manage(actor: dict, target: dict) -> bool:
    if target["role"] == "superadmin" or str(target["_id"]) == str(actor["_id"]):
        return False                       # no one edits a superadmin, or themselves
    if actor["role"] == "superadmin":
        return True
    return (target["hospital_id"] == actor["hospital_id"]
            and target["role"] in ASSIGNABLE["hospital_admin"])


# ------------------------------------------------------------ accounts
def list_users(db, actor: dict, hospital_id: Optional[str] = None,
               status: Optional[str] = None) -> list:
    require_manager(actor)
    query: dict = {}
    if actor["role"] == "hospital_admin":
        query["hospital_id"] = actor["hospital_id"]
    elif hospital_id:
        query["hospital_id"] = hospital_id
    if status:
        query["status"] = status
    return [admin_view(u) for u in
            auth.users(db).find(query, {"password_hash": 0}).sort("created_at", -1)]


def create_user(db, actor: dict, email: str, role: str, name: str = "",
                hospital_id: Optional[str] = None, insurer_id: Optional[str] = None) -> dict:
    """Add an account with a temporary password, or approve a pending self-signup
    with the same email. Returns the account and, for a new one, the temporary
    password - shown once and never stored in plain text."""
    require_manager(actor)
    _check_assignable(actor, role)
    email = auth.normalise_email(email)
    if not auth._EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="A valid email address is required")
    place = _placement(db, actor, role, hospital_id, insurer_id)
    now = auth._now()
    fields = {"role": role, "status": "active", "name": (name or "").strip(),
              **place, "updated_at": now}

    existing = auth.users(db).find_one({"email": email})
    if existing:
        current = auth.effective(existing)
        unattached_signup = (current["status"] == "pending" and not current["hospital_id"]
                             and not existing.get("insurer_id"))
        if not unattached_signup:
            raise HTTPException(status_code=409, detail="An account with that email already exists")
        auth.users(db).update_one({"_id": existing["_id"]},
                                  {"$set": {**fields, "approved_by": actor["email"]}})
        return {"user": admin_view({**existing, **fields}), "temporary_password": None,
                "approved_existing": True}

    password = temporary_password()
    doc = {"email": email, "password_hash": auth.hash_password(password),
           "must_change_password": True,
           "app_access": list(auth.DEFAULT_APP_ACCESS),
           "created_at": now, "created_by": actor["email"], **fields}
    try:
        doc["_id"] = auth.users(db).insert_one(doc).inserted_id
    except Exception as exc:
        if "duplicate key" in str(exc).lower() or "E11000" in str(exc):
            raise HTTPException(status_code=409,
                                detail="An account with that email already exists") from exc
        raise
    return {"user": admin_view(doc), "temporary_password": password, "approved_existing": False}


def update_user(db, actor: dict, user_id: str, role: Optional[str] = None,
                status: Optional[str] = None, hospital_id: Optional[str] = None,
                insurer_id: Optional[str] = None, name: Optional[str] = None) -> dict:
    """Change a role, approve or suspend (status), move or name an account."""
    require_manager(actor)
    target = _load_target(db, actor, user_id)
    current = auth.effective(target)

    new_role = role or current["role"]
    if role is not None:
        _check_assignable(actor, role)
    if status is not None and status not in auth.STATUSES:
        raise HTTPException(status_code=422, detail=f"Status must be one of {list(auth.STATUSES)}")

    place = _placement(db, actor, new_role,
                       hospital_id if hospital_id is not None else current["hospital_id"],
                       insurer_id if insurer_id is not None else target.get("insurer_id"))
    fields = {"role": new_role, "status": status or current["status"], **place,
              "updated_at": auth._now()}
    if name is not None:
        fields["name"] = name.strip()
    auth.users(db).update_one({"_id": target["_id"]}, {"$set": fields})
    return admin_view({**target, **fields})


def import_users(db, actor: dict, csv_text: str, hospital_id: Optional[str] = None,
                 insurer_id: Optional[str] = None) -> dict:
    """Create accounts from CSV with columns email, name, role (header row
    required). Each row succeeds or fails on its own, so one bad line does not
    lose the rest; failures come back with their line number."""
    require_manager(actor)
    reader = csv.DictReader(io.StringIO((csv_text or "").strip()))
    columns = {c.strip().lower() for c in (reader.fieldnames or [])}
    if not {"email", "role"} <= columns:
        raise HTTPException(status_code=422,
                            detail="The CSV needs a header row with at least: email, role (and optionally name)")
    rows = list(reader)
    if len(rows) > MAX_IMPORT_ROWS:
        raise HTTPException(status_code=422, detail=f"At most {MAX_IMPORT_ROWS} rows per import")

    created, failed = [], []
    for line, row in enumerate(rows, start=2):          # line 1 is the header
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        try:
            result = create_user(db, actor, row.get("email", ""), row.get("role", "").lower(),
                                 row.get("name", ""), hospital_id, insurer_id)
            created.append({"line": line, **result})
        except HTTPException as exc:
            failed.append({"line": line, "email": row.get("email", ""), "error": exc.detail})
    return {"created": created, "failed": failed}


# ------------------------------------------------------------ own password
def change_password(db, token: str, current_password: str, new_password: str) -> dict:
    """Replace your own password, clearing the must-change flag a temporary
    password carries. Returns a token with the updated claims."""
    claims = auth.decode_token(token)
    account = auth.authenticate(db, token, allow_pending=True, allow_password_change=True)
    if not auth.password_matches(current_password or "", account.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="The current password is incorrect")
    if len(new_password or "") < auth.MIN_PASSWORD_LENGTH:
        raise HTTPException(status_code=422, detail=f"The new password must be at least "
                                                    f"{auth.MIN_PASSWORD_LENGTH} characters")
    if new_password == current_password:
        raise HTTPException(status_code=422, detail="Choose a password different from the current one")
    fields = {"password_hash": auth.hash_password(new_password),
              "must_change_password": False, "updated_at": auth._now()}
    auth.users(db).update_one({"_id": account["_id"]}, {"$set": fields})
    return auth.issue_token({**account, **fields}, exp=claims["exp"])
