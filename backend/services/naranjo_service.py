"""
Service: Naranjo Causality Algorithm.
LLM answers each of the 10 Naranjo questions based on case text,
algorithm computes score and verdict deterministically.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional

from core.llm_client import LLMClient
from models.schemas import (
    NaranjoAssessment, NaranjoQuestion, NaranjoAnswer, CausalityVerdict
)
# from models.prompt_schemas import NARANJO_SCHEMA
from models.schemas import NARANJO_SCHEMA


# ---------------------------------------------------------------------------
# Naranjo scoring table
# Q#: (question_text, yes_score, no_score, unknown_score)
# ---------------------------------------------------------------------------
NARANJO_QUESTIONS: list[tuple[int, str, int, int, int]] = [
    (1,  "Есть ли ранее опубликованные убедительные отчёты об этой нежелательной реакции?", 1, 0, 0),
    (2,  "Нежелательная реакция появилась после введения подозреваемого препарата?", 2, -1, 0),
    (3,  "Улучшилось ли состояние при отмене препарата или после введения специфического антагониста?", 1, 0, 0),
    (4,  "Не появилась ли нежелательная реакция снова при повторном введении препарата (rechallenge)?", 2, -1, 0),
    (5,  "Есть ли альтернативные причины (кроме препарата), которые могли вызвать данную реакцию?", -1, 2, 0),
    (6,  "Реакция подтверждена при применении плацебо?", -1, 1, 0),
    (7,  "Препарат был обнаружен в крови (или других жидкостях) в токсической концентрации?", 1, 0, 0),
    (8,  "Тяжесть реакции была дозозависимой (увеличение дозы → усиление реакции)?", 1, 0, 0),
    (9,  "Была ли у пациента аналогичная реакция на этот или похожий препарат в прошлом?", 1, 0, 0),
    (10, "Нежелательная реакция подтверждена объективными данными?", 1, 0, 0),
]


class _NaranjoLLMOutput(BaseModel):
    """LLM answers for all 10 Naranjo questions."""
    q1: NaranjoAnswer
    q1_rationale: str
    q2: NaranjoAnswer
    q2_rationale: str
    q3: NaranjoAnswer
    q3_rationale: str
    q4: NaranjoAnswer
    q4_rationale: str
    q5: NaranjoAnswer
    q5_rationale: str
    q6: NaranjoAnswer
    q6_rationale: str
    q7: NaranjoAnswer
    q7_rationale: str
    q8: NaranjoAnswer
    q8_rationale: str
    q9: NaranjoAnswer
    q9_rationale: str
    q10: NaranjoAnswer
    q10_rationale: str
    missing_data: list[str] = Field(
        default_factory=list,
        description="Перечень данных, которых не хватает для точной оценки"
    )


SYSTEM_PROMPT = """Ты — клинический фармаколог, специалист по оценке причинно-следственной связи
нежелательных реакций по алгоритму Наранжо.

Ответь на каждый из 10 вопросов алгоритма Наранжо строго на основании предоставленного текста кейса.
- "yes" — если текст явно подтверждает утверждение
- "no" — если текст явно опровергает утверждение
- "unknown" — если информации недостаточно для ответа

Для каждого вопроса укажи краткое обоснование (rationale) со ссылкой на факты из текста.
Перечисли missing_data — данные, которых не хватает для более точной оценки."""


class NaranjoService:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def _compute_score(self, answers: _NaranjoLLMOutput) -> tuple[list[NaranjoQuestion], int]:
        answer_map = {
            1: (answers.q1, answers.q1_rationale),
            2: (answers.q2, answers.q2_rationale),
            3: (answers.q3, answers.q3_rationale),
            4: (answers.q4, answers.q4_rationale),
            5: (answers.q5, answers.q5_rationale),
            6: (answers.q6, answers.q6_rationale),
            7: (answers.q7, answers.q7_rationale),
            8: (answers.q8, answers.q8_rationale),
            9: (answers.q9, answers.q9_rationale),
            10: (answers.q10, answers.q10_rationale),
        }

        questions: list[NaranjoQuestion] = []
        total = 0

        for q_id, q_text, yes_s, no_s, unk_s in NARANJO_QUESTIONS:
            answer, rationale = answer_map[q_id]
            if answer == NaranjoAnswer.YES:
                score = yes_s
            elif answer == NaranjoAnswer.NO:
                score = no_s
            else:
                score = unk_s
            total += score
            questions.append(NaranjoQuestion(
                question_id=q_id,
                question_text=q_text,
                answer=answer,
                score=score,
                rationale=rationale,
            ))

        return questions, total

    def _confidence(self, answers: _NaranjoLLMOutput) -> str:
        unknowns = sum(
            1 for a in [
                answers.q1, answers.q2, answers.q3, answers.q4, answers.q5,
                answers.q6, answers.q7, answers.q8, answers.q9, answers.q10
            ] if a == NaranjoAnswer.UNKNOWN
        )
        if unknowns <= 2:
            return "высокая"
        elif unknowns <= 5:
            return "средняя"
        else:
            return "низкая"

    def assess(self, case_text: str) -> NaranjoAssessment:
        answers: _NaranjoLLMOutput = self.llm.complete_structured(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=(
                f"Оцени следующий кейс по алгоритму Наранжо:\n\n{case_text}\n\n"
                "Ответь на все 10 вопросов."
            ),
            schema=_NaranjoLLMOutput,
            schema_hint_explicit=NARANJO_SCHEMA
        )
        answers = _NaranjoLLMOutput.model_validate(answers)

        questions, total = self._compute_score(answers)
        verdict = NaranjoAssessment.compute_verdict(total)
        confidence = self._confidence(answers)

        return NaranjoAssessment(
            questions=questions,
            total_score=total,
            verdict=verdict,
            confidence=confidence,
            missing_data_for_assessment=answers.missing_data,
        )
