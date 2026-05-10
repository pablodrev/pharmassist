"""Extended authentication tests — UC-1 (Registration), UC-2 (Login / profile)."""

import pytest
from fastapi import status


# ── UC-1: Registration ────────────────────────────────────────────────────


def test_register_specialist_role(client):
    """Specialist role is accepted during registration."""
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "spec@example.com",
            "password": "securepass",
            "full_name": "Dr. Specialist",
            "role": "specialist",
        },
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["user"]["role"] == "specialist"
    assert data["user"]["email"] == "spec@example.com"


def test_register_short_password_rejected(client):
    """Password shorter than 6 characters is rejected with 422."""
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "password": "abc",
            "full_name": "User",
            "role": "reporter",
        },
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_register_invalid_email_rejected(client):
    """Malformed email address is rejected with 422."""
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "password": "password123",
            "full_name": "User",
            "role": "reporter",
        },
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_register_invalid_role_rejected(client):
    """Unknown role value is rejected with 422."""
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "password": "password123",
            "full_name": "User",
            "role": "admin",
        },
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_register_returns_access_token(client):
    """Registration response includes a non-empty JWT access_token."""
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "reporter@example.com",
            "password": "password123",
            "full_name": "Reporter User",
            "role": "reporter",
        },
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["access_token"]


# ── UC-2: Login / profile ─────────────────────────────────────────────────


def test_login_nonexistent_email_rejected(client):
    """Login with an email that was never registered returns 401."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@example.com", "password": "password123"},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_login_returns_user_data(client):
    """Successful login response includes user info and role."""
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "reporter@example.com",
            "password": "password123",
            "full_name": "John Reporter",
            "role": "reporter",
        },
    )
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "reporter@example.com", "password": "password123"},
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["user"]["role"] == "reporter"
    assert data["user"]["full_name"] == "John Reporter"
    assert data["user"]["is_active"] is True


def test_profile_reflects_correct_role(client):
    """GET /users/me returns the full_name and role stored at registration."""
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "spec@example.com",
            "password": "password123",
            "full_name": "Dr. Jane",
            "role": "specialist",
        },
    )
    token = reg.json()["access_token"]
    resp = client.get(
        "/api/v1/auth/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["role"] == "specialist"
    assert data["full_name"] == "Dr. Jane"


def test_change_password_wrong_old_rejected(client):
    """Supplying the wrong old password returns 401."""
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "reporter@example.com",
            "password": "correctpassword",
            "full_name": "Reporter",
            "role": "reporter",
        },
    )
    token = reg.json()["access_token"]
    resp = client.patch(
        "/api/v1/auth/users/me/password",
        json={"old_password": "wrongpassword", "new_password": "newpass123"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_change_password_new_too_short_rejected(client):
    """New password shorter than 6 characters is rejected with 422."""
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "reporter@example.com",
            "password": "correctpassword",
            "full_name": "Reporter",
            "role": "reporter",
        },
    )
    token = reg.json()["access_token"]
    resp = client.patch(
        "/api/v1/auth/users/me/password",
        json={"old_password": "correctpassword", "new_password": "ab"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_no_token_rejected(client):
    """No Authorization header returns 401."""
    resp = client.get("/api/v1/auth/users/me")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_invalid_token_rejected(client):
    """A tampered or invalid JWT returns 401."""
    resp = client.get(
        "/api/v1/auth/users/me",
        headers={"Authorization": "Bearer invalidtoken.payload.sig"},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
