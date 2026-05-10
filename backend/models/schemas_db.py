from uuid import UUID, uuid4
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, TEXT
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import SQLModel, Field, Relationship

# Импортируем твои существующие Pydantic-схемы
# from schemas import CaseExtraction, CausalityVerdict, ExpectednessVerdict

class User(SQLModel, table=True):
    __tablename__ = "users"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    full_name: str
    role: str # 'reporter' | 'specialist' [cite: 55]
    is_active: bool = True

class Drug(SQLModel, table=True):
    __tablename__ = "drugs"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name_ru: str = Field(index=True)
    name_en: Optional[str] = None
    atc_code: Optional[str] = None

class Report(SQLModel, table=True):
    __tablename__ = "reports"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    reporter_id: UUID = Field(foreign_key="users.id")
    drug_id: Optional[UUID] = Field(default=None, foreign_key="drugs.id")
    status: str = "submitted" # [cite: 57]
    
    # Интеграция твоей схемы CaseExtraction через JSONB
    extracted_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))
    raw_text: str = Field(sa_column=Column(TEXT))
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AIRecommendation(SQLModel, table=True):
    __tablename__ = "ai_recommendations"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    report_id: UUID = Field(foreign_key="reports.id")
    type: str # 'completeness', 'causality', etc. [cite: 59]
    
    # Здесь хранится результат одной из твоих схем (NaranjoAssessment и др.)
    ai_output: Dict[str, Any] = Field(sa_column=Column(JSONB))
    
    specialist_verdict: Optional[str] = None
    specialist_comment: Optional[str] = None