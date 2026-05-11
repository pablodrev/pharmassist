"""
Analysis orchestrator: runs all services in sequence and returns AnalysisReport.
"""

from __future__ import annotations
import logging
import time
from contextlib import contextmanager

from core.llm_client import LLMClient
from core.rag_engine import RAGEngine
from models.schemas import AnalysisReport, CaseExtraction
from services.case_extraction import CaseExtractionService
from services.ime_service import IMEService
from services.naranjo_service import NaranjoService
from services.expectedness_service import ExpectednessService
#from services.seriousness_service import SeriousnessService

logger = logging.getLogger(__name__)


@contextmanager
def _timed(label: str):
    """Log start/end of a pipeline step with elapsed time."""
    logger.info("➡️  %s — start", label)
    t0 = time.perf_counter()
    try:
        yield
    except Exception:
        elapsed = time.perf_counter() - t0
        logger.exception("❌ %s — failed after %.2fs", label, elapsed)
        raise
    else:
        elapsed = time.perf_counter() - t0
        logger.info("✅ %s — done in %.2fs", label, elapsed)


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

    def analyze_with_case(self, case_text: str, case: CaseExtraction) -> AnalysisReport:
        """Run IME → Naranjo → Expectedness using a pre-built CaseExtraction.

        Use this when the case structure is already known (e.g. submitted via form),
        so the LLM extraction step is skipped entirely.
        case_text is still passed to IME/Naranjo/Expectedness as narrative context.
        """
        logger.info("🚀 Pipeline start (form, %d chars) — extraction skipped", len(case_text))
        pipeline_t0 = time.perf_counter()
        warnings: list[str] = []

        missing = case.missing_mandatory_fields()
        if missing:
            warnings.append(f"Недостающие обязательные поля: {', '.join(missing)}")

        with _timed("Step 2/4 — IME assessment"):
            ime = self.ime_svc.assess(case_text)

        naranjo = None
        if not case.adverse_reaction or not case.suspect_drug:
            warnings.append(
                "Оценка причинно-следственной связи (Наранжо) невозможна: "
                "отсутствуют данные о нежелательной реакции или препарате."
            )
            logger.info("⏭️  Step 3/4 — Naranjo skipped (missing reaction or drug)")
        else:
            with _timed("Step 3/4 — Naranjo assessment"):
                try:
                    naranjo = self.naranjo_svc.assess(case_text)
                    if naranjo.missing_data_for_assessment:
                        warnings.extend(naranjo.missing_data_for_assessment)
                except Exception as e:
                    warnings.append(f"Ошибка оценки Наранжо: {e}")

        expectedness = None
        if case.adverse_reaction and case.adverse_reaction.description:
            with _timed("Step 4/4 — Expectedness assessment"):
                try:
                    expectedness = self.expectedness_svc.assess(
                        case_text,
                        case.adverse_reaction.description,
                    )
                except Exception as e:
                    warnings.append(f"Ошибка оценки предвиденности: {e}")
        else:
            logger.info("⏭️  Step 4/4 — Expectedness skipped (no reaction description)")

        logger.info(
            "🏁 Pipeline finished in %.2fs (form path)",
            time.perf_counter() - pipeline_t0,
        )
        return AnalysisReport(
            case_extraction=case,
            ime_assessment=ime,
            naranjo_assessment=naranjo,
            expectedness_assessment=expectedness,
            missing_mandatory_fields=missing,
            warnings=warnings,
        )

    def analyze(self, case_text: str) -> AnalysisReport:
        logger.info("🚀 Pipeline start (raw text, %d chars)", len(case_text))
        pipeline_t0 = time.perf_counter()
        warnings: list[str] = []

        with _timed("Step 1/4 — Case extraction (LLM)"):
            case = self.case_svc.extract(case_text)

        missing = case.missing_mandatory_fields()
        if missing:
            warnings.append(f"Недостающие обязательные поля: {', '.join(missing)}")

        with _timed("Step 2/4 — IME assessment"):
            ime = self.ime_svc.assess(case_text)

        naranjo = None
        if not case.adverse_reaction or not case.suspect_drug:
            warnings.append(
                "Оценка причинно-следственной связи (Наранжо) невозможна: "
                "отсутствуют данные о нежелательной реакции или препарате."
            )
            logger.info("⏭️  Step 3/4 — Naranjo skipped (missing reaction or drug)")
        else:
            with _timed("Step 3/4 — Naranjo assessment"):
                try:
                    naranjo = self.naranjo_svc.assess(case_text)
                    if naranjo.missing_data_for_assessment:
                        warnings.extend(naranjo.missing_data_for_assessment)
                except Exception as e:
                    warnings.append(f"Ошибка оценки Наранжо: {e}")

        expectedness = None
        if case.adverse_reaction and case.adverse_reaction.description:
            with _timed("Step 4/4 — Expectedness assessment"):
                try:
                    expectedness = self.expectedness_svc.assess(
                        case_text,
                        case.adverse_reaction.description,
                    )
                except Exception as e:
                    warnings.append(f"Ошибка оценки предвиденности: {e}")
        else:
            logger.info("⏭️  Step 4/4 — Expectedness skipped (no reaction description)")

        logger.info(
            "🏁 Pipeline finished in %.2fs (raw text path)",
            time.perf_counter() - pipeline_t0,
        )
        return AnalysisReport(
            case_extraction=case,
            ime_assessment=ime,
            naranjo_assessment=naranjo,
            expectedness_assessment=expectedness,
            missing_mandatory_fields=missing,
            warnings=warnings,
        )
