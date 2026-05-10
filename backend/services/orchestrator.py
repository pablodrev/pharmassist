"""
Analysis orchestrator: runs all services in sequence and returns AnalysisReport.
"""

from __future__ import annotations
import logging

from core.llm_client import LLMClient
from core.rag_engine import RAGEngine
from models.schemas import AnalysisReport
from services.case_extraction import CaseExtractionService
from services.ime_service import IMEService
from services.naranjo_service import NaranjoService
from services.expectedness_service import ExpectednessService
#from services.seriousness_service import SeriousnessService

logger = logging.getLogger(__name__)


class AnalysisOrchestrator:
    def __init__(
        self,
        llm: LLMClient,
        rag: RAGEngine,
        ime_csv_path: str | None = None,
    ):
        self.case_svc = CaseExtractionService(llm)
        self.ime_svc = IMEService(llm, ime_csv_path)
        self.naranjo_svc = NaranjoService(llm)
        self.expectedness_svc = ExpectednessService(llm, rag)
        # self.seriousness_svc = SeriousnessService(llm)

    def analyze(self, case_text: str) -> AnalysisReport:
        warnings: list[str] = []

        # Step 1: Extract case structure
        logger.info("Step 1: Extracting case structure...")
        case = self.case_svc.extract(case_text)

        # Check mandatory fields
        missing = case.missing_mandatory_fields()
        if missing:
            warnings.append(f"Недостающие обязательные поля: {', '.join(missing)}")
        
        print("Case", case)

        
        # Step 2: IME clinical significance
        logger.info("Step 2: IME assessment...")
        ime = self.ime_svc.assess(case_text)

        print("IME: ", ime)
        # Step 3: Naranjo causality (only if we have enough data)
        naranjo = None
        if not case.adverse_reaction or not case.suspect_drug:
            warnings.append(
                "Оценка причинно-следственной связи (Наранжо) невозможна: "
                "отсутствуют данные о нежелательной реакции или препарате."
            )
        else:
            logger.info("Step 3: Naranjo assessment...")
            try:
                naranjo = self.naranjo_svc.assess(case_text)
                if naranjo.missing_data_for_assessment:
                    warnings.extend(naranjo.missing_data_for_assessment)
            except Exception as e:
                warnings.append(f"Ошибка оценки Наранжо: {e}")
        
        print("Naranjo: ", naranjo)
        # Step 4: Expectedness
        seriousness = None
        expectedness = None
        print("CASE ADVERSE REACTION: ", case.adverse_reaction)
        print("CASE ADVERSE REACTION DESCRIPTION: ", case.adverse_reaction.description)
        if case.adverse_reaction and case.adverse_reaction.description:
            logger.info("Step 4: Expectedness assessment...")
            try:
                expectedness = self.expectedness_svc.assess(
                    case_text,
                    case.adverse_reaction.description,
                )
                print("EXPECTEDNESS: ", expectedness)
            except Exception as e:
                warnings.append(f"Ошибка оценки предвиденности: {e}")
        # print("EXPECTEDNESS: ", expectedness)
        return AnalysisReport(
            case_extraction=case,
            ime_assessment=ime,
            naranjo_assessment=naranjo,
            expectedness_assessment=expectedness,
            missing_mandatory_fields=missing,
            warnings=warnings,
        )
