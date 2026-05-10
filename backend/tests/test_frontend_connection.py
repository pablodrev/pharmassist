"""
Тесты соединения фронтенда и бэкенда.

Проверяют сквозные API-сценарии, которые использует React-приложение:
  - health-check
  - регистрация / вход / получение профиля
  - создание отчёта через форму
  - список отчётов
  - получение статуса анализа
  - смена статуса (только специалист)
  - финализация (только специалист)
  - поиск препаратов
  - ограничение по роли (репортёр → 403 на специалистские эндпоинты)
  - защита эндпоинтов (без токена → 401)
"""

import uuid
import pytest


# ─── Вспомогательные функции ──────────────────────────────────────────────────

def _register(client, suffix: str = "", role: str = "reporter") -> dict:
    """Регистрирует нового пользователя и возвращает AuthResponse."""
    unique = suffix or str(uuid.uuid4())[:8]
    resp = client.post("/api/v1/auth/register", json={
        "email": f"test_{unique}@example.com",
        "password": "secret123",
        "full_name": f"Тест {unique}",
        "role": role,
    })
    assert resp.status_code == 200, resp.text
    return resp.json()


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


FORM_PAYLOAD = {
    "patient": {
        "name": "Иванов Иван Иванович",
        "age": "45",
        "sex": "мужской",
        "weight": "80",
        "diagnosis": "Гипертония",
        "comorbidities": "Сахарный диабет 2 типа",
    },
    "doctor": {
        "name": "Петрова Светлана Анатольевна",
        "specialty": "Кардиология",
        "organization": "ГКБ №1",
        "email": "doctor@hospital.ru",
    },
    "medication": {
        "trade_name": "Аспирин",
        "inn": "Ацетилсалициловая кислота",
        "dose": "100 мг",
        "route": "перорально",
        "start_date": "2024-01-01",
        "end_date": "2024-03-01",
        "indication": "Профилактика тромбозов",
        "manufacturer": "Bayer",
    },
    "adverse_effect": {
        "date": "2024-02-15",
        "description": "Желудочно-кишечное кровотечение, боль в животе, тошнота",
        "severity": "severe",
        "outcome": "выздоровление",
        "causality_assessment": "вероятная",
    },
    "additional_info": {
        "additional_info": "Пациент прекратил приём препарата самостоятельно.",
    },
}


# ─── Тесты ────────────────────────────────────────────────────────────────────

def test_health_check(client):
    """GET /health возвращает {"status": "ok"}."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_register_and_login(client):
    """Регистрация создаёт аккаунт и возвращает JWT-токен."""
    data = _register(client, role="reporter")
    assert "access_token" in data
    assert data["user"]["role"] == "reporter"
    assert data["user"]["email"].endswith("@example.com")


def test_login_returns_token(client):
    """POST /auth/login возвращает JWT для зарегистрированного пользователя."""
    uid = str(uuid.uuid4())[:8]
    email = f"login_{uid}@example.com"
    client.post("/api/v1/auth/register", json={
        "email": email, "password": "qwerty123",
        "full_name": "Тест", "role": "reporter",
    })
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "qwerty123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_get_me(client):
    """GET /auth/users/me возвращает профиль текущего пользователя."""
    data = _register(client, role="specialist")
    token = data["access_token"]
    resp = client.get("/api/v1/auth/users/me", headers=_auth_headers(token))
    assert resp.status_code == 200
    me = resp.json()
    assert me["role"] == "specialist"
    assert "id" in me


def test_auth_required_reports(client):
    """GET /reports без токена → 401."""
    resp = client.get("/api/v1/reports")
    assert resp.status_code == 401


def test_auth_required_drugs(client):
    """GET /drugs без токена → 401."""
    resp = client.get("/api/v1/drugs?search=аспир")
    assert resp.status_code == 401


def test_create_report_from_form(client):
    """POST /reports/from-form создаёт отчёт и возвращает id + status."""
    token = _register(client, role="reporter")["access_token"]
    resp = client.post(
        "/api/v1/reports/from-form",
        json=FORM_PAYLOAD,
        headers=_auth_headers(token),
    )
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert "id" in body
    assert body["status"] == "submitted"


def test_get_reports_list(client):
    """GET /reports возвращает список с полями items, total, page."""
    token = _register(client, role="reporter")["access_token"]
    # Создаём один отчёт, чтобы список не был пустым
    client.post(
        "/api/v1/reports/from-form",
        json=FORM_PAYLOAD,
        headers=_auth_headers(token),
    )
    resp = client.get("/api/v1/reports", headers=_auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert "page" in body
    assert body["total"] >= 1


def test_get_report_by_id(client):
    """GET /reports/{id} возвращает полный отчёт с полями ai_recommendations."""
    token = _register(client, role="reporter")["access_token"]
    create_resp = client.post(
        "/api/v1/reports/from-form",
        json=FORM_PAYLOAD,
        headers=_auth_headers(token),
    )
    report_id = create_resp.json()["id"]

    resp = client.get(f"/api/v1/reports/{report_id}", headers=_auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == report_id
    assert "ai_recommendations" in body
    assert "status" in body


def test_get_analysis_status(client):
    """GET /reports/{id}/analysis-status возвращает analysis_status."""
    token = _register(client, role="reporter")["access_token"]
    report_id = client.post(
        "/api/v1/reports/from-form",
        json=FORM_PAYLOAD,
        headers=_auth_headers(token),
    ).json()["id"]

    resp = client.get(
        f"/api/v1/reports/{report_id}/analysis-status",
        headers=_auth_headers(token),
    )
    assert resp.status_code == 200
    assert "analysis_status" in resp.json()


def test_drugs_search(client, drugs_in_db):
    """GET /drugs?search=... возвращает DrugSearchResponse с полем items."""
    token = _register(client, role="reporter")["access_token"]
    # Ищем по-английски — SQLite LIKE хорошо работает с ASCII
    resp = client.get("/api/v1/drugs?search=Asp", headers=_auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert isinstance(body["items"], list)


def test_drugs_search_min_length(client):
    """GET /drugs?search=а (1 символ) → 422 (min_length=2)."""
    token = _register(client, role="reporter")["access_token"]
    resp = client.get("/api/v1/drugs?search=а", headers=_auth_headers(token))
    assert resp.status_code == 422


def test_role_restriction_status_change(client):
    """Репортёр не может изменить статус отчёта → 403."""
    reporter_token = _register(client, role="reporter")["access_token"]
    report_id = client.post(
        "/api/v1/reports/from-form",
        json=FORM_PAYLOAD,
        headers=_auth_headers(reporter_token),
    ).json()["id"]

    resp = client.patch(
        f"/api/v1/reports/{report_id}/status",
        json={"status": "clarification"},
        headers=_auth_headers(reporter_token),
    )
    assert resp.status_code == 403


def test_role_restriction_finalize(client):
    """Репортёр не может финализировать отчёт → 403."""
    reporter_token = _register(client, role="reporter")["access_token"]
    report_id = client.post(
        "/api/v1/reports/from-form",
        json=FORM_PAYLOAD,
        headers=_auth_headers(reporter_token),
    ).json()["id"]

    resp = client.post(
        f"/api/v1/reports/{report_id}/finalize",
        headers=_auth_headers(reporter_token),
    )
    assert resp.status_code == 403


def test_specialist_can_change_status(client):
    """Специалист может перевести отчёт в статус 'clarification'."""
    # Репортёр создаёт отчёт
    reporter_token = _register(client, role="reporter")["access_token"]
    report_id = client.post(
        "/api/v1/reports/from-form",
        json=FORM_PAYLOAD,
        headers=_auth_headers(reporter_token),
    ).json()["id"]

    # Специалист меняет статус
    spec_token = _register(client, role="specialist")["access_token"]
    resp = client.patch(
        f"/api/v1/reports/{report_id}/status",
        json={"status": "clarification", "comment": "Уточните дату начала приёма"},
        headers=_auth_headers(spec_token),
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    # Проверяем, что статус обновился
    report = client.get(
        f"/api/v1/reports/{report_id}",
        headers=_auth_headers(spec_token),
    ).json()
    assert report["status"] == "clarification"


def test_reporter_sees_only_own_reports(client):
    """Репортёр видит только свои отчёты, не чужие."""
    token_a = _register(client, role="reporter")["access_token"]
    token_b = _register(client, role="reporter")["access_token"]

    # Репортёр A создаёт отчёт
    client.post(
        "/api/v1/reports/from-form",
        json=FORM_PAYLOAD,
        headers=_auth_headers(token_a),
    )

    # Репортёр B не должен видеть отчёт A
    resp_b = client.get("/api/v1/reports", headers=_auth_headers(token_b))
    assert resp_b.status_code == 200
    assert resp_b.json()["total"] == 0


def test_specialist_sees_all_reports(client):
    """Специалист видит все отчёты от всех репортёров."""
    token_a = _register(client, role="reporter")["access_token"]
    token_b = _register(client, role="reporter")["access_token"]
    spec_token = _register(client, role="specialist")["access_token"]

    client.post("/api/v1/reports/from-form", json=FORM_PAYLOAD, headers=_auth_headers(token_a))
    client.post("/api/v1/reports/from-form", json=FORM_PAYLOAD, headers=_auth_headers(token_b))

    resp = client.get("/api/v1/reports", headers=_auth_headers(spec_token))
    assert resp.status_code == 200
    assert resp.json()["total"] >= 2


def test_cors_headers_present(client):
    """Бэкенд возвращает CORS-заголовки для запросов с фронтенда."""
    resp = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert resp.status_code == 200
    # TestClient проходит через middleware, заголовок должен присутствовать
    assert "access-control-allow-origin" in resp.headers
