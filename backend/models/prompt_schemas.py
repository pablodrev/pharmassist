from __future__ import annotations

CASE_EXRTRACTION_SCHEMA = """{
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
  "reactions": []
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