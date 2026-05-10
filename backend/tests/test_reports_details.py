"""
Report detail, workflow, and edge-case tests.

UC-6  — View report details (GET /api/v1/reports/{id})
UC-7  — Check analysis status (GET /api/v1/reports/{id}/analysis-status)
UC-8  — List/filter reports (GET /api/v1/reports)
UC-9  — Change report status (PATCH /api/v1/reports/{id}/status)
UC-10 — Specialist review / overrides (PATCH /api/v1/reports/{id}/specialist-review)
UC-11 — Finalize report (POST /api/v1/reports/{id}/finalize)
UC-12 — Re-analyze with different LLM (POST /api/v1/reports/{id}/reanalyze)
"""

import pytest
from uuid import uuid4
from fastapi import status

REPORT_TEXT = (
    "Пациент Иванов И.И., 45 лет, после приёма Аспирина 500 мг "
    "возникла головная боль через 2 часа. Реакция умеренной тяжести."
)


def _register(client, email, role="reporter"):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Test", "role": role},
    )
    assert resp.status_code == status.HTTP_200_OK, resp.json()
    return resp.json()["access_token"]


def _create_report(client, token, text=REPORT_TEXT):
    resp = client.post(
        "/api/v1/reports",
        json={"raw_text": text},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_202_ACCEPTED, resp.json()
    return resp.json()["id"]


# ── UC-6: View report details ─────────────────────────────────────────────


def test_get_report_own(client):
    """Reporter can fetch their own report and sees full data."""
    token = _register(client, "reporter@example.com")
    report_id = _create_report(client, token)

    resp = client.get(
        f"/api/v1/reports/{report_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["id"] == report_id
    assert data["raw_text"] == REPORT_TEXT
    assert data["status"] == "submitted"
    assert "ai_recommendations" in data


def test_get_report_access_denied_for_other_reporter(client):
    """Reporter B cannot view a report submitted by reporter A."""
    token_a = _register(client, "reporter_a@example.com")
    token_b = _register(client, "reporter_b@example.com")
    report_id = _create_report(client, token_a)

    resp = client.get(
        f"/api/v1/reports/{report_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_get_report_specialist_can_view_any(client):
    """Specialist can view a report submitted by any reporter."""
    reporter_token = _register(client, "reporter@example.com")
    spec_token = _register(client, "specialist@example.com", "specialist")
    report_id = _create_report(client, reporter_token)

    resp = client.get(
        f"/api/v1/reports/{report_id}",
        headers={"Authorization": f"Bearer {spec_token}"},
    )
    assert resp.status_code == status.HTTP_200_OK


def test_get_report_not_found(client):
    """Requesting a non-existent report ID returns 404."""
    token = _register(client, "reporter@example.com")
    resp = client.get(
        f"/api/v1/reports/{uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_get_report_unauthorized(client):
    """Unauthenticated request returns 401."""
    resp = client.get(f"/api/v1/reports/{uuid4()}")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ── UC-7: Analysis status ─────────────────────────────────────────────────


def test_analysis_status_returned_after_create(client):
    """Analysis-status endpoint responds for a created report."""
    token = _register(client, "reporter@example.com")
    report_id = _create_report(client, token)

    resp = client.get(
        f"/api/v1/reports/{report_id}/analysis-status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["analysis_status"] in ("ready", "failed", "pending")


def test_analysis_status_failed_when_no_llm_credentials(client):
    """Without LLM credentials the analysis fails and status is 'failed'."""
    token = _register(client, "reporter@example.com")
    report_id = _create_report(client, token)

    resp = client.get(
        f"/api/v1/reports/{report_id}/analysis-status",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = resp.json()
    assert data["analysis_status"] == "failed"
    assert data["error"] is not None


def test_analysis_status_not_found(client):
    """Analysis-status for non-existent report ID returns 404."""
    token = _register(client, "reporter@example.com")
    resp = client.get(
        f"/api/v1/reports/{uuid4()}/analysis-status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


# ── UC-8: List / filter reports ───────────────────────────────────────────


def test_reporter_sees_only_own_reports(client):
    """Reporter B's list contains zero entries when only reporter A has reports."""
    token_a = _register(client, "reporter_a@example.com")
    token_b = _register(client, "reporter_b@example.com")
    _create_report(client, token_a)

    resp = client.get(
        "/api/v1/reports",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["total"] == 0


def test_specialist_sees_all_reporters_reports(client):
    """Specialist's list includes reports from every reporter."""
    token_a = _register(client, "reporter_a@example.com")
    token_b = _register(client, "reporter_b@example.com")
    spec_token = _register(client, "specialist@example.com", "specialist")
    _create_report(client, token_a)
    _create_report(client, token_b)

    resp = client.get(
        "/api/v1/reports",
        headers={"Authorization": f"Bearer {spec_token}"},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["total"] == 2


def test_list_reports_pagination(client):
    """Page size is honoured and total reflects all records."""
    token = _register(client, "reporter@example.com")
    for _ in range(3):
        _create_report(client, token)

    resp = client.get(
        "/api/v1/reports?page=1&limit=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 3
    assert data["page"] == 1


def test_list_reports_filter_by_status(client):
    """Status filter returns only reports with matching status."""
    token = _register(client, "reporter@example.com")
    _create_report(client, token)

    resp = client.get(
        "/api/v1/reports?status=submitted",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_200_OK
    for item in resp.json()["items"]:
        assert item["status"] == "submitted"


def test_list_reports_date_range_today(client):
    """Date range filter 'today' does not raise an error."""
    token = _register(client, "reporter@example.com")
    _create_report(client, token)

    resp = client.get(
        "/api/v1/reports?date_range=today",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert "items" in resp.json()


def test_list_reports_response_shape(client):
    """Response includes items, total, and page keys."""
    token = _register(client, "reporter@example.com")
    resp = client.get(
        "/api/v1/reports",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data


# ── UC-9: Change report status ────────────────────────────────────────────


def test_change_status_to_clarification(client):
    """Specialist can move a report into 'clarification' status."""
    reporter_token = _register(client, "reporter@example.com")
    spec_token = _register(client, "specialist@example.com", "specialist")
    report_id = _create_report(client, reporter_token)

    resp = client.patch(
        f"/api/v1/reports/{report_id}/status",
        json={"status": "clarification", "comment": "Нужна дополнительная информация"},
        headers={"Authorization": f"Bearer {spec_token}"},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["ok"] is True


def test_change_status_to_analysis(client):
    """Specialist can move a report into 'analysis' status."""
    reporter_token = _register(client, "reporter@example.com")
    spec_token = _register(client, "specialist@example.com", "specialist")
    report_id = _create_report(client, reporter_token)

    resp = client.patch(
        f"/api/v1/reports/{report_id}/status",
        json={"status": "analysis"},
        headers={"Authorization": f"Bearer {spec_token}"},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["ok"] is True


def test_change_status_persists(client):
    """After a status change the report detail reflects the new status."""
    reporter_token = _register(client, "reporter@example.com")
    spec_token = _register(client, "specialist@example.com", "specialist")
    report_id = _create_report(client, reporter_token)

    client.patch(
        f"/api/v1/reports/{report_id}/status",
        json={"status": "analysis"},
        headers={"Authorization": f"Bearer {spec_token}"},
    )

    detail = client.get(
        f"/api/v1/reports/{report_id}",
        headers={"Authorization": f"Bearer {spec_token}"},
    ).json()
    assert detail["status"] == "analysis"


def test_change_status_invalid_value_rejected(client):
    """Attempting to set 'finalized' via the status endpoint returns 400."""
    reporter_token = _register(client, "reporter@example.com")
    spec_token = _register(client, "specialist@example.com", "specialist")
    report_id = _create_report(client, reporter_token)

    resp = client.patch(
        f"/api/v1/reports/{report_id}/status",
        json={"status": "finalized"},
        headers={"Authorization": f"Bearer {spec_token}"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_change_status_reporter_forbidden(client):
    """Reporter cannot change a report's status."""
    token = _register(client, "reporter@example.com")
    report_id = _create_report(client, token)

    resp = client.patch(
        f"/api/v1/reports/{report_id}/status",
        json={"status": "analysis"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_change_status_not_found(client):
    """Changing status of a non-existent report returns 404."""
    spec_token = _register(client, "specialist@example.com", "specialist")
    resp = client.patch(
        f"/api/v1/reports/{uuid4()}/status",
        json={"status": "analysis"},
        headers={"Authorization": f"Bearer {spec_token}"},
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


# ── UC-10: Specialist review / overrides ─────────────────────────────────


def test_specialist_review_saves_overrides(client):
    """Specialist can submit review overrides and receives ok=true."""
    reporter_token = _register(client, "reporter@example.com")
    spec_token = _register(client, "specialist@example.com", "specialist")
    report_id = _create_report(client, reporter_token)

    resp = client.patch(
        f"/api/v1/reports/{report_id}/specialist-review",
        json={
            "ime": {"verdict": "confirmed", "comment": "Клинически значимая реакция"},
            "naranjo": {"verdict": "probable", "comment": "Баллы по шкале Наранжо: 6"},
            "expectedness": {"verdict": "unexpected"},
        },
        headers={"Authorization": f"Bearer {spec_token}"},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["ok"] is True


def test_specialist_review_reporter_forbidden(client):
    """Reporter cannot submit specialist review overrides."""
    token = _register(client, "reporter@example.com")
    report_id = _create_report(client, token)

    resp = client.patch(
        f"/api/v1/reports/{report_id}/specialist-review",
        json={"ime": {"verdict": "confirmed"}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_specialist_review_not_found(client):
    """Specialist review on a non-existent report returns 404."""
    spec_token = _register(client, "specialist@example.com", "specialist")
    resp = client.patch(
        f"/api/v1/reports/{uuid4()}/specialist-review",
        json={"ime": {"verdict": "confirmed"}},
        headers={"Authorization": f"Bearer {spec_token}"},
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


# ── UC-11: Finalize report ────────────────────────────────────────────────


def test_finalize_report_success(client):
    """Specialist can finalize a report — response has ok=true and finalized_at."""
    reporter_token = _register(client, "reporter@example.com")
    spec_token = _register(client, "specialist@example.com", "specialist")
    report_id = _create_report(client, reporter_token)

    resp = client.post(
        f"/api/v1/reports/{report_id}/finalize",
        headers={"Authorization": f"Bearer {spec_token}"},
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["ok"] is True
    assert "finalized_at" in data


def test_finalize_updates_report_status(client):
    """After finalization, the report's status field becomes 'finalized'."""
    reporter_token = _register(client, "reporter@example.com")
    spec_token = _register(client, "specialist@example.com", "specialist")
    report_id = _create_report(client, reporter_token)

    client.post(
        f"/api/v1/reports/{report_id}/finalize",
        headers={"Authorization": f"Bearer {spec_token}"},
    )

    detail = client.get(
        f"/api/v1/reports/{report_id}",
        headers={"Authorization": f"Bearer {spec_token}"},
    ).json()
    assert detail["status"] == "finalized"


def test_finalize_reporter_forbidden(client):
    """Reporter cannot finalize a report."""
    token = _register(client, "reporter@example.com")
    report_id = _create_report(client, token)

    resp = client.post(
        f"/api/v1/reports/{report_id}/finalize",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_finalize_not_found(client):
    """Finalizing a non-existent report returns 404."""
    spec_token = _register(client, "specialist@example.com", "specialist")
    resp = client.post(
        f"/api/v1/reports/{uuid4()}/finalize",
        headers={"Authorization": f"Bearer {spec_token}"},
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


# ── UC-12: Re-analyze with different LLM ─────────────────────────────────


def test_reanalyze_invalid_provider_rejected(client):
    """Requesting reanalysis with an unknown provider returns 400."""
    reporter_token = _register(client, "reporter@example.com")
    spec_token = _register(client, "specialist@example.com", "specialist")
    report_id = _create_report(client, reporter_token)

    resp = client.post(
        f"/api/v1/reports/{report_id}/reanalyze",
        json={"llm_provider": "openai", "llm_model": "gpt-4"},
        headers={"Authorization": f"Bearer {spec_token}"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_reanalyze_not_found(client):
    """Reanalyzing a non-existent report returns 404."""
    spec_token = _register(client, "specialist@example.com", "specialist")
    resp = client.post(
        f"/api/v1/reports/{uuid4()}/reanalyze",
        json={"llm_provider": "yandex", "llm_model": "gpt-4o-mini"},
        headers={"Authorization": f"Bearer {spec_token}"},
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_reanalyze_reporter_forbidden(client):
    """Reporter cannot trigger reanalysis."""
    token = _register(client, "reporter@example.com")
    report_id = _create_report(client, token)

    resp = client.post(
        f"/api/v1/reports/{report_id}/reanalyze",
        json={"llm_provider": "yandex", "llm_model": "gpt-4o-mini"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_reanalyze_missing_fields_rejected(client):
    """Reanalyze request with missing llm_model returns 422."""
    spec_token = _register(client, "specialist@example.com", "specialist")
    resp = client.post(
        f"/api/v1/reports/{uuid4()}/reanalyze",
        json={"llm_provider": "yandex"},
        headers={"Authorization": f"Bearer {spec_token}"},
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ── Additional report creation edge cases ────────────────────────────────


def test_create_report_from_form_success(client):
    """Reporter can create a report via the structured form endpoint."""
    token = _register(client, "reporter@example.com")
    resp = client.post(
        "/api/v1/reports/from-form",
        json={
            "patient": {"name": "Иванов И.И.", "age": "45", "sex": "мужской"},
            "doctor": {"name": "Петров А.А.", "specialty": "терапевт"},
            "medication": {"trade_name": "Аспирин", "dose": "500мг"},
            "adverse_effect": {
                "description": "Головная боль и тошнота через час после приёма"
            },
            "additional_info": {},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_202_ACCEPTED
    data = resp.json()
    assert "id" in data
    assert data["status"] == "submitted"


def test_create_report_from_form_unauthorized(client):
    """Unauthenticated form submission returns 401."""
    resp = client.post(
        "/api/v1/reports/from-form",
        json={
            "patient": {},
            "doctor": {},
            "medication": {},
            "adverse_effect": {"description": "Some reaction"},
            "additional_info": {},
        },
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_report_from_form_missing_adverse_effect(client):
    """Form missing adverse_effect.description (required) returns 422."""
    token = _register(client, "reporter@example.com")
    resp = client.post(
        "/api/v1/reports/from-form",
        json={
            "patient": {},
            "doctor": {},
            "medication": {},
            "adverse_effect": {},
            "additional_info": {},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_extract_from_file_wrong_content_type(client):
    """Uploading a plain-text file to extract-from-file returns 400."""
    token = _register(client, "reporter@example.com")
    resp = client.post(
        "/api/v1/reports/extract-from-file",
        files={"file": ("report.txt", b"Patient data text", "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_extract_from_file_unauthorized(client):
    """Unauthenticated file extraction request returns 401."""
    resp = client.post(
        "/api/v1/reports/extract-from-file",
        files={"file": ("report.pdf", b"", "application/pdf")},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
