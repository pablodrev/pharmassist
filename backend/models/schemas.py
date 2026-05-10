"""
Domain models (Pydantic schemas) for pharmacovigilance analysis.
All LLM JSON outputs are validated against these schemas.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CausalityVerdict(str, Enum):
    DEFINITE = "Определённая"
    PROBABLE = "Вероятная"
    POSSIBLE = "Возможная"
    DOUBTFUL = "Сомнительная"
    CONDITIONAL = "Условная/Неклассифицируемая"
    UNASSESSABLE = "Неоцениваемая"


class ExpectednessVerdict(str, Enum):
    EXPECTED = "Предвиденный"
    UNEXPECTED = "Непредвиденный"
    UNKNOWN = "Невозможно определить"


class NaranjoAnswer(str, Enum):
    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Case Entities
# ---------------------------------------------------------------------------

class PatientInfo(BaseModel):
    age: Optional[str] = Field(None, description="Возраст пациента")
    sex: Optional[str] = Field(None, description="Пол пациента")
    weight: Optional[str] = Field(None, description="Вес пациента")
    diagnosis: Optional[str] = Field(None, description="Основное заболевание")
    comorbidities: Optional[str] = Field(None, description="Сопутствующие заболевания")


class ReporterInfo(BaseModel):
    type: Optional[str] = Field(None, description="Тип репортёра (врач/пациент/фармацевт)")
    name: Optional[str] = Field(None, description="Имя репортёра если указано")
    organization: Optional[str] = Field(None, description="Организация")


class AdverseReactionInfo(BaseModel):
    description: str = Field(..., description="Описание нежелательной реакции")
    onset_date: Optional[str] = Field(None, description="Дата начала реакции")
    outcome: Optional[str] = Field(None, description="Исход реакции")
    severity: Optional[str] = Field(None, description="Степень тяжести")
    is_serious: Optional[bool] = Field(None, description="Серьёзная НР")
    seriousness_criteria: Optional[str] = Field(None, description="Критерии серьёзности")


class DrugInfo(BaseModel):
    name: str = Field(..., description="МНН или торговое название")
    dose: Optional[str] = Field(None, description="Доза")
    route: Optional[str] = Field(None, description="Путь введения")
    start_date: Optional[str] = Field(None, description="Дата начала")
    end_date: Optional[str] = Field(None, description="Дата окончания")
    indication: Optional[str] = Field(None, description="Показание к применению")
    action_taken: Optional[str] = Field(None, description="Действия с препаратом")
    is_suspect: bool = Field(True, description="Подозреваемый препарат")


class CaseExtraction(BaseModel):
    """Structured extraction of a pharmacovigilance case report."""
    patient: Optional[PatientInfo] = None
    reporter: Optional[ReporterInfo] = None
    adverse_reaction: Optional[AdverseReactionInfo] = None
    suspect_drug: Optional[DrugInfo] = None
    concomitant_drugs: list[DrugInfo] = Field(default_factory=list)
    case_narrative: Optional[str] = Field(None, description="Краткое резюме кейса")

    def missing_mandatory_fields(self) -> list[str]:
        """Return list of missing mandatory fields for assessment."""
        missing = []
        if not self.patient:
            missing.append("Информация о пациенте")
        if not self.reporter:
            missing.append("Информация о репортёре")
        if not self.adverse_reaction or not self.adverse_reaction.description:
            missing.append("Описание нежелательной реакции")
        if not self.suspect_drug:
            missing.append("Информация о подозреваемом препарате")
        return missing


# ---------------------------------------------------------------------------
# Naranjo Algorithm
# ---------------------------------------------------------------------------

class NaranjoQuestion(BaseModel):
    question_id: int
    question_text: str
    answer: NaranjoAnswer
    score: int
    rationale: str = Field(..., description="Обоснование ответа на основе текста")


class NaranjoAssessment(BaseModel):
    """Result of Naranjo causality algorithm."""
    questions: list[NaranjoQuestion]
    total_score: int
    verdict: CausalityVerdict
    confidence: str = Field(..., description="Уверенность в оценке: высокая/средняя/низкая")
    missing_data_for_assessment: list[str] = Field(
        default_factory=list,
        description="Данные, которых не хватает для более точной оценки"
    )

    @classmethod
    def compute_verdict(cls, score: int) -> CausalityVerdict:
        if score >= 9:
            return CausalityVerdict.DEFINITE
        elif score >= 5:
            return CausalityVerdict.PROBABLE
        elif score >= 1:
            return CausalityVerdict.POSSIBLE
        else:
            return CausalityVerdict.DOUBTFUL


# ---------------------------------------------------------------------------
# IME (Important Medical Events) Check
# ---------------------------------------------------------------------------

class IMEMatch(BaseModel):
    reaction_from_text: str = Field(..., description="Реакция из текста кейса")
    ime_pt_name: str = Field(..., description="PT Name из списка EMA IME")
    ime_soc_name: str = Field(..., description="SOC Name из списка EMA IME")
    meddra_code: Optional[str] = Field(None, description="MedDRA код")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Семантическое сходство")


class IMEAssessment(BaseModel):
    is_clinically_significant: bool
    matches: list[IMEMatch]
    reactions_not_in_ime: list[str] = Field(
        default_factory=list,
        description="Реакции из текста, не найденные в EMA IME"
    )
    extracted_reactions: list[str] = Field(
        default_factory=list,
        description="Все реакции, извлечённые из текста"
    )


# ---------------------------------------------------------------------------
# Expectedness (RAG-based)
# ---------------------------------------------------------------------------

class ExpectednessAssessment(BaseModel):
    verdict: ExpectednessVerdict
    rationale: str = Field(..., description="Обоснование вердикта")
    relevant_smp_sections: list[str] = Field(
        default_factory=list,
        description="Релевантные разделы ИМП"
    )
    rag_used: bool = Field(False, description="Использовался ли RAG для оценки")


# ---------------------------------------------------------------------------
# Final Report
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Seriousness (ICH E2A)
# ---------------------------------------------------------------------------

class SeriousnessCriteria(str, Enum):
    FATAL = "Летальный исход"
    LIFE_THREATENING = "Угроза жизни"
    HOSPITALIZATION = "Госпитализация или её продление"
    DISABILITY = "Стойкая нетрудоспособность/инвалидизация"
    CONGENITAL_ANOMALY = "Врождённая аномалия"
    MEDICALLY_SIGNIFICANT = "Медицински значимое событие"


class SeriousnessAssessment(BaseModel):
    is_serious: bool
    criteria_met: list[SeriousnessCriteria] = Field(default_factory=list)
    rationale: str
    requires_expedited_reporting: bool = False


# ---------------------------------------------------------------------------
# Final Report
# ---------------------------------------------------------------------------

class AnalysisReport(BaseModel):
    """Complete pharmacovigilance analysis report."""
    case_extraction: CaseExtraction
    ime_assessment: IMEAssessment
    naranjo_assessment: Optional[NaranjoAssessment] = None
    expectedness_assessment: Optional[ExpectednessAssessment] = None
    seriousness_assessment: Optional[SeriousnessAssessment] = None
    missing_mandatory_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)



CASE_EXTRACTION_SCHEMA = """{
  "patient_age": "string | null",
  "patient_sex": "string | null",
  "patient_weight": "string | null",
  "patient_diagnosis": "string | null",
  "patient_comorbidities": "string | null",
  "reporter_type": "string | null",
  "reporter_name": "string | null",
  "reporter_organization": "string | null",
  "adverse_reaction_description": "string",
  "adverse_reaction_onset_date": "string | null",
  "adverse_reaction_outcome": "string | null",
  "adverse_reaction_severity": "string | null",
  "adverse_reaction_is_serious": "boolean | null",
  "adverse_reaction_seriousness_criteria": "string | null",
  "suspect_drug_name": "string",
  "suspect_drug_dose": "string | null",
  "suspect_drug_route": "string | null",
  "suspect_drug_start_date": "string | null",
  "suspect_drug_end_date": "string | null",
  "suspect_drug_indication": "string | null",
  "suspect_drug_action_taken": "string | null",
  "concomitant_drugs": []
}"""

IME_SCHEMA = """{
  // Список нежелательных реакций из текста
  "reactions": [
    {
      "reaction_ru": "string",
      "reaction_en": "string"
    }
  ]
}"""

NARANJO_SCHEMA = """{
  // Вопрос 1: "Есть ли ранее опубликованные убедительные отчёты об этой нежелательной реакции?"
  "q1": "yes/no/unknown",
  "q1_rationale": "строка с обоснованием",

  // Вопрос 2: "Нежелательная реакция появилась после введения подозреваемого препарата?"
  "q2": "yes/no/unknown",
  "q2_rationale": "строка с обоснованием",

  // Вопрос 3: "Улучшилось ли состояние при отмене препарата или после введения специфического антагониста?"
  "q3": "yes/no/unknown",
  "q3_rationale": "строка с обоснованием",

  // Вопрос 4: "Не появилась ли нежелательная реакция снова при повторном введении препарата (rechallenge)?"
  "q4": "yes/no/unknown",
  "q4_rationale": "строка с обоснованием",

  // Вопрос 5: "Есть ли альтернативные причины (кроме препарата), которые могли вызвать данную реакцию?"
  "q5": "yes/no/unknown",
  "q5_rationale": "строка с обоснованием",

  // Вопрос 6: "Реакция подтверждена при применении плацебо?"
  "q6": "yes/no/unknown",
  "q6_rationale": "строка с обоснованием",

  // Вопрос 7: "Препарат был обнаружен в крови (или других жидкостях) в токсической концентрации?"
  "q7": "yes/no/unknown",
  "q7_rationale": "строка с обоснованием",

  // Вопрос 8: "Тяжесть реакции была дозозависимой (увеличение дозы → усиление реакции)?"
  "q8": "yes/no/unknown",
  "q8_rationale": "строка с обоснованием",

  // Вопрос 9: "Была ли у пациента аналогичная реакция на этот или похожий препарат в прошлом?"
  "q9": "yes/no/unknown",
  "q9_rationale": "строка с обоснованием",

  // Вопрос 10: "Нежелательная реакция подтверждена объективными данными?"
  "q10": "yes/no/unknown",
  "q10_rationale": "строка с обоснованием",

  "missing_data": [] // Список недостающих данных
}"""

EXPECTEDNESS_SCHEMA = """{
  "verdict": "одно из значений: 'Предвиденный', 'Непредвиденный', 'Невозможно определить'",
  "rationale": "строка с обоснованием",
  "relevant_sections": [] // Цитаты из разделов ИМП
}"""
