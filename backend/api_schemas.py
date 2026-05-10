"""Pydantic schemas for API requests/responses."""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from uuid import UUID

# ── Auth ────────────────────────────────────────────────────────────────────
class UserRole(str, Enum):
    REPORTER = "reporter"
    SPECIALIST = "specialist"


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=256)
    full_name: str
    role: UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., max_length=256)


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool


class AuthResponse(BaseModel):
    access_token: str
    user: UserResponse


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., max_length=256)
    new_password: str = Field(..., min_length=6, max_length=256)


# ── Reports ─────────────────────────────────────────────────────────────────
class ReportStatus(str, Enum):
    SUBMITTED = "submitted"
    CLARIFICATION = "clarification"
    ANALYSIS = "analysis"
    FINALIZED = "finalized"


class SeverityLevel(str, Enum):
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    LIFE_THREATENING = "life-threatening"


class DateRangeFilter(str, Enum):
    TODAY = "today"
    WEEK = "week"
    MONTH = "month"


class CreateReportRequest(BaseModel):
    raw_text: str = Field(..., min_length=10)


class ReanalyzeReportRequest(BaseModel):
    llm_provider: str = Field(..., description="LLM provider: 'yandex' or 'ollama'")
    llm_model: str = Field(..., description="Model name (e.g., 'gpt-4o-mini' for yandex, 'mistral' for ollama)")


class PatientFormData(BaseModel):
    name: Optional[str] = None
    age: Optional[str] = None
    sex: Optional[str] = None
    weight: Optional[str] = None
    diagnosis: Optional[str] = None
    comorbidities: Optional[str] = None


class DoctorFormData(BaseModel):
    name: Optional[str] = None
    specialty: Optional[str] = None
    organization: Optional[str] = None
    email: Optional[str] = None


class MedicationFormData(BaseModel):
    trade_name: Optional[str] = None
    inn: Optional[str] = None
    dose: Optional[str] = None
    route: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    indication: Optional[str] = None
    manufacturer: Optional[str] = None


class AdverseEffectFormData(BaseModel):
    date: Optional[str] = None
    description: str
    severity: Optional[SeverityLevel] = None
    is_serious: Optional[bool] = None
    outcome: Optional[str] = None
    causality_assessment: Optional[str] = None


class FilesFormData(BaseModel):
    additional_info: Optional[str] = None


class CreateReportFromFormRequest(BaseModel):
    patient: PatientFormData
    doctor: DoctorFormData
    medication: MedicationFormData
    adverse_effect: AdverseEffectFormData
    additional_info: FilesFormData


class ExtractedCaseData(BaseModel):
    patient: Optional[Dict[str, Any]] = None
    reporter: Optional[Dict[str, Any]] = None
    adverse_reaction: Optional[Dict[str, Any]] = None
    suspect_drug: Optional[Dict[str, Any]] = None
    concomitant_drugs: List[Dict[str, Any]] = []
    case_narrative: Optional[str] = None
    # Исходный текст файла — используется фронтендом для включения в нарратив отчёта,
    # когда LLM не смог извлечь структурированные данные.
    raw_text: Optional[str] = None


class AIRecommendationsResponse(BaseModel):
    analysis_status: str  # pending | ready | failed
    case_extraction: Optional[ExtractedCaseData] = None
    ime: Optional[Dict[str, Any]] = None
    naranjo: Optional[Dict[str, Any]] = None
    expectedness: Optional[Dict[str, Any]] = None
    completeness: Optional[Dict[str, Any]] = None


class DrugResponse(BaseModel):
    id: Optional[UUID] = None
    name_ru: str
    name_en: Optional[str] = None
    atc_code: Optional[str] = None


class ReportResponse(BaseModel):
    id: UUID
    status: ReportStatus
    reporter_id: UUID
    raw_text: str
    created_at: datetime
    drug: Optional[DrugResponse] = None
    extracted_data: Optional[ExtractedCaseData] = None
    ai_recommendations: AIRecommendationsResponse
    specialist_overrides: Optional[Dict[str, Any]] = None


class ReportShortResponse(BaseModel):
    id: UUID
    status: ReportStatus
    reporter_id: UUID
    drug_name: Optional[str] = None
    adverse_reaction: Optional[str] = None
    reporter_name: Optional[str] = None
    is_clinically_significant: Optional[bool] = None
    analysis_status: str
    created_at: datetime
    severity: Optional[SeverityLevel] = None


class ReportListResponse(BaseModel):
    items: List[ReportShortResponse]
    total: int
    page: int


class AnalysisStatusResponse(BaseModel):
    analysis_status: str  # pending | ready | failed
    error: Optional[str] = None


class ChangeReportStatusRequest(BaseModel):
    status: str  # clarification | analysis
    comment: Optional[str] = None


class SpecialistReviewRequest(BaseModel):
    causality: Optional[Dict[str, str]] = None
    ime: Optional[Dict[str, str]] = None
    naranjo: Optional[Dict[str, str]] = None
    expectedness: Optional[Dict[str, str]] = None
    completeness: Optional[Dict[str, str]] = None


class FinalizeReportResponse(BaseModel):
    ok: bool
    finalized_at: datetime


# ── RAG & Documents ─────────────────────────────────────────────────────────
class DocumentUploadResponse(BaseModel):
    document_id: UUID
    drug_name_ru: str
    status: str  # indexed
    indexed_at: datetime


class DocumentListResponse(BaseModel):
    items: List[Dict[str, Any]]


class DrugSearchResponse(BaseModel):
    items: List[DrugResponse]


class SimpleOkResponse(BaseModel):
    ok: bool
