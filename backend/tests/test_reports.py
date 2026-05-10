"""Tests for report routes."""

import pytest
from fastapi import status


@pytest.mark.asyncio
async def test_create_report(client, reporter_token):
    """Test creating a report."""
    token, _ = reporter_token
    
    # First, register a user
    reg_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "reporter@example.com",
            "password": "securepassword123",
            "full_name": "John Reporter",
            "role": "reporter"
        }
    )
    reg_token = reg_response.json()["access_token"]
    
    # Create report
    response = client.post(
        "/api/v1/reports",
        json={
            "raw_text": "Patient John Doe, age 45, presented with severe headache after taking Aspirin. Reaction started 2 hours after intake."
        },
        headers={"Authorization": f"Bearer {reg_token}"}
    )
    
    assert response.status_code == status.HTTP_202_ACCEPTED
    data = response.json()
    assert "id" in data
    assert data["status"] == "submitted"


@pytest.mark.asyncio
async def test_create_report_unauthorized(client):
    """Test creating report without auth."""
    response = client.post(
        "/api/v1/reports",
        json={
            "raw_text": "Some adverse event text here"
        }
    )
    
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_create_report_invalid_text(client, reporter_token):
    """Test creating report with invalid text."""
    reg_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "reporter@example.com",
            "password": "securepassword123",
            "full_name": "John Reporter",
            "role": "reporter"
        }
    )
    reg_token = reg_response.json()["access_token"]
    
    # Too short text
    response = client.post(
        "/api/v1/reports",
        json={"raw_text": "short"},
        headers={"Authorization": f"Bearer {reg_token}"}
    )
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_list_reports_reporter(client):
    """Test listing reports as reporter."""
    # Register reporter
    reg_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "reporter@example.com",
            "password": "securepassword123",
            "full_name": "John Reporter",
            "role": "reporter"
        }
    )
    token = reg_response.json()["access_token"]
    
    # Create report
    client.post(
        "/api/v1/reports",
        json={
            "raw_text": "Patient John Doe, age 45, presented with severe headache after taking Aspirin. Reaction started 2 hours after intake."
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # List reports
    response = client.get(
        "/api/v1/reports",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data


@pytest.mark.asyncio
async def test_list_reports_filter_by_status(client):
    """Test listing reports with status filter."""
    # Register reporter
    reg_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "reporter@example.com",
            "password": "securepassword123",
            "full_name": "John Reporter",
            "role": "reporter"
        }
    )
    token = reg_response.json()["access_token"]
    
    # Create report
    client.post(
        "/api/v1/reports",
        json={
            "raw_text": "Patient John Doe, age 45, presented with severe headache after taking Aspirin. Reaction started 2 hours after intake."
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # List with status filter
    response = client.get(
        "/api/v1/reports?status=submitted",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_change_report_status_specialist_only(client):
    """Test that only specialists can change report status."""
    # Register reporter
    reg_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "reporter@example.com",
            "password": "securepassword123",
            "full_name": "John Reporter",
            "role": "reporter"
        }
    )
    reporter_token = reg_response.json()["access_token"]
    
    # Create report
    report_response = client.post(
        "/api/v1/reports",
        json={
            "raw_text": "Patient John Doe, age 45, presented with severe headache after taking Aspirin. Reaction started 2 hours after intake."
        },
        headers={"Authorization": f"Bearer {reporter_token}"}
    )
    report_id = report_response.json()["id"]
    
    # Try to change status as reporter (should fail)
    response = client.patch(
        f"/api/v1/reports/{report_id}/status",
        json={
            "status": "analysis",
            "comment": "test"
        },
        headers={"Authorization": f"Bearer {reporter_token}"}
    )
    
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_change_report_status_specialist(client):
    """Test changing report status as specialist."""
    # Register reporter and specialist
    reporter_reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "reporter@example.com",
            "password": "securepassword123",
            "full_name": "John Reporter",
            "role": "reporter"
        }
    )
    reporter_token = reporter_reg.json()["access_token"]
    
    spec_reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "specialist@example.com",
            "password": "securepassword123",
            "full_name": "Jane Specialist",
            "role": "specialist"
        }
    )
    specialist_token = spec_reg.json()["access_token"]
    
    # Create report
    report_response = client.post(
        "/api/v1/reports",
        json={
            "raw_text": "Patient John Doe, age 45, presented with severe headache after taking Aspirin. Reaction started 2 hours after intake."
        },
        headers={"Authorization": f"Bearer {reporter_token}"}
    )
    report_id = report_response.json()["id"]
    
    # Change status as specialist
    response = client.patch(
        f"/api/v1/reports/{report_id}/status",
        json={
            "status": "analysis"
        },
        headers={"Authorization": f"Bearer {specialist_token}"}
    )
    
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_finalize_report_specialist_only(client):
    """Test that only specialists can finalize reports."""
    # Register reporter and specialist
    reporter_reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "reporter@example.com",
            "password": "securepassword123",
            "full_name": "John Reporter",
            "role": "reporter"
        }
    )
    reporter_token = reporter_reg.json()["access_token"]
    
    # Create report
    report_response = client.post(
        "/api/v1/reports",
        json={
            "raw_text": "Patient John Doe, age 45, presented with severe headache after taking Aspirin. Reaction started 2 hours after intake."
        },
        headers={"Authorization": f"Bearer {reporter_token}"}
    )
    report_id = report_response.json()["id"]
    
    # Try to finalize as reporter (should fail)
    response = client.post(
        f"/api/v1/reports/{report_id}/finalize",
        headers={"Authorization": f"Bearer {reporter_token}"}
    )
    
    assert response.status_code == status.HTTP_403_FORBIDDEN
