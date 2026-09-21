"""
Unit tests for Backend/routers/auth.py.

These patch core.mongo.get_db with an in-memory fake, so tests run fast
and never touch the real Atlas cluster or leave test users behind.

Run from inside Backend/ (with venv active):
    pytest tests/test_auth.py -v
"""

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from routers import auth as auth_module
from schemas.user import UserCreate, UserLogin


class FakeObjectId:
    """Minimal stand-in for bson.ObjectId — just needs str()."""
    _counter = 0

    def __init__(self):
        FakeObjectId._counter += 1
        self._id = f"fakeid{FakeObjectId._counter:06d}"

    def __str__(self):
        return self._id


class FakeInsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class FakeUsersCollection:
    """In-memory stand-in for db.users, supporting only what auth.py calls."""

    def __init__(self):
        self._docs = {}

    async def find_one(self, query):
        return self._docs.get(query.get("email"))

    async def insert_one(self, doc):
        oid = FakeObjectId()
        self._docs[doc["email"]] = {**doc, "_id": oid}
        return FakeInsertResult(oid)


class FakeDB:
    def __init__(self):
        self.users = FakeUsersCollection()


@pytest.fixture
def fake_db():
    return FakeDB()


@pytest.fixture(autouse=True)
def patch_get_db(fake_db):
    with patch.object(auth_module, "get_db", return_value=fake_db):
        yield fake_db


# ---------- password hashing ----------

def test_hash_password_does_not_return_plaintext():
    hashed = auth_module._hash_password("mypassword123")
    assert hashed != "mypassword123"


def test_hash_password_uses_a_fresh_salt_each_time():
    h1 = auth_module._hash_password("samepassword")
    h2 = auth_module._hash_password("samepassword")
    assert h1 != h2


def test_verify_password_correct():
    hashed = auth_module._hash_password("correcthorse")
    assert auth_module._verify_password("correcthorse", hashed) is True


def test_verify_password_incorrect():
    hashed = auth_module._hash_password("correcthorse")
    assert auth_module._verify_password("wrongpassword", hashed) is False


# ---------- token creation ----------

def test_create_token_looks_like_a_jwt():
    token = auth_module._create_token("user123", "a@b.com")
    assert isinstance(token, str)
    assert len(token.split(".")) == 3  # header.payload.signature


# ---------- register ----------

@pytest.mark.asyncio
async def test_register_creates_new_user(fake_db):
    body = UserCreate(email="new@example.com", password="testpass123")
    result = await auth_module.register(body)
    assert result.user.email == "new@example.com"
    assert result.access_token
    assert "new@example.com" in fake_db.users._docs


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email(fake_db):
    body = UserCreate(email="dupe@example.com", password="testpass123")
    await auth_module.register(body)

    with pytest.raises(HTTPException) as exc_info:
        await auth_module.register(body)
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_register_lowercases_email(fake_db):
    body = UserCreate(email="MixedCase@Example.com", password="testpass123")
    result = await auth_module.register(body)
    assert result.user.email == "mixedcase@example.com"


@pytest.mark.asyncio
async def test_register_never_exposes_password_hash(fake_db):
    body = UserCreate(email="secure@example.com", password="testpass123")
    result = await auth_module.register(body)
    assert not hasattr(result.user, "password")
    assert not hasattr(result.user, "password_hash")


# ---------- login ----------

@pytest.mark.asyncio
async def test_login_succeeds_with_correct_password(fake_db):
    await auth_module.register(UserCreate(email="login@example.com", password="rightpass"))
    result = await auth_module.login(UserLogin(email="login@example.com", password="rightpass"))
    assert result.user.email == "login@example.com"
    assert result.access_token


@pytest.mark.asyncio
async def test_login_fails_with_wrong_password(fake_db):
    await auth_module.register(UserCreate(email="login2@example.com", password="rightpass"))
    with pytest.raises(HTTPException) as exc_info:
        await auth_module.login(UserLogin(email="login2@example.com", password="wrongpass"))
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_login_fails_for_nonexistent_user(fake_db):
    with pytest.raises(HTTPException) as exc_info:
        await auth_module.login(UserLogin(email="ghost@example.com", password="whatever"))
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_login_is_case_insensitive_on_email(fake_db):
    await auth_module.register(UserCreate(email="case@example.com", password="testpass123"))
    result = await auth_module.login(UserLogin(email="CASE@EXAMPLE.com", password="testpass123"))
    assert result.user.email == "case@example.com"