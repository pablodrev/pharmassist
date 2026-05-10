"""
Service: Extract structured case data from free-text report.
"""

from __future__ import annotations
import json
import logging
from pydantic import BaseModel, Field
from typing import Optional

from core.llm_client import LLMClient

logger = logging.getLogger(__name__)
from models.schemas import (
    CaseExtraction, PatientInfo, ReporterInfo,
    AdverseReactionInfo, DrugInfo
)

# from models.prompt_schemas import CASE_EXTRACTION_SCHEMA
from models.schemas import CASE_EXTRACTION_SCHEMA

# Internal intermediate schema for LLM output
class _LLMCaseOutput(BaseModel):
    patient_age: Optional[str] = None
    patient_sex: Optional[str] = None
    patient_weight: Optional[str] = None
    patient_diagnosis: Optional[str] = None
    patient_comorbidities: Optional[str] = None
    reporter_type: Optional[str] = None
    reporter_name: Optional[str] = None
    reporter_organization: Optional[str] = None
    adverse_reaction_description: Optional[str] = None
    adverse_reaction_onset_date: Optional[str] = None
    adverse_reaction_outcome: Optional[str] = None
    adverse_reaction_severity: Optional[str] = None
    adverse_reaction_is_serious: Optional[bool] = None
    adverse_reaction_seriousness_criteria: Optional[str] = None
    suspect_drug_name: Optional[str] = None
    suspect_drug_dose: Optional[str] = None
    suspect_drug_route: Optional[str] = None
    suspect_drug_start_date: Optional[str] = None
    suspect_drug_end_date: Optional[str] = None
    suspect_drug_indication: Optional[str] = None
    suspect_drug_action_taken: Optional[str] = None
    concomitant_drugs: list[dict] = Field(default_factory=list)


SYSTEM_PROMPT = """Ты — специалист по фармаконадзору. Твоя задача — извлечь структурированные данные
из сообщения о нежелательной реакции на лекарственный препарат.
Обязательные поля для полноценной оценки: пациент, репортёр, нежелательная реакция, подозреваемый препарат.
Если данные отсутствуют в тексте — используй null.
Отвечай строго на русском языке."""


class CaseExtractionService:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def extract(self, case_text: str) -> CaseExtraction:
        logger.info(
            "case_extraction: input len=%d, preview=%r",
            len(case_text),
            case_text[:400],
        )
        raw: _LLMCaseOutput = self.llm.complete_structured(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=f"Извлеки данные из следующего сообщения о побочном эффекте:\n\n{case_text}",
            schema=_LLMCaseOutput,
            schema_hint_explicit=CASE_EXTRACTION_SCHEMA
        )

        raw = _LLMCaseOutput.model_validate(raw)    

        print("CASE EXTRACTOR RAW: ", raw)

        patient = PatientInfo(
            age=raw.patient_age,
            sex=raw.patient_sex,
            weight=raw.patient_weight,
            diagnosis=raw.patient_diagnosis,
            comorbidities=raw.patient_comorbidities,
        ) if any([raw.patient_age, raw.patient_sex, raw.patient_diagnosis]) else None

        reporter = ReporterInfo(
            type=raw.reporter_type,
            name=raw.reporter_name,
            organization=raw.reporter_organization,
        ) if any([raw.reporter_type, raw.reporter_name, raw.reporter_organization]) else None

        adverse_reaction = AdverseReactionInfo(
            description=raw.adverse_reaction_description,
            onset_date=raw.adverse_reaction_onset_date,
            outcome=raw.adverse_reaction_outcome,
            severity=raw.adverse_reaction_severity,
            is_serious=raw.adverse_reaction_is_serious,
            seriousness_criteria=raw.adverse_reaction_seriousness_criteria,
        ) if raw.adverse_reaction_description else None

        suspect_drug = DrugInfo(
            name=raw.suspect_drug_name,
            dose=raw.suspect_drug_dose,
            route=raw.suspect_drug_route,
            start_date=raw.suspect_drug_start_date,
            end_date=raw.suspect_drug_end_date,
            indication=raw.suspect_drug_indication,
            action_taken=raw.suspect_drug_action_taken,
            is_suspect=True,
        ) if raw.suspect_drug_name else None

        concomitant = []
        for d in raw.concomitant_drugs:
            try:
                concomitant.append(DrugInfo(
                    name=d.get("name", ""),
                    dose=d.get("dose"),
                    route=d.get("route"),
                    start_date=d.get("start_date"),
                    end_date=d.get("end_date"),
                    indication=d.get("indication"),
                    is_suspect=False,
                ))
            except Exception:
                pass

        return CaseExtraction(
            patient=patient,
            reporter=reporter,
            adverse_reaction=adverse_reaction,
            suspect_drug=suspect_drug,
            concomitant_drugs=concomitant,
        )
