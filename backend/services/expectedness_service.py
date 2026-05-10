"""
Service: Expectedness Assessment.
Compares adverse reaction from case with drug's Instructions for Medical Use (ИМП)
using RAG retrieval + LLM judgment.
"""

from __future__ import annotations
from pydantic import BaseModel, Field

from core.llm_client import LLMClient
from core.rag_engine import RAGEngine
from models.schemas import ExpectednessAssessment, ExpectednessVerdict
# from models.prompt_schemas import EXPECTEDNESS_SCHEMA
from models.schemas import EXPECTEDNESS_SCHEMA


class _ExpectednessLLMOutput(BaseModel):
    verdict: ExpectednessVerdict
    rationale: str = Field(..., description="Подробное обоснование на основе контекста ИМП")
    relevant_sections: list[str] = Field(
        default_factory=list,
        description="Цитаты или описание релевантных разделов ИМП"
    )


SYSTEM_WITH_RAG = """Ты — специалист по фармаконадзору. Оцени предвиденность нежелательной реакции.

ЗАДАЧА:
Определи, упомянута ли нежелательная реакция из кейса в Инструкции по медицинскому применению (ИМП) препарата.
- "Предвиденный" — реакция упомянута в ИМП (в разделе нежелательных эффектов, особых указаний или предупреждений)
- "Непредвиденный" — реакция НЕ упомянута в ИМП
- "Невозможно определить" — ИМП не загружена или контекст недостаточен

КОНТЕКСТ ИЗ ИМП:
{smp_context}

Обоснуй ответ, ссылаясь на конкретные фрагменты из ИМП."""

SYSTEM_NO_RAG = """Ты — специалист по фармаконадзору.
ИМП для данного препарата не загружена.
Верни verdict = "Невозможно определить" и укажи это в rationale."""


class ExpectednessService:
    def __init__(self, llm: LLMClient, rag: RAGEngine):
        self.llm = llm
        self.rag = rag

    def assess(self, case_text: str, adverse_reaction: str) -> ExpectednessAssessment:
        if not self.rag.is_loaded:
            result: _ExpectednessLLMOutput = self.llm.complete_structured(
                system_prompt=SYSTEM_NO_RAG,
                user_prompt=(
                    f"Нежелательная реакция: {adverse_reaction}\n"
                    f"Кейс: {case_text}"
                ),
                schema=_ExpectednessLLMOutput,
                schema_hint_explicit=EXPECTEDNESS_SCHEMA
            )
            return ExpectednessAssessment(
                verdict=result.verdict,
                rationale=result.rationale,
                relevant_smp_sections=result.relevant_sections,
                rag_used=False,
            )

        # RAG retrieval
        query = f"нежелательные реакции {adverse_reaction} побочные эффекты"
        context = self.rag.retrieve_text(query, top_k=6)

        system_prompt = SYSTEM_WITH_RAG.format(smp_context=context or "Контекст не найден.")

        result = self.llm.complete_structured(
            system_prompt=system_prompt,
            user_prompt=(
                f"Нежелательная реакция из кейса: {adverse_reaction}\n\n"
                f"Кейс (краткое описание): {case_text[:500]}"
            ),
            schema=_ExpectednessLLMOutput,
            schema_hint_explicit=EXPECTEDNESS_SCHEMA
        )

        result = _ExpectednessLLMOutput.model_validate(result)

        return ExpectednessAssessment(
            verdict=result.verdict,
            rationale=result.rationale,
            relevant_smp_sections=result.relevant_sections,
            rag_used=True,
        )
