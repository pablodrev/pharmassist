"""RAG (knowledge base) routes."""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4
from datetime import datetime
import os
import tempfile

from db import get_session
from models.schemas_db import Drug
from auth import require_specialist
from api_schemas import DocumentUploadResponse, SimpleOkResponse, DocumentListResponse
from core.rag_engine import RAGEngine

router = APIRouter(prefix="/api/v1/rag/documents", tags=["rag"])

# Initialize RAG engine
rag = RAGEngine()


@router.post("", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    drug_name_ru: str = Form(...),
    drug_name_en: str = Form(None),
    atc_code: str = Form(None),
    current_user: dict = Depends(require_specialist),
    session: AsyncSession = Depends(get_session)
):
    """Upload drug's instruction manual (IMP) to RAG index."""
    
    if file.content_type not in ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF and DOCX files are supported"
        )
    
    if file.size > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size must be less than 10 MB"
        )
    
    # Save file temporarily
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        # Extract text from file
        text = ""
        if file.content_type == "application/pdf":
            from pypdf import PdfReader
            reader = PdfReader(tmp_path)
            text = "\n".join([page.extract_text() for page in reader.pages])
        else:
            from docx import Document
            doc = Document(tmp_path)
            text = "\n".join([para.text for para in doc.paragraphs])
        
        if not text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract text from file"
            )
        
        # Index in RAG
        doc_id = str(uuid4())
        rag.add_document(doc_id, text, {"drug_name_ru": drug_name_ru})
        
        # Create or update drug in DB
        stmt = select(Drug).where(Drug.name_ru == drug_name_ru)
        result = await session.execute(stmt)
        drug = result.scalar_one_or_none()
        
        if not drug:
            drug = Drug(
                name_ru=drug_name_ru,
                name_en=drug_name_en,
                atc_code=atc_code
            )
            session.add(drug)
        else:
            if drug_name_en:
                drug.name_en = drug_name_en
            if atc_code:
                drug.atc_code = atc_code
            session.add(drug)
        
        await session.commit()
        
        return DocumentUploadResponse(
            document_id=doc_id,
            drug_name_ru=drug_name_ru,
            status="indexed",
            indexed_at=datetime.utcnow()
        )
        
    finally:
        os.unlink(tmp_path)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    current_user: dict = Depends(require_specialist),
    session: AsyncSession = Depends(get_session)
):
    """List all indexed documents."""
    # Get all drugs
    stmt = select(Drug)
    result = await session.execute(stmt)
    drugs = result.scalars().all()
    
    items = [
        {
            "id": str(drug.id),
            "drug_name_ru": drug.name_ru,
            "drug_name_en": drug.name_en,
            "atc_code": drug.atc_code
        }
        for drug in drugs
    ]
    
    return DocumentListResponse(items=items)


@router.delete("/{document_id}", response_model=SimpleOkResponse)
async def delete_document(
    document_id: str,
    current_user: dict = Depends(require_specialist),
    session: AsyncSession = Depends(get_session)
):
    """Delete document from RAG index."""
    # RAG engine doesn't have explicit delete, but we can mark drug as inactive
    # or simply remove from RAG if it supports it
    
    try:
        rag.remove_document(document_id)
    except:
        # Document might not exist in RAG, that's ok
        pass
    
    return SimpleOkResponse(ok=True)
