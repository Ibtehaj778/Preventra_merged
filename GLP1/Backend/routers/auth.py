"""
Shared auth service (Task A). Serves both GLP-1 and Preventra —
reads/writes shared_identity.users instead of GLP-1's own database.
"""

import re
from datetime import datetime, timedelta, timezone
from pymongo.errors import DuplicateKeyError

import bcrypt
from fastapi import APIRouter, HTTPException
from jose import jwt

from core.config import settings
from core.mongo import get_shared_identity_db
from schemas.user import SignupRequest, UserLogin, UserPublic, TokenResponse, VALID_ROLES, ROLE_APP_ACCESS

router = APIRouter(prefix="/auth", tags=["auth"])

_ALGORITHM = "HS256"
_TOKEN_EXPIRE_MINUTES = 60 * 12  # 12h


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def _slugify_org(org_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", org_name.strip().lower())
    return slug.strip("-") or "org"


def _create_token(user_id: str, email: str, role: str, org_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "org_id": org_id,
        "app_access": ROLE_APP_ACCESS[role],
        "exp": expire,
    }
    return jwt.encode(payload, settings.shared_secret_key, algorithm=_ALGORITHM)


@router.post("/signup", response_model=TokenResponse, status_code=201)
async def signup(body: SignupRequest):
    if body.role not in VALID_ROLES:
        raise HTTPException(status_code=422, detail=f"role must be one of {VALID_ROLES}")

    db = get_shared_identity_db()
    org_id = _slugify_org(body.org_name)

    existing = await db.users.find_one({"email": body.email.lower()})
    if existing is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    doc = {
        "email":         body.email.lower(),
        "password_hash": _hash_password(body.password),
        "role":          body.role,
        "org_id":        org_id,
        "org_name":      body.org_name,
        "created_at":    datetime.now(timezone.utc),
    }
    try:
        result = await db.users.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    user_id = str(result.inserted_id)
    return TokenResponse(
        access_token=_create_token(user_id, doc["email"], doc["role"], org_id),
        user=UserPublic(id=user_id, email=doc["email"], role=doc["role"], org_id=org_id),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin):
    db = get_shared_identity_db()

    doc = await db.users.find_one({"email": body.email.lower()})
    if doc is None or not _verify_password(body.password, doc["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user_id = str(doc["_id"])
    return TokenResponse(
        access_token=_create_token(user_id, doc["email"], doc["role"], doc["org_id"]),
        user=UserPublic(id=user_id, email=doc["email"], role=doc["role"], org_id=doc["org_id"]),
    )