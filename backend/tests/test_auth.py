"""Tests for authentication routes."""

import pytest
from fastapi import status


def test_register(client):
    """Test user registration."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "reporter@example.com",
            "password": "securepassword123",
            "full_name": "John Reporter",
            "role": "reporter"
        }
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["user"]["email"] == "reporter@example.com"
    assert data["user"]["role"] == "reporter"
    assert "access_token" in data


def test_register_duplicate_email(client):
    """Test registration with duplicate email."""
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "reporter@example.com",
            "password": "securepassword123",
            "full_name": "John Reporter",
            "role": "reporter"
        }
    )
    
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "reporter@example.com",
            "password": "otherpassword123",
            "full_name": "Jane Reporter",
            "role": "specialist"
        }
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_login_success(client):
    """Test successful login."""
    # Register first
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "reporter@example.com",
            "password": "securepassword123",
            "full_name": "John Reporter",
            "role": "reporter"
        }
    )
    
    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "reporter@example.com",
            "password": "securepassword123"
        }
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["user"]["email"] == "reporter@example.com"
    assert "access_token" in data


def test_login_invalid_password(client):
    """Test login with invalid password."""
    # Register first
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "reporter@example.com",
            "password": "securepassword123",
            "full_name": "John Reporter",
            "role": "reporter"
        }
    )
    
    # Login with wrong password
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "reporter@example.com",
            "password": "wrongpassword"
        }
    )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_current_user(client, reporter_token):
    """Test getting current user profile."""
    token, _ = reporter_token
    
    response = client.get(
        "/api/v1/auth/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == status.HTTP_200_OK


def test_get_current_user_no_token(client):
    """Test getting current user without token."""
    response = client.get("/api/v1/auth/users/me")
    
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_change_password(client, reporter_token):
    """Test changing password."""
    token, _ = reporter_token
    
    # Register a user first
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "reporter@example.com",
            "password": "oldpassword123",
            "full_name": "John Reporter",
            "role": "reporter"
        }
    )
    
    # Get the token
    login_resp = client.post(
        "/api/v1/auth/login",
        json={
            "email": "reporter@example.com",
            "password": "oldpassword123"
        }
    )
    new_token = login_resp.json()["access_token"]
    
    # Change password
    response = client.patch(
        "/api/v1/auth/users/me/password",
        json={
            "old_password": "oldpassword123",
            "new_password": "newpassword456"
        },
        headers={"Authorization": f"Bearer {new_token}"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    
    # Try login with new password
    login_resp = client.post(
        "/api/v1/auth/login",
        json={
            "email": "reporter@example.com",
            "password": "newpassword456"
        }
    )
    
    assert login_resp.status_code == status.HTTP_200_OK
