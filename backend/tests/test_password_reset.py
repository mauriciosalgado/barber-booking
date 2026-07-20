"""Password-reset flow tests."""

from fastapi.testclient import TestClient

from app.security import create_reset_token
from tests.conftest import auth, register


def test_forgot_password_always_returns_200(client: TestClient):
    """Never leak whether an email exists."""
    resp = client.post("/auth/forgot-password", json={"email": "nobody@test.com"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "sent"


def test_reset_password_with_valid_token(client: TestClient):
    """A valid reset token lets the user set a new password."""
    register(client, "joe@test.com", password="oldpass")
    user_id = auth(client, "joe@test.com", "oldpass")
    me = client.get("/auth/me", headers=user_id).json()

    token = create_reset_token(me["id"])
    resp = client.post(
        "/auth/reset-password", json={"token": token, "new_password": "newpass"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "password_updated"

    # Old password no longer works
    old_login = client.post(
        "/auth/token", data={"username": "joe@test.com", "password": "oldpass"}
    )
    assert old_login.status_code == 401

    # New password works
    new_login = client.post(
        "/auth/token", data={"username": "joe@test.com", "password": "newpass"}
    )
    assert new_login.status_code == 200
    assert "access_token" in new_login.json()


def test_reset_password_rejects_bad_token(client: TestClient):
    resp = client.post(
        "/auth/reset-password", json={"token": "garbage", "new_password": "x"}
    )
    assert resp.status_code == 400
