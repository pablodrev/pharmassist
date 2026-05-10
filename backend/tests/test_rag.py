"""
RAG document management tests.

UC-13 — Upload drug instruction manual (POST /api/v1/rag/documents)
UC-14 — List indexed documents (GET  /api/v1/rag/documents)
UC-15 — Delete document         (DELETE /api/v1/rag/documents/{id})
"""

import io
import pytest
from unittest.mock import patch, MagicMock
from fastapi import status


def _register(client, email, role="reporter"):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Test", "role": role},
    )
    assert resp.status_code == status.HTTP_200_OK
    return resp.json()["access_token"]


def _make_docx(text: str = "Инструкция по применению. Показания: болевой синдром.") -> bytes:
    """Create a minimal in-memory DOCX file."""
    from docx import Document

    doc = Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()


DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


# ── UC-14: List documents ─────────────────────────────────────────────────


def test_list_documents_specialist(client):
    """Specialist can list all indexed documents."""
    spec_token = _register(client, "specialist@example.com", "specialist")
    resp = client.get(
        "/api/v1/rag/documents",
        headers={"Authorization": f"Bearer {spec_token}"},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert "items" in resp.json()


def test_list_documents_empty(client):
    """Empty knowledge base returns an empty items list."""
    spec_token = _register(client, "specialist@example.com", "specialist")
    resp = client.get(
        "/api/v1/rag/documents",
        headers={"Authorization": f"Bearer {spec_token}"},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["items"] == []


def test_list_documents_reporter_forbidden(client):
    """Reporter cannot list indexed documents."""
    token = _register(client, "reporter@example.com")
    resp = client.get(
        "/api/v1/rag/documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_list_documents_unauthorized(client):
    """Unauthenticated request returns 401."""
    resp = client.get("/api/v1/rag/documents")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ── UC-13: Upload document ────────────────────────────────────────────────


def test_upload_wrong_content_type_rejected(client):
    """Uploading a plain-text file returns 400 (only PDF/DOCX accepted)."""
    spec_token = _register(client, "specialist@example.com", "specialist")
    resp = client.post(
        "/api/v1/rag/documents",
        data={"drug_name_ru": "Аспирин"},
        files={"file": ("instruction.txt", b"some text", "text/plain")},
        headers={"Authorization": f"Bearer {spec_token}"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_upload_reporter_forbidden(client):
    """Reporter cannot upload a drug instruction document."""
    token = _register(client, "reporter@example.com")
    resp = client.post(
        "/api/v1/rag/documents",
        data={"drug_name_ru": "Аспирин"},
        files={"file": ("instruction.txt", b"content", "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_upload_unauthorized(client):
    """Unauthenticated upload request returns 401."""
    resp = client.post(
        "/api/v1/rag/documents",
        data={"drug_name_ru": "Аспирин"},
        files={"file": ("doc.pdf", b"", "application/pdf")},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_upload_docx_success(client):
    """Specialist can upload a valid DOCX file; response contains document_id and status."""
    spec_token = _register(client, "specialist@example.com", "specialist")
    docx_bytes = _make_docx(
        "Препарат Аспирин. Показания: болевой синдром. "
        "Нежелательные реакции: тошнота, головная боль."
    )

    with patch("api.routes.rag.rag") as mock_rag:
        mock_rag.add_document = MagicMock(return_value=None)
        resp = client.post(
            "/api/v1/rag/documents",
            data={"drug_name_ru": "Аспирин", "drug_name_en": "Aspirin", "atc_code": "B01AC06"},
            files={"file": ("aspirin.docx", docx_bytes, DOCX_MIME)},
            headers={"Authorization": f"Bearer {spec_token}"},
        )

    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["drug_name_ru"] == "Аспирин"
    assert data["status"] == "indexed"
    assert "document_id" in data
    assert "indexed_at" in data


def test_upload_creates_drug_in_db(client):
    """After a successful upload the drug appears in the documents list."""
    spec_token = _register(client, "specialist@example.com", "specialist")
    docx_bytes = _make_docx("Инструкция препарата Ибупрофен.")

    with patch("api.routes.rag.rag") as mock_rag:
        mock_rag.add_document = MagicMock(return_value=None)
        client.post(
            "/api/v1/rag/documents",
            data={"drug_name_ru": "Ибупрофен"},
            files={"file": ("ibuprofen.docx", docx_bytes, DOCX_MIME)},
            headers={"Authorization": f"Bearer {spec_token}"},
        )

    list_resp = client.get(
        "/api/v1/rag/documents",
        headers={"Authorization": f"Bearer {spec_token}"},
    )
    names = [item["drug_name_ru"] for item in list_resp.json()["items"]]
    assert "Ибупрофен" in names


def test_upload_duplicate_drug_updates_metadata(client):
    """Re-uploading a document for the same drug updates optional fields."""
    spec_token = _register(client, "specialist@example.com", "specialist")
    docx_bytes = _make_docx("Инструкция.")

    with patch("api.routes.rag.rag") as mock_rag:
        mock_rag.add_document = MagicMock(return_value=None)
        # First upload — no ATC code
        client.post(
            "/api/v1/rag/documents",
            data={"drug_name_ru": "Аспирин"},
            files={"file": ("a.docx", docx_bytes, DOCX_MIME)},
            headers={"Authorization": f"Bearer {spec_token}"},
        )
        # Second upload — with ATC code
        resp = client.post(
            "/api/v1/rag/documents",
            data={"drug_name_ru": "Аспирин", "atc_code": "B01AC06"},
            files={"file": ("a2.docx", docx_bytes, DOCX_MIME)},
            headers={"Authorization": f"Bearer {spec_token}"},
        )

    assert resp.status_code == status.HTTP_200_OK


# ── UC-15: Delete document ────────────────────────────────────────────────


def test_delete_document_specialist(client):
    """Specialist can delete a document by ID — always returns ok=true."""
    spec_token = _register(client, "specialist@example.com", "specialist")
    resp = client.delete(
        "/api/v1/rag/documents/nonexistent-doc-id",
        headers={"Authorization": f"Bearer {spec_token}"},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["ok"] is True


def test_delete_document_reporter_forbidden(client):
    """Reporter cannot delete RAG documents."""
    token = _register(client, "reporter@example.com")
    resp = client.delete(
        "/api/v1/rag/documents/some-doc-id",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_delete_document_unauthorized(client):
    """Unauthenticated delete request returns 401."""
    resp = client.delete("/api/v1/rag/documents/some-doc-id")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
