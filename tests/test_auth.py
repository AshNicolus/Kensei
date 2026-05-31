from __future__ import annotations


def test_register_then_login(client):
    r = client.post(
        "/api/auth/register",
        json={"email": "alice@example.com", "password": "longpassword", "full_name": "Alice"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email"] == "alice@example.com"
    assert body["is_active"] is True
    assert body["is_admin"] is False
    assert "hashed_password" not in body

    r = client.post(
        "/api/auth/login",
        json={"email": "alice@example.com", "password": "longpassword"},
    )
    assert r.status_code == 200
    token = r.json()
    assert token["token_type"] == "bearer"
    assert token["access_token"]
    assert token["expires_in"] > 0


def test_duplicate_registration_rejected(client):
    payload = {"email": "dup@example.com", "password": "longpassword"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    r = client.post("/api/auth/register", json=payload)
    assert r.status_code == 409


def test_login_with_wrong_password(client):
    client.post(
        "/api/auth/register",
        json={"email": "bob@example.com", "password": "longpassword"},
    )
    r = client.post(
        "/api/auth/login",
        json={"email": "bob@example.com", "password": "wrongpassword"},
    )
    assert r.status_code == 401


def test_login_unknown_email(client):
    r = client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "longpassword"},
    )
    assert r.status_code == 401


def test_me_requires_token(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_returns_current_user(client, auth_user):
    email, headers = auth_user
    r = client.get("/api/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == email


def test_protected_route_rejects_missing_token(client):
    r = client.get("/api/datasets")
    assert r.status_code == 401


def test_protected_route_rejects_bad_token(client):
    r = client.get("/api/datasets", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401


def test_register_validates_short_password(client):
    r = client.post(
        "/api/auth/register",
        json={"email": "short@example.com", "password": "abc"},
    )
    assert r.status_code == 422


def test_register_validates_email_format(client):
    r = client.post(
        "/api/auth/register",
        json={"email": "not-an-email", "password": "longpassword"},
    )
    assert r.status_code == 422
