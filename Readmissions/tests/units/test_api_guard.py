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


# ------------------------------------------------------- User Management
def admin_routes(service):
    for route in service.app.routes:
        if isinstance(route, APIRoute) and route.path.startswith("/auth/admin/"):
            for method in route.methods:
                yield method, re.sub(r"\{[^}]+\}", "x", route.path)


def active_account(db, email, role, hospital_id="demo-hospital-a", **extra):
    auth.users(db).insert_one({"email": email, "role": role, "status": "active",
                               "hospital_id": hospital_id,
                               "password_hash": auth.hash_password("correct-horse"), **extra})
    return auth.login(db, email, "correct-horse")["token"]


def test_every_admin_route_refuses_a_request_without_a_token(main, db):
    client = TestClient(main.app)
    routes = list(admin_routes(main))
    assert len(routes) >= 7
    assert [(m, p) for m, p in routes if client.request(m, p).status_code != 401] == []


def test_every_admin_route_refuses_staff_who_are_not_managers(main, db):
    token = active_account(db, "doc@a.org", "doctor")
    client = TestClient(main.app, headers={"Authorization": f"Bearer {token}"})
    assert [(m, p) for m, p in admin_routes(main)
            if client.request(m, p, json={}).status_code != 403] == []


def test_user_management_skips_the_api_key_but_data_routes_do_not(main, db, monkeypatch):
    """GLP-1 calls User Management without our service key, so /auth/* cannot
    need it - while /api/* still does."""
    monkeypatch.setattr(main, "API_KEY", "service-key")
    token = active_account(db, "ops@team.com", "superadmin", hospital_id=None)
    client = TestClient(main.app, headers={"Authorization": f"Bearer {token}"})
    assert client.get("/auth/admin/users").status_code == 200
    assert client.get("/api/summary").status_code == 401             # no key
    assert client.get("/api/summary", headers={"X-API-Key": "service-key"}).status_code \
        not in (401, 403)


def test_a_temporary_password_is_refused_on_every_data_route(main, db):
    token = active_account(db, "doc@a.org", "doctor", must_change_password=True)
    client = TestClient(main.app, headers={"Authorization": f"Bearer {token}"})
    assert [(m, p) for m, p in api_routes(main) if client.request(m, p).status_code != 403] == []
    me = client.get("/auth/me")
    assert me.status_code == 200 and me.json()["must_change_password"] is True


def test_the_admin_endpoints_work_end_to_end_for_a_hospital_admin(main, db):
    sa = active_account(db, "ops@team.com", "superadmin", hospital_id=None)
    as_sa = TestClient(main.app, headers={"Authorization": f"Bearer {sa}"})
    assert as_sa.post("/auth/admin/hospitals", json={"name": "Demo Hospital A"}).status_code == 201

    admin = active_account(db, "admin@a.org", "hospital_admin")
    as_admin = TestClient(main.app, headers={"Authorization": f"Bearer {admin}"})
    created = as_admin.post("/auth/admin/users", json={"email": "doc@a.org", "role": "doctor",
                                                       "name": "Dr A"})
    assert created.status_code == 201
    temp = created.json()["temporary_password"]

    # The new doctor signs in, is made to change the temporary password, then works.
    doc_token = TestClient(main.app).post("/auth/login", json={"email": "doc@a.org",
                                                              "password": temp}).json()["token"]
    as_doc = TestClient(main.app, headers={"Authorization": f"Bearer {doc_token}"})
    assert as_doc.get("/api/summary").status_code == 403
    changed = as_doc.post("/auth/change-password", json={"current_password": temp,
                                                         "new_password": "my-own-password"})
    assert changed.status_code == 200
    fresh = TestClient(main.app, headers={"Authorization": f"Bearer {changed.json()['token']}"})
    assert fresh.get("/api/summary").status_code not in (401, 403)

    user_id = next(u["sub"] for u in as_admin.get("/auth/admin/users").json()
                   if u["email"] == "doc@a.org")
    assert as_admin.patch(f"/auth/admin/users/{user_id}",
                          json={"role": "nurse"}).json()["role"] == "nurse"
