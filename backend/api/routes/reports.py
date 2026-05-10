"""Report routes."""

import asyncio
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
from datetime import datetime, timedelta
from uuid import UUID
import os
import tempfile
import logging
from typing import Optional

from db import async_session as _async_session
from db import get_session
from models.schemas_db import User, Report, Drug, AIRecommendation
from auth import get_current_user, require_specialist
from api_schemas import (
    CreateReportRequest, CreateReportFromFormRequest, ReportResponse,
    ReportShortResponse, ReportListResponse, AnalysisStatusResponse,
    ChangeReportStatusRequest, SpecialistReviewRequest, FinalizeReportResponse,
    SimpleOkResponse, SeverityLevel, DateRangeFilter, ReportStatus,
    ExtractedCaseData, AIRecommendationsResponse, DrugResponse,
    ReanalyzeReportRequest
)
from services.orchestrator import AnalysisOrchestrator
from core.llm_client import LLMClient
from core.rag_engine import RAGEngine
from models.schemas import CaseExtraction, PatientInfo, ReporterInfo, AdverseReactionInfo, DrugInfo
import json
import requests

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

# Initialize services with environment variables
def _init_llm(provider: Optional[str] = None, model: Optional[str] = None, validate_connection: bool = False):
    """Initialize LLM client from environment variables or parameters.
    
    Args:
        provider: LLM provider ('yandex' or 'ollama')
        model: Model name
        validate_connection: If True, check connection on init (only for Ollama reanalyze)
    """
    llm_provider = (provider or os.getenv("LLM_PROVIDER", "yandex")).lower()
    llm_model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")
    
    logger.info(f"🔧 Initializing LLM: provider={llm_provider}, model={llm_model}")
    
    if llm_provider == "yandex":
        yandex_folder = os.getenv("YANDEX_CLOUD_FOLDER")
        yandex_key = os.getenv("YANDEX_CLOUD_API_KEY")
        
        if not yandex_folder or not yandex_key:
            error_msg = "YANDEX_CLOUD_FOLDER and YANDEX_CLOUD_API_KEY must be set"
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)
        
        logger.info(f"✅ Yandex Cloud configured: folder={yandex_folder[:10]}...")
        return LLMClient(
            model=llm_model,
            provider="yandex",
            yandex_api_key=yandex_key,
            yandex_folder_id=yandex_folder
        )
    else:
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        logger.info(f"⚙️ Ollama configured: url={ollama_url}")
        
        # Only validate connection if explicitly requested (for reanalyze)
        if validate_connection:
            try:
                response = requests.head(f"{ollama_url}/api/tags", timeout=5)
                if response.status_code != 200:
                    raise RuntimeError(f"Ollama не ответил: {response.status_code}")
                logger.info(f"✅ Ollama connection verified")
            except Exception as e:
                logger.error(f"❌ Ollama connection failed: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Ollama not available at {ollama_url}. Запустите: ollama serve"
                )
        
        return LLMClient(
            model=llm_model,
            provider="ollama",
            base_url=ollama_url
        )

_rag: Optional[RAGEngine] = None
_orchestrator: Optional[AnalysisOrchestrator] = None


def _get_rag() -> RAGEngine:
    global _rag
    if _rag is None:
        _rag = RAGEngine()
    return _rag


def _get_orchestrator() -> AnalysisOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AnalysisOrchestrator(_init_llm(), _get_rag())
    return _orchestrator


async def _extract_text_from_upload(file: UploadFile) -> str:
    """Extract plain text from an uploaded PDF or DOCX file."""
    filename_lower = (file.filename or "").lower()
    _PDF_MIME = "application/pdf"
    _DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    if file.content_type == _PDF_MIME or filename_lower.endswith(".pdf"):
        effective_type = "pdf"
    elif file.content_type == _DOCX_MIME or filename_lower.endswith(".docx"):
        effective_type = "docx"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF and DOCX files are supported",
        )

    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size must be less than 10 MB",
        )

    logger.info(
        "[file-extract] filename=%r content_type=%r effective_type=%r size=%s",
        file.filename, file.content_type, effective_type, file.size,
    )

    content = await file.read()

    with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        if effective_type == "pdf":
            from pypdf import PdfReader
            reader = PdfReader(tmp_path)
            pages_text = [page.extract_text() or "" for page in reader.pages]
            text = "\n".join(pages_text)
            logger.info("[file-extract] PDF: %d pages, %d chars", len(pages_text), len(text))
        else:
            from docx import Document
            doc = Document(tmp_path)
            parts: list[str] = []
            for para in doc.paragraphs:
                if para.text.strip():
                    parts.append(para.text)
            for table in doc.tables:
                for row in table.rows:
                    row_cells = [c.text.strip() for c in row.cells if c.text.strip()]
                    if row_cells:
                        parts.append(" | ".join(row_cells))
            text = "\n".join(parts)
            logger.info("[file-extract] DOCX: %d chars", len(text))
    finally:
        os.unlink(tmp_path)

    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Не удалось извлечь текст из файла. "
                   "Убедитесь, что документ содержит текстовые данные (не только изображения).",
        )

    return text


async def _run_analysis_bg(
    report_id: UUID,
    raw_text: str,
    case: Optional[CaseExtraction] = None,
) -> None:
    """Background task: run analysis pipeline and persist results with own DB session."""
    async with _async_session() as session:
        try:
            orchestrator = _get_orchestrator()
            if case is not None:
                analysis = await asyncio.to_thread(orchestrator.analyze_with_case, raw_text, case)
            else:
                analysis = await asyncio.to_thread(orchestrator.analyze, raw_text)

            stmt = select(Report).where(Report.id == report_id)
            report = (await session.execute(stmt)).scalar_one_or_none()
            if report is None:
                logger.error("Report %s not found in bg task", report_id)
                return

            extracted_dict = analysis.case_extraction.model_dump() if analysis.case_extraction else None

            if analysis.case_extraction and analysis.case_extraction.suspect_drug:
                drug_name = analysis.case_extraction.suspect_drug.name
                drug = (await session.execute(
                    select(Drug).where(Drug.name_ru == drug_name)
                )).scalar_one_or_none()
                if not drug:
                    drug = Drug(name_ru=drug_name)
                    session.add(drug)
                    await session.flush()
                report.drug_id = drug.id

            report.extracted_data = extracted_dict

            recs = []
            if analysis.case_extraction:
                recs.append(AIRecommendation(report_id=report_id, type="case_extraction",
                                             ai_output=extracted_dict or {}))
            if analysis.ime_assessment:
                recs.append(AIRecommendation(report_id=report_id, type="ime",
                                             ai_output=analysis.ime_assessment.model_dump()))
            if analysis.naranjo_assessment:
                recs.append(AIRecommendation(report_id=report_id, type="naranjo",
                                             ai_output=analysis.naranjo_assessment.model_dump()))
            if analysis.expectedness_assessment:
                recs.append(AIRecommendation(report_id=report_id, type="expectedness",
                                             ai_output=analysis.expectedness_assessment.model_dump()))
            recs.append(AIRecommendation(report_id=report_id, type="completeness",
                                         ai_output={
                                             "missing_mandatory_fields": analysis.missing_mandatory_fields,
                                             "warnings": analysis.warnings,
                                         }))
            for rec in recs:
                session.add(rec)
            await session.commit()
            logger.info("✅ BG analysis saved for report %s", report_id)

        except Exception as e:
            logger.error("❌ BG analysis failed for %s: %s", report_id, e, exc_info=True)
            await session.rollback()
            session.add(AIRecommendation(
                report_id=report_id, type="completeness",
                ai_output={"error": str(e), "missing_mandatory_fields": [], "warnings": []},
            ))
            await session.commit()


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_report(
    request: CreateReportRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Create report from raw text."""
    user_id = UUID(current_user["user_id"])
    logger.info("📝 Creating report from text for user %s (%d chars)", user_id, len(request.raw_text))
    report = Report(reporter_id=user_id, raw_text=request.raw_text, status="submitted")
    session.add(report)
    await session.commit()
    await session.refresh(report)
    background_tasks.add_task(_run_analysis_bg, report.id, request.raw_text)
    return {"id": report.id, "status": "pending"}


@router.post("/from-file", status_code=status.HTTP_202_ACCEPTED)
async def create_report_from_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Create report from a PDF or DOCX file."""
    user_id = UUID(current_user["user_id"])
    logger.info("📎 Creating report from file %r for user %s", file.filename, user_id)
    text = await _extract_text_from_upload(file)
    report = Report(reporter_id=user_id, raw_text=text, status="submitted")
    session.add(report)
    await session.commit()
    await session.refresh(report)
    background_tasks.add_task(_run_analysis_bg, report.id, text)
    return {"id": report.id, "status": "pending"}


@router.post("/from-form", status_code=status.HTTP_202_ACCEPTED)
async def create_report_from_form(
    request: CreateReportFromFormRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Create report from structured form. Skips LLM case extraction."""
    user_id = UUID(current_user["user_id"])

    # Build narrative — used as context for IME/Naranjo/Expectedness LLM calls
    narrative = (
        f"Пациент: {request.patient.name or 'Не указан'}, "
        f"возраст {request.patient.age or 'не указан'}, "
        f"пол {request.patient.sex or 'не указан'}, "
        f"вес {request.patient.weight or 'не указан'}. "
        f"Диагноз: {request.patient.diagnosis or 'не указан'}. "
        f"Сопутствующие заболевания: {request.patient.comorbidities or 'нет'}.\n"
        f"Врач: {request.doctor.name or 'Не указан'}, "
        f"специальность {request.doctor.specialty or 'не указана'}, "
        f"организация {request.doctor.organization or 'не указана'}.\n"
        f"Препарат: {request.medication.trade_name or request.medication.inn or 'не указан'} "
        f"(МНН: {request.medication.inn or 'не указан'}), "
        f"доза {request.medication.dose or 'не указана'}, "
        f"путь введения {request.medication.route or 'не указан'}, "
        f"начало {request.medication.start_date or 'не указано'}, "
        f"окончание {request.medication.end_date or 'не указано'}, "
        f"показание: {request.medication.indication or 'не указано'}.\n"
        f"Нежелательная реакция: {request.adverse_effect.description}. "
        f"Дата: {request.adverse_effect.date or 'не указана'}. "
        f"Тяжесть: {request.adverse_effect.severity or 'не указана'}. "
        f"Серьёзная: {request.adverse_effect.is_serious or 'не указано'}. "
        f"Исход: {request.adverse_effect.outcome or 'не указан'}.\n"
        f"Дополнительная информация: {request.additional_info.additional_info or 'нет'}."
    )

    # Map form fields directly to CaseExtraction — no LLM call needed
    drug_name = request.medication.trade_name or request.medication.inn
    case = CaseExtraction(
        patient=PatientInfo(
            age=request.patient.age,
            sex=request.patient.sex,
            weight=request.patient.weight,
            diagnosis=request.patient.diagnosis,
            comorbidities=request.patient.comorbidities,
        ) if any([request.patient.age, request.patient.sex, request.patient.diagnosis]) else None,
        reporter=ReporterInfo(
            type="врач",
            name=request.doctor.name,
            organization=request.doctor.organization,
        ) if any([request.doctor.name, request.doctor.organization]) else None,
        adverse_reaction=AdverseReactionInfo(
            description=request.adverse_effect.description,
            onset_date=request.adverse_effect.date,
            outcome=request.adverse_effect.outcome,
            severity=str(request.adverse_effect.severity) if request.adverse_effect.severity else None,
            is_serious=request.adverse_effect.is_serious,
        ),
        suspect_drug=DrugInfo(
            name=drug_name,
            dose=request.medication.dose,
            route=request.medication.route,
            start_date=request.medication.start_date,
            end_date=request.medication.end_date,
            indication=request.medication.indication,
            is_suspect=True,
        ) if drug_name else None,
    )

    report = Report(reporter_id=user_id, raw_text=narrative, status="submitted")
    session.add(report)
    await session.commit()
    await session.refresh(report)
    logger.info("📋 Report created from form: %s", report.id)
    background_tasks.add_task(_run_analysis_bg, report.id, narrative, case)
    return {"id": report.id, "status": "pending"}


@router.get("", response_model=ReportListResponse)
async def list_reports(
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    severity: Optional[SeverityLevel] = Query(None),
    date_range: Optional[DateRangeFilter] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """List reports with filters."""
    user_id = UUID(current_user["user_id"])
    role = current_user["role"]
    
    # Build query
    query = select(Report)
    
    # Filter by user role
    if role == "reporter":
        query = query.where(Report.reporter_id == user_id)
    
    # Filter by status
    if status_filter:
        query = query.where(Report.status == status_filter)
    
    # Filter by date range
    if date_range:
        now = datetime.utcnow()
        if date_range == DateRangeFilter.TODAY:
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_range == DateRangeFilter.WEEK:
            start_date = now - timedelta(days=7)
        elif date_range == DateRangeFilter.MONTH:
            start_date = now - timedelta(days=30)
        else:
            start_date = None
        if start_date:
            query = query.where(Report.created_at >= start_date)
    
    # Get total count
    count_stmt = select(func.count(Report.id)).select_from(Report).where(
        query.whereclause if query.whereclause is not None else True
    )
    count_result = await session.execute(count_stmt)
    total = count_result.scalar() or 0
    
    # Paginate
    query = query.order_by(desc(Report.created_at))
    query = query.offset((page - 1) * limit).limit(limit)
    
    result = await session.execute(query)
    reports = result.scalars().all()
    
    # Build responses
    items = []
    for report in reports:
        # Get AI recommendations
        stmt = select(AIRecommendation).where(AIRecommendation.report_id == report.id)
        recs_result = await session.execute(stmt)
        recs = recs_result.scalars().all()
        
        ime_rec = next((r for r in recs if r.type == "ime"), None)
        
        # Extract drug name
        drug_name = None
        if report.drug_id:
            stmt = select(Drug).where(Drug.id == report.drug_id)
            drug_result = await session.execute(stmt)
            drug = drug_result.scalar_one_or_none()
            if drug:
                drug_name = drug.name_ru
        
        # Extract adverse reaction and reporter
        adverse_reaction = None
        reporter_name = None
        if report.extracted_data:
            data = report.extracted_data
            if isinstance(data, str):
                data = json.loads(data)
            if data.get("adverse_reaction"):
                adverse_reaction = data["adverse_reaction"].get("description")
            if data.get("reporter"):
                reporter_name = data["reporter"].get("name")
        
        item = ReportShortResponse(
            id=report.id,
            status=report.status,
            reporter_id=report.reporter_id,
            drug_name=drug_name,
            adverse_reaction=adverse_reaction,
            reporter_name=reporter_name,
            is_clinically_significant=ime_rec.ai_output.get("is_clinically_significant") if ime_rec else None,
            analysis_status="ready" if ime_rec else "pending",
            created_at=report.created_at,
            severity=None  # TODO: extract from data
        )
        items.append(item)
    
    return ReportListResponse(items=items, total=total, page=page)


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: UUID,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get report details."""
    user_id = UUID(current_user["user_id"])
    role = current_user["role"]
    
    stmt = select(Report).where(Report.id == report_id)
    result = await session.execute(stmt)
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    
    # Check access
    if role == "reporter" and report.reporter_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    # Get drug
    drug = None
    if report.drug_id:
        stmt = select(Drug).where(Drug.id == report.drug_id)
        result = await session.execute(stmt)
        drug_obj = result.scalar_one_or_none()
        if drug_obj:
            drug = DrugResponse(
                id=drug_obj.id,
                name_ru=drug_obj.name_ru,
                name_en=drug_obj.name_en,
                atc_code=drug_obj.atc_code
            )
    
    # Get AI recommendations
    stmt = select(AIRecommendation).where(AIRecommendation.report_id == report.id)
    result = await session.execute(stmt)
    recs = result.scalars().all()
    
    ai_recs = {}
    for rec in recs:
        ai_recs[rec.type] = rec.ai_output
    
    analysis_status = "ready" if ai_recs else "pending"
    
    # Build extracted data
    extracted_data = None
    if report.extracted_data:
        data = report.extracted_data
        if isinstance(data, str):
            data = json.loads(data)
        extracted_data = ExtractedCaseData(**data)
    
    ai_recommendations = AIRecommendationsResponse(
        analysis_status=analysis_status,
        case_extraction=extracted_data,
        ime=ai_recs.get("ime"),
        naranjo=ai_recs.get("naranjo"),
        expectedness=ai_recs.get("expectedness"),
        completeness=ai_recs.get("completeness")
    )
    
    return ReportResponse(
        id=report.id,
        status=report.status,
        reporter_id=report.reporter_id,
        raw_text=report.raw_text,
        created_at=report.created_at,
        drug=drug,
        extracted_data=extracted_data,
        ai_recommendations=ai_recommendations
    )


@router.get("/{report_id}/analysis-status", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    report_id: UUID,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get AI analysis status."""
    stmt = select(Report).where(Report.id == report_id)
    result = await session.execute(stmt)
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    
    # Get completeness recommendation
    stmt = select(AIRecommendation).where(
        and_(AIRecommendation.report_id == report.id, AIRecommendation.type == "completeness")
    )
    result = await session.execute(stmt)
    rec = result.scalar_one_or_none()
    
    if not rec:
        return AnalysisStatusResponse(analysis_status="pending")
    
    error = rec.ai_output.get("error") if rec.ai_output else None
    status_val = "failed" if error else "ready"
    
    return AnalysisStatusResponse(
        analysis_status=status_val,
        error=error
    )


@router.patch("/{report_id}/status", response_model=SimpleOkResponse)
async def change_report_status(
    report_id: UUID,
    request: ChangeReportStatusRequest,
    current_user: dict = Depends(require_specialist),
    session: AsyncSession = Depends(get_session)
):
    """Change report status. Only specialists."""
    stmt = select(Report).where(Report.id == report_id)
    result = await session.execute(stmt)
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    
    # Validate transition
    if request.status not in ["clarification", "analysis"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")
    
    report.status = request.status
    session.add(report)
    await session.commit()
    
    return SimpleOkResponse(ok=True)


@router.patch("/{report_id}/specialist-review", response_model=SimpleOkResponse)
async def specialist_review(
    report_id: UUID,
    request: SpecialistReviewRequest,
    current_user: dict = Depends(require_specialist),
    session: AsyncSession = Depends(get_session)
):
    """Save specialist overrides."""
    stmt = select(Report).where(Report.id == report_id)
    result = await session.execute(stmt)
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    
    # Get AI recommendations
    stmt = select(AIRecommendation).where(AIRecommendation.report_id == report.id)
    result = await session.execute(stmt)
    recs = result.scalars().all()
    
    # Update verdicts
    rec_map = {r.type: r for r in recs}
    
    if request.causality and "causality" in rec_map:
        rec_map["causality"].specialist_verdict = request.causality.get("verdict")
        rec_map["causality"].specialist_comment = request.causality.get("comment")
    
    if request.ime and "ime" in rec_map:
        rec_map["ime"].specialist_verdict = request.ime.get("verdict")
        rec_map["ime"].specialist_comment = request.ime.get("comment")
    
    if request.naranjo and "naranjo" in rec_map:
        rec_map["naranjo"].specialist_verdict = request.naranjo.get("verdict")
        rec_map["naranjo"].specialist_comment = request.naranjo.get("comment")
    
    if request.expectedness and "expectedness" in rec_map:
        rec_map["expectedness"].specialist_verdict = request.expectedness.get("verdict")
        rec_map["expectedness"].specialist_comment = request.expectedness.get("comment")
    
    if request.completeness and "completeness" in rec_map:
        rec_map["completeness"].specialist_verdict = request.completeness.get("verdict")
        rec_map["completeness"].specialist_comment = request.completeness.get("comment")
    
    for rec in recs:
        session.add(rec)
    
    await session.commit()
    
    return SimpleOkResponse(ok=True)


@router.post("/{report_id}/finalize", response_model=FinalizeReportResponse)
async def finalize_report(
    report_id: UUID,
    current_user: dict = Depends(require_specialist),
    session: AsyncSession = Depends(get_session)
):
    """Finalize report. Only specialists."""
    stmt = select(Report).where(Report.id == report_id)
    result = await session.execute(stmt)
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    
    report.status = "finalized"
    session.add(report)
    await session.commit()
    
    return FinalizeReportResponse(ok=True, finalized_at=datetime.utcnow())


@router.post("/{report_id}/reanalyze", response_model=SimpleOkResponse)
async def reanalyze_report(
    report_id: UUID,
    request: ReanalyzeReportRequest,
    current_user: dict = Depends(require_specialist),
    session: AsyncSession = Depends(get_session)
):
    """
    Re-analyze report with a different LLM provider/model.
    Only specialists can use this endpoint.
    This overwrites previous analysis results (Variant A - simple).
    """
    logger.info(f"🔄 Reanalyze request for report {report_id}")
    logger.info(f"   Requested: provider={request.llm_provider}, model={request.llm_model}")
    
    # Validate provider
    if request.llm_provider.lower() not in ["yandex", "ollama"]:
        logger.warning(f"❌ Invalid provider: {request.llm_provider}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider must be 'yandex' or 'ollama'"
        )
    
    # Get report
    stmt = select(Report).where(Report.id == report_id)
    result = await session.execute(stmt)
    report = result.scalar_one_or_none()
    
    if not report:
        logger.warning(f"❌ Report {report_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    logger.info(f"✅ Found report {report_id}, raw_text length: {len(report.raw_text)} chars")
    
    try:
        # Initialize new LLM client with requested parameters
        logger.info(f"🔧 Creating new LLM client...")
        
        # For Ollama, validate connection first
        if request.llm_provider.lower() == "ollama":
            logger.info(f"🔍 Checking Ollama availability...")
            new_llm = _init_llm(
                provider=request.llm_provider.lower(),
                model=request.llm_model,
                validate_connection=True
            )
        else:
            new_llm = _init_llm(
                provider=request.llm_provider.lower(),
                model=request.llm_model,
                validate_connection=False
            )
        
        logger.info(f"✅ New LLM client initialized")
        
        # Create new orchestrator with new LLM
        new_orchestrator = AnalysisOrchestrator(new_llm, _get_rag())
        logger.info(f"🔄 Starting re-analysis with {request.llm_provider}/{request.llm_model}...")
        
        # Run analysis
        analysis = new_orchestrator.analyze(report.raw_text)
        logger.info(f"✅ Re-analysis completed successfully")
        
        # Delete existing recommendations (Variant A - overwrite)
        logger.info(f"🗑️ Deleting previous recommendations...")
        stmt = select(AIRecommendation).where(AIRecommendation.report_id == report.id)
        result = await session.execute(stmt)
        existing_recs = result.scalars().all()
        for rec in existing_recs:
            await session.delete(rec)
        logger.info(f"✅ Deleted {len(existing_recs)} previous recommendations")
        
        # Convert to dict
        extracted_dict = analysis.case_extraction.model_dump() if analysis.case_extraction else None
        
        # Save extracted data
        report.extracted_data = extracted_dict
        logger.info(f"📊 Updated extracted data")
        
        # Save new AI recommendations
        if analysis.case_extraction:
            logger.info(f"💾 Saving case_extraction from {request.llm_provider}")
            rec = AIRecommendation(
                report_id=report.id,
                type="case_extraction",
                ai_output=extracted_dict or {}
            )
            session.add(rec)
        
        if analysis.ime_assessment:
            logger.info(f"💾 Saving ime from {request.llm_provider}")
            rec = AIRecommendation(
                report_id=report.id,
                type="ime",
                ai_output=analysis.ime_assessment.model_dump()
            )
            session.add(rec)
        
        if analysis.naranjo_assessment:
            logger.info(f"💾 Saving naranjo from {request.llm_provider}")
            rec = AIRecommendation(
                report_id=report.id,
                type="naranjo",
                ai_output=analysis.naranjo_assessment.model_dump()
            )
            session.add(rec)
        
        if analysis.expectedness_assessment:
            logger.info(f"💾 Saving expectedness from {request.llm_provider}")
            rec = AIRecommendation(
                report_id=report.id,
                type="expectedness",
                ai_output=analysis.expectedness_assessment.model_dump()
            )
            session.add(rec)
        
        # Completeness
        completeness = {
            "missing_mandatory_fields": analysis.missing_mandatory_fields,
            "warnings": analysis.warnings,
            "reanalyzed_with": f"{request.llm_provider}/{request.llm_model}"
        }
        logger.info(f"💾 Saving completeness from {request.llm_provider}")
        rec = AIRecommendation(
            report_id=report.id,
            type="completeness",
            ai_output=completeness
        )
        session.add(rec)
        
        await session.commit()
        logger.info(f"✅ All new recommendations saved for report {report_id}")
        logger.info(f"✅ Re-analysis completed successfully with {request.llm_provider}/{request.llm_model}")
        
        return SimpleOkResponse(ok=True)
        
    except Exception as e:
        logger.error(f"❌ Error during re-analysis of {report_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Re-analysis failed: {str(e)}"
        )
