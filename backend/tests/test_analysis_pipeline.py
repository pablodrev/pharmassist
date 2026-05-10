"""
AI analysis pipeline tests using a mocked orchestrator.

UC-3 — Create report from raw text with full AI analysis
UC-4 — Create report from structured form with full AI analysis
UC-5 — Extract structured data from uploaded file

The orchestrator is mocked to avoid LLM/network dependencies.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import status

from models.schemas import (
    AnalysisReport,
    CaseExtraction,
    PatientInfo,
    ReporterInfo,
    AdverseReactionInfo,
    DrugInfo,
    IMEAssessment,
    NaranjoAssessment,
    NaranjoQuestion,
    NaranjoAnswer,
    CausalityVerdict,
    ExpectednessAssessment,
    ExpectednessVerdict,
)

# ── Fixtures / helpers ────────────────────────────────────────────────────

REPORT_TEXT = (
    "Пациент Иванов И.И., 45 лет. Врач-терапевт Петров А.А. сообщает: "
    "после приёма Аспирина 500 мг per os возникла головная боль через 2 ч. "
    "Реакция умеренной тяжести, прошла самостоятельно через 4 ч."
)

FORM_PAYLOAD = {
    "patient": {
        "name": "Иванов И.И.",
        "age": "45",
        "sex": "мужской",
        "diagnosis": "ОРВИ",
    },
    "doctor": {
        "name": "Петров А.А.",
        "specialty": "терапевт",
        "organization": "ГКБ №1",
    },
    "medication": {
        "trade_name": "Аспирин",
        "inn": "ацетилсалициловая кислота",
        "dose": "500мг",
        "route": "per os",
    },
    "adverse_effect": {
        "description": "Головная боль и тошнота, возникшие через час после приёма",
        "severity": "moderate",
        "is_serious": False,
        "outcome": "выздоровление",
    },
    "additional_info": {"additional_info": "Сопутствующих препаратов нет"},
}


def _register(client, email="reporter@example.com", role="reporter"):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Test", "role": role},
    )
    assert resp.status_code == status.HTTP_200_OK
    return resp.json()["access_token"]


def _make_full_analysis() -> AnalysisReport:
    """Build a complete mock AnalysisReport covering all pipeline stages."""
    return AnalysisReport(
        case_extraction=CaseExtraction(
            patient=PatientInfo(age="45", sex="мужской", diagnosis="ОРВИ"),
            reporter=ReporterInfo(type="врач", name="Петров А.А.", organization="ГКБ №1"),
            adverse_reaction=AdverseReactionInfo(
                description="Головная боль",
                onset_date="2026-05-08",
                severity="умеренная",
                is_serious=False,
                outcome="выздоровление",
            ),
            suspect_drug=DrugInfo(
                name="Аспирин",
                dose="500мг",
                route="per os",
                indication="ОРВИ",
            ),
            case_narrative=(
                "Пациент 45 лет получил головную боль после приёма Аспирина 500 мг"
            ),
        ),
        ime_assessment=IMEAssessment(
            is_clinically_significant=False,
            matches=[],
            reactions_not_in_ime=["головная боль"],
            extracted_reactions=["головная боль"],
        ),
        naranjo_assessment=NaranjoAssessment(
            questions=[
                NaranjoQuestion(
                    question_id=1,
                    question_text="Есть ли ранее опубликованные отчёты об этой реакции?",
                    answer=NaranjoAnswer.YES,
                    score=1,
                    rationale="Головная боль при Аспирине задокументирована в литературе",
                ),
                NaranjoQuestion(
                    question_id=2,
                    question_text="Реакция появилась после введения препарата?",
                    answer=NaranjoAnswer.YES,
                    score=2,
                    rationale="Головная боль возникла через 2 часа после приёма",
                ),
            ],
            total_score=5,
            verdict=CausalityVerdict.PROBABLE,
            confidence="средняя",
            missing_data_for_assessment=["Данные о рехалендже недоступны"],
        ),
        expectedness_assessment=ExpectednessAssessment(
            verdict=ExpectednessVerdict.UNKNOWN,
            rationale="Инструкция по применению не загружена в систему",
            relevant_smp_sections=[],
            rag_used=False,
        ),
        missing_mandatory_fields=[],
        warnings=[],
    )


# ── UC-3: Create report from raw text with full AI analysis ───────────────


def test_create_report_all_recommendations_saved(client):
    """All five recommendation types (case_extraction, ime, naranjo,
    expectedness, completeness) are stored when analysis succeeds."""
    token = _register(client)

    with patch("api.routes.reports._get_orchestrator") as mock_fn:
        mock_fn.return_value.analyze.return_value = _make_full_analysis()
        resp = client.post(
            "/api/v1/reports",
            json={"raw_text": REPORT_TEXT},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == status.HTTP_202_ACCEPTED
    report_id = resp.json()["id"]

    detail = client.get(
        f"/api/v1/reports/{report_id}",
        headers={"Authorization": f"Bearer {token}"},
    ).json()

    ai = detail["ai_recommendations"]
    assert ai["case_extraction"] is not None
    assert ai["ime"] is not None
    assert ai["naranjo"] is not None
    assert ai["expectedness"] is not None
    assert ai["completeness"] is not None


def test_create_report_analysis_status_ready(client):
    """Analysis status is 'ready' immediately after a successful pipeline run."""
    token = _register(client)

    with patch("api.routes.reports._get_orchestrator") as mock_fn:
        mock_fn.return_value.analyze.return_value = _make_full_analysis()
        resp = client.post(
            "/api/v1/reports",
            json={"raw_text": REPORT_TEXT},
            headers={"Authorization": f"Bearer {token}"},
        )

    report_id = resp.json()["id"]
    status_resp = client.get(
        f"/api/v1/reports/{report_id}/analysis-status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert status_resp.status_code == status.HTTP_200_OK
    assert status_resp.json()["analysis_status"] == "ready"


def test_create_report_ime_result_in_detail(client):
    """GET /reports/{id} includes is_clinically_significant from IME assessment."""
    token = _register(client)

    with patch("api.routes.reports._get_orchestrator") as mock_fn:
        mock_fn.return_value.analyze.return_value = _make_full_analysis()
        resp = client.post(
            "/api/v1/reports",
            json={"raw_text": REPORT_TEXT},
            headers={"Authorization": f"Bearer {token}"},
        )

    report_id = resp.json()["id"]
    detail = client.get(
        f"/api/v1/reports/{report_id}",
        headers={"Authorization": f"Bearer {token}"},
    ).json()

    ime = detail["ai_recommendations"]["ime"]
    assert "is_clinically_significant" in ime
    assert ime["is_clinically_significant"] is False


def test_create_report_naranjo_result_in_detail(client):
    """GET /reports/{id} includes Naranjo total_score and verdict."""
    token = _register(client)

    with patch("api.routes.reports._get_orchestrator") as mock_fn:
        mock_fn.return_value.analyze.return_value = _make_full_analysis()
        resp = client.post(
            "/api/v1/reports",
            json={"raw_text": REPORT_TEXT},
            headers={"Authorization": f"Bearer {token}"},
        )

    report_id = resp.json()["id"]
    detail = client.get(
        f"/api/v1/reports/{report_id}",
        headers={"Authorization": f"Bearer {token}"},
    ).json()

    naranjo = detail["ai_recommendations"]["naranjo"]
    assert naranjo["total_score"] == 5
    assert naranjo["verdict"] == CausalityVerdict.PROBABLE.value


def test_create_report_expectedness_in_detail(client):
    """GET /reports/{id} includes expectedness verdict."""
    token = _register(client)

    with patch("api.routes.reports._get_orchestrator") as mock_fn:
        mock_fn.return_value.analyze.return_value = _make_full_analysis()
        resp = client.post(
            "/api/v1/reports",
            json={"raw_text": REPORT_TEXT},
            headers={"Authorization": f"Bearer {token}"},
        )

    report_id = resp.json()["id"]
    detail = client.get(
        f"/api/v1/reports/{report_id}",
        headers={"Authorization": f"Bearer {token}"},
    ).json()

    exp = detail["ai_recommendations"]["expectedness"]
    assert exp["verdict"] == ExpectednessVerdict.UNKNOWN.value


def test_create_report_case_extraction_stored(client):
    """Suspect drug name extracted by the pipeline is stored in extracted_data."""
    token = _register(client)

    with patch("api.routes.reports._get_orchestrator") as mock_fn:
        mock_fn.return_value.analyze.return_value = _make_full_analysis()
        resp = client.post(
            "/api/v1/reports",
            json={"raw_text": REPORT_TEXT},
            headers={"Authorization": f"Bearer {token}"},
        )

    report_id = resp.json()["id"]
    detail = client.get(
        f"/api/v1/reports/{report_id}",
        headers={"Authorization": f"Bearer {token}"},
    ).json()

    case_extraction = detail["ai_recommendations"]["case_extraction"]
    assert case_extraction["suspect_drug"]["name"] == "Аспирин"
    assert case_extraction["adverse_reaction"]["description"] == "Головная боль"


def test_create_report_analysis_failure_saved(client):
    """When orchestrator raises an exception the report is still created
    and analysis-status returns 'failed' with a non-null error message."""
    token = _register(client)

    # No mock → orchestrator init fails (no LLM credentials) → exception saved
    resp = client.post(
        "/api/v1/reports",
        json={"raw_text": REPORT_TEXT},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_202_ACCEPTED
    report_id = resp.json()["id"]

    status_resp = client.get(
        f"/api/v1/reports/{report_id}/analysis-status",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = status_resp.json()
    assert data["analysis_status"] == "failed"
    assert data["error"] is not None


def test_create_report_analysis_orchestrator_called_with_text(client):
    """The orchestrator receives the exact raw_text that was submitted."""
    token = _register(client)
    captured = {}

    def fake_analyze(text):
        captured["text"] = text
        return _make_full_analysis()

    with patch("api.routes.reports._get_orchestrator") as mock_fn:
        mock_fn.return_value.analyze.side_effect = fake_analyze
        client.post(
            "/api/v1/reports",
            json={"raw_text": REPORT_TEXT},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert captured["text"] == REPORT_TEXT


# ── UC-4: Create report from structured form ──────────────────────────────


def test_create_from_form_all_recommendations_saved(client):
    """Form-based report creation stores all recommendation types."""
    token = _register(client)

    with patch("api.routes.reports._get_orchestrator") as mock_fn:
        mock_fn.return_value.analyze.return_value = _make_full_analysis()
        resp = client.post(
            "/api/v1/reports/from-form",
            json=FORM_PAYLOAD,
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == status.HTTP_202_ACCEPTED
    report_id = resp.json()["id"]

    detail = client.get(
        f"/api/v1/reports/{report_id}",
        headers={"Authorization": f"Bearer {token}"},
    ).json()

    ai = detail["ai_recommendations"]
    assert ai["case_extraction"] is not None
    assert ai["ime"] is not None


def test_create_from_form_analysis_status_ready(client):
    """Form report analysis status is 'ready' when orchestrator succeeds."""
    token = _register(client)

    with patch("api.routes.reports._get_orchestrator") as mock_fn:
        mock_fn.return_value.analyze.return_value = _make_full_analysis()
        resp = client.post(
            "/api/v1/reports/from-form",
            json=FORM_PAYLOAD,
            headers={"Authorization": f"Bearer {token}"},
        )

    report_id = resp.json()["id"]
    status_resp = client.get(
        f"/api/v1/reports/{report_id}/analysis-status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert status_resp.json()["analysis_status"] == "ready"


def test_create_from_form_builds_narrative_from_fields(client):
    """The form narrative passed to the orchestrator contains patient and drug info."""
    token = _register(client)
    captured = {}

    def fake_analyze(text):
        captured["text"] = text
        return _make_full_analysis()

    with patch("api.routes.reports._get_orchestrator") as mock_fn:
        mock_fn.return_value.analyze.side_effect = fake_analyze
        client.post(
            "/api/v1/reports/from-form",
            json=FORM_PAYLOAD,
            headers={"Authorization": f"Bearer {token}"},
        )

    narrative = captured.get("text", "")
    assert "Иванов И.И." in narrative
    assert "Аспирин" in narrative


# ── UC-5: Extract structured data from uploaded file ─────────────────────


def test_extract_from_docx_success(client):
    """A valid DOCX file is accepted and extraction is attempted."""
    import io
    from docx import Document

    token = _register(client)

    doc = Document()
    doc.add_paragraph(
        "Пациент Иванов, 45 лет. После Аспирина 500 мг возникла головная боль."
    )
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    docx_bytes = buf.read()

    mock_extraction = _make_full_analysis().case_extraction

    with patch("api.routes.reports._init_llm"), \
         patch("api.routes.reports.CaseExtractionService") as mock_svc_cls:
        mock_svc_cls.return_value.extract.return_value = mock_extraction

        resp = client.post(
            "/api/v1/reports/extract-from-file",
            files={
                "file": (
                    "case.docx",
                    docx_bytes,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["suspect_drug"]["name"] == "Аспирин"
    assert data["adverse_reaction"]["description"] == "Головная боль"


def test_extract_from_file_wrong_type_returns_400(client):
    """Uploading a plain-text file returns 400 before any LLM call."""
    token = _register(client)
    resp = client.post(
        "/api/v1/reports/extract-from-file",
        files={"file": ("report.txt", b"Patient data", "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_extract_from_file_unauthorized(client):
    """Unauthenticated extraction request returns 401."""
    resp = client.post(
        "/api/v1/reports/extract-from-file",
        files={"file": ("report.pdf", b"", "application/pdf")},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
