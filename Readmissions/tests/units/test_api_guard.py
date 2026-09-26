"""Every /api/* route in the real service refuses anyone who is not an active,
signed-in user.

Walks the routes of api.main itself rather than a copy, so a route added later
is covered without anyone remembering to add a test for it. The service's
database handle is swapped for mongomock; nothing here reaches a cluster.
"""
import os
import re

import mongomock
import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from api import auth

SECRET = "test-secret-not-the-real-one"


@pytest.fixture(scope="module")
def main():
    # Point the import-time client at nothing, briefly, so importing the service
    # neither needs nor waits on a real cluster.
    os.environ.setdefault("MONGO_URI", "mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=100")
    from api import main as service
    return service


@pytest.fixture
def db(main, monkeypatch):
    fake = mongomock.MongoClient()["neuroshield"]
    monkeypatch.setattr(main, "db", fake)            # require_user looks `db` up per request
    monkeypatch.setattr(main, "API_KEY", None)       # isolate the user check from the key check
    monkeypatch.setattr(auth, "SHARED_SECRET_KEY", SECRET)
    return fake


def api_routes(service):
    for route in service.app.routes:
        if isinstance(route, APIRoute) and route.path.startswith("/api/"):
            for method in route.methods:
                yield method, re.sub(r"\{[^}]+\}", "x", route.path)


def test_the_guard_is_installed_on_the_whole_app(main):
    names = [d.dependency.__name__ for d in main.app.router.dependencies]
    assert "require_user" in names


def test_every_api_route_refuses_a_request_without_a_token(main, db):
    client = TestClient(main.app)
    routes = list(api_routes(main))
    assert len(routes) > 30                           # the walk found the real routes
    let_through = [(m, p) for m, p in routes
                   if client.request(m, p).status_code != 401]
    assert let_through == []


def test_every_api_route_refuses_a_pending_account(main, db):
    token = auth.signup(db, "a@b.com", "correct-horse")["token"]
    client = TestClient(main.app, headers={"Authorization": f"Bearer {token}"})
    let_through = [(m, p) for m, p in api_routes(main)
                   if client.request(m, p).status_code != 403]
    assert let_through == []


def test_an_active_user_gets_past_the_guard(main, db):
    auth.users(db).insert_one({"email": "doc@test.com", "role": "doctor", "status": "active",
                               "hospital_id": "demo-hospital-a",
                               "password_hash": auth.hash_password("correct-horse")})
    token = auth.login(db, "doc@test.com", "correct-horse")["token"]
    r = TestClient(main.app).get("/api/summary", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code not in (401, 403)


def test_the_login_endpoints_stay_open(main, db):
    """The portal calls these before anyone has a token."""
    client = TestClient(main.app)
    assert client.post("/auth/signup", json={"email": "n@test.com",
                                             "password": "correct-horse"}).status_code == 200
    assert client.post("/auth/login", json={"email": "n@test.com",
                                            "password": "correct-horse"}).status_code == 200


def test_signup_ignores_a_role_or_hospital_sent_by_the_client(main, db):
    """Older portals still send them. Neither may stick."""
    client = TestClient(main.app)
    r = client.post("/auth/signup", json={"email": "sneaky@test.com", "password": "correct-horse",
                                          "role": "superadmin", "org_name": "City Hospital"})
    assert r.json()["user"]["role"] == "case_manager"
    assert r.json()["user"]["status"] == "pending"
    assert r.json()["user"]["hospital_id"] is None


def test_me_and_refresh_answer_for_a_pending_account(main, db):
    token = auth.signup(db, "p@test.com", "correct-horse")["token"]
    client = TestClient(main.app, headers={"Authorization": f"Bearer {token}"})
    assert client.get("/auth/me").json()["status"] == "pending"
    assert client.post("/auth/refresh").status_code == 200
