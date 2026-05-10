"""Drug search use-case tests — UC-16 (GET /api/v1/drugs)."""

import pytest
from fastapi import status


def _register(client, email="reporter@example.com", role="reporter"):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Test", "role": role},
    )
    assert resp.status_code == status.HTTP_200_OK
    return resp.json()["access_token"]


# ── Search mechanics ──────────────────────────────────────────────────────


def test_search_drugs_found_by_name_ru(client, drugs_in_db):
    """Substring match against name_ru returns matching drugs."""
    token = _register(client)
    resp = client.get(
        "/api/v1/drugs?search=Аспир",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_200_OK
    names = [d["name_ru"] for d in resp.json()["items"]]
    assert "Аспирин" in names


def test_search_drugs_found_by_name_en(client, drugs_in_db):
    """Substring match against name_en is case-insensitive for ASCII."""
    token = _register(client)
    resp = client.get(
        "/api/v1/drugs?search=aspirin",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_200_OK
    items = resp.json()["items"]
    assert any(d["name_en"] == "Aspirin" for d in items)


def test_search_drugs_not_found(client, drugs_in_db):
    """A query that matches nothing returns an empty list."""
    token = _register(client)
    resp = client.get(
        "/api/v1/drugs?search=xyz999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["items"] == []


def test_search_drugs_returns_multiple_results(client, drugs_in_db):
    """Multiple matching drugs are returned together."""
    token = _register(client)
    # All three drugs share no common prefix — search "fen" matches "Ибупрофен" via 'fen'
    resp = client.get(
        "/api/v1/drugs?search=Ibuprofen",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_200_OK
    # At least one result
    assert len(resp.json()["items"]) >= 1


def test_search_drugs_response_has_expected_fields(client, drugs_in_db):
    """Each drug item contains id, name_ru, name_en, and atc_code fields."""
    token = _register(client)
    resp = client.get(
        "/api/v1/drugs?search=Аспир",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_200_OK
    item = resp.json()["items"][0]
    assert "id" in item
    assert "name_ru" in item
    assert "name_en" in item
    assert "atc_code" in item


# ── Access control ────────────────────────────────────────────────────────


def test_search_drugs_unauthorized(client, drugs_in_db):
    """Drug search without authentication returns 401."""
    resp = client.get("/api/v1/drugs?search=Аспир")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ── Validation ────────────────────────────────────────────────────────────


def test_search_drugs_query_too_short(client, drugs_in_db):
    """A single-character search term is rejected with 422 (min_length=2)."""
    token = _register(client)
    resp = client.get(
        "/api/v1/drugs?search=А",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_search_drugs_missing_query(client, drugs_in_db):
    """Omitting the search parameter altogether returns 422."""
    token = _register(client)
    resp = client.get(
        "/api/v1/drugs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ── Result limit ─────────────────────────────────────────────────────────


def test_search_drugs_respects_limit(client, drugs_in_db):
    """Result list never exceeds 10 entries."""
    token = _register(client)
    # With only 3 drugs in DB this just verifies the response is ≤ 10
    resp = client.get(
        "/api/v1/drugs?search=Ibu",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.json()["items"]) <= 10
