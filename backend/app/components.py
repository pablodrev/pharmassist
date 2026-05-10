"""
Streamlit UI components for displaying analysis results.
"""

import streamlit as st
from models.schemas import (
    AnalysisReport, NaranjoAnswer, CausalityVerdict,
    ExpectednessVerdict, IMEMatch
)


# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------

def _verdict_color(verdict: CausalityVerdict) -> str:
    mapping = {
        CausalityVerdict.DEFINITE:      "#d32f2f",
        CausalityVerdict.PROBABLE:      "#f57c00",
        CausalityVerdict.POSSIBLE:      "#fbc02d",
        CausalityVerdict.DOUBTFUL:      "#388e3c",
        CausalityVerdict.CONDITIONAL:   "#1976d2",
        CausalityVerdict.UNASSESSABLE:  "#757575",
    }
    return mapping.get(verdict, "#757575")


def _expectedness_color(verdict: ExpectednessVerdict) -> str:
    return {"Предвиденный": "#388e3c", "Непредвиденный": "#d32f2f"}.get(
        verdict.value, "#757575"
    )


def _answer_badge(answer: NaranjoAnswer) -> str:
    badges = {
        NaranjoAnswer.YES:     "🟢 Да",
        NaranjoAnswer.NO:      "🔴 Нет",
        NaranjoAnswer.UNKNOWN: "⚪ Неизвестно",
    }
    return badges.get(answer, "—")


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def render_case_extraction(report: AnalysisReport):
    case = report.case_extraction

    st.subheader("📋 Структура кейса")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**👤 Пациент**")
        if case.patient:
            p = case.patient
            info = {
                "Возраст": p.age,
                "Пол": p.sex,
                "Вес": p.weight,
                "Диагноз": p.diagnosis,
                "Сопутствующие заболевания": p.comorbidities,
            }
            for k, v in info.items():
                if v:
                    st.markdown(f"- **{k}:** {v}")
        else:
            st.warning("⚠️ Информация о пациенте отсутствует")

        st.markdown("**🏥 Репортёр**")
        if case.reporter:
            r = case.reporter
            for k, v in [("Тип", r.type), ("Имя", r.name), ("Организация", r.organization)]:
                if v:
                    st.markdown(f"- **{k}:** {v}")
        else:
            st.warning("⚠️ Информация о репортёре отсутствует")

    with col2:
        st.markdown("**⚠️ Нежелательная реакция**")
        if case.adverse_reaction:
            ar = case.adverse_reaction
            for k, v in [
                ("Описание", ar.description),
                ("Дата начала", ar.onset_date),
                ("Исход", ar.outcome),
                ("Степень тяжести", ar.severity),
                ("Серьёзная", "Да" if ar.is_serious else ("Нет" if ar.is_serious is not None else None)),
                ("Критерии серьёзности", ar.seriousness_criteria),
            ]:
                if v:
                    st.markdown(f"- **{k}:** {v}")
        else:
            st.warning("⚠️ Информация о нежелательной реакции отсутствует")

        st.markdown("**💊 Подозреваемый препарат**")
        if case.suspect_drug:
            d = case.suspect_drug
            for k, v in [
                ("Название", d.name),
                ("Доза", d.dose),
                ("Путь введения", d.route),
                ("Начало", d.start_date),
                ("Окончание", d.end_date),
                ("Показание", d.indication),
                ("Действия с препаратом", d.action_taken),
            ]:
                if v:
                    st.markdown(f"- **{k}:** {v}")
        else:
            st.warning("⚠️ Информация о подозреваемом препарате отсутствует")

    if case.concomitant_drugs:
        with st.expander(f"💊 Сопутствующие препараты ({len(case.concomitant_drugs)})"):
            for drug in case.concomitant_drugs:
                parts = [f"**{drug.name}**"]
                if drug.dose:
                    parts.append(f"доза: {drug.dose}")
                if drug.start_date:
                    parts.append(f"с {drug.start_date}")
                if drug.end_date:
                    parts.append(f"по {drug.end_date}")
                st.markdown("- " + ", ".join(parts))

    if case.case_narrative:
        with st.expander("📝 Резюме кейса"):
            st.write(case.case_narrative)


def render_ime_assessment(report: AnalysisReport):
    ime = report.ime_assessment

    st.subheader("🏥 Клиническая значимость (EMA IME)")

    if not ime.extracted_reactions:
        st.info("Нежелательные реакции не извлечены из текста.")
        return

    st.markdown(f"**Извлечённые реакции:** {', '.join(ime.extracted_reactions)}")

    if ime.is_clinically_significant:
        st.error(f"🚨 Клинически значимые реакции найдены в EMA IME списке!")
    else:
        st.success("✅ Реакции не найдены в EMA IME списке")

    if ime.matches:
        st.markdown("**Совпадения с EMA IME:**")
        for match in ime.matches:
            score_pct = int(match.similarity_score * 100)
            score_bar = "█" * (score_pct // 10) + "░" * (10 - score_pct // 10)
            with st.expander(
                f"🔴 {match.reaction_from_text} → {match.ime_pt_name} ({score_pct}%)"
            ):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Реакция из кейса:** {match.reaction_from_text}")
                    st.markdown(f"**PT Name (IME):** {match.ime_pt_name}")
                    st.markdown(f"**SOC Name:** {match.ime_soc_name}")
                with col2:
                    if match.meddra_code:
                        st.markdown(f"**MedDRA код:** {match.meddra_code}")
                    st.markdown(f"**Сходство:** `{score_bar}` {score_pct}%")

    if ime.reactions_not_in_ime:
        st.markdown(
            f"**Реакции вне IME списка:** {', '.join(ime.reactions_not_in_ime)}"
        )


def render_naranjo_assessment(report: AnalysisReport):
    naranjo = report.naranjo_assessment
    if not naranjo:
        st.subheader("🔗 Причинно-следственная связь (Наранжо)")
        st.warning("Оценка причинно-следственной связи не была выполнена.")
        return

    st.subheader("🔗 Причинно-следственная связь (Наранжо)")

    color = _verdict_color(naranjo.verdict)
    col1, col2, col3 = st.columns(3)
    col1.metric("Итоговый балл", naranjo.total_score)
    col2.metric("Уверенность", naranjo.confidence)
    col3.markdown(
        f"<div style='text-align:center;padding:10px;"
        f"background:{color};border-radius:8px;color:white;"
        f"font-weight:bold;font-size:1.1em'>{naranjo.verdict.value}</div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown("**Детали по вопросам Наранжо:**")

    answer_icons = {
        NaranjoAnswer.YES: "🟢",
        NaranjoAnswer.NO: "🔴",
        NaranjoAnswer.UNKNOWN: "⚪",
    }

    for q in naranjo.questions:
        score_str = f"+{q.score}" if q.score > 0 else str(q.score)
        icon = answer_icons.get(q.answer, "⚪")
        with st.expander(
            f"В{q.question_id}. {icon} {q.question_text[:70]}... "
            f"[{_answer_badge(q.answer)}, {score_str}]"
        ):
            st.markdown(f"**Вопрос:** {q.question_text}")
            st.markdown(f"**Ответ:** {_answer_badge(q.answer)} (балл: {score_str})")
            st.markdown(f"**Обоснование:** {q.rationale}")

    if naranjo.missing_data_for_assessment:
        st.markdown("**⚠️ Для более точной оценки не хватает:**")
        for item in naranjo.missing_data_for_assessment:
            st.markdown(f"- {item}")


def render_expectedness_assessment(report: AnalysisReport):
    exp = report.expectedness_assessment

    st.subheader("📖 Предвиденность НР (по ИМП)")

    if not exp:
        st.warning("Оценка предвиденности не выполнена.")
        return

    color = _expectedness_color(exp.verdict)
    st.markdown(
        f"<div style='padding:12px;background:{color};border-radius:8px;"
        f"color:white;font-weight:bold;font-size:1.15em'>"
        f"Вердикт: {exp.verdict.value}"
        f"{'  |  RAG ✅' if exp.rag_used else '  |  ИМП не загружена'}</div>",
        unsafe_allow_html=True,
    )
    st.markdown("")
    st.markdown(f"**Обоснование:** {exp.rationale}")

    if exp.relevant_smp_sections:
        with st.expander("📄 Релевантные разделы ИМП"):
            for section in exp.relevant_smp_sections:
                st.markdown(f"> {section}")


def render_warnings(report: AnalysisReport):
    if report.missing_mandatory_fields or report.warnings:
        st.subheader("⚠️ Предупреждения и недостающие данные")

        if report.missing_mandatory_fields:
            st.error(
                "**Обязательные поля отсутствуют:**\n"
                + "\n".join(f"- {f}" for f in report.missing_mandatory_fields)
            )

        unique_warnings = list(dict.fromkeys(report.warnings))
        for w in unique_warnings:
            if w not in report.missing_mandatory_fields:
                st.warning(w)


def render_full_report(report: AnalysisReport):
    render_warnings(report)
    st.markdown("---")

    tabs = st.tabs([
        "📋 Структура кейса",
        "🏥 IME список",
        "🔗 Наранжо",
        "📖 Предвиденность",
    ])

    print(report)

    with tabs[0]:
        render_case_extraction(report)
    with tabs[1]:
        render_ime_assessment(report)
    with tabs[2]:
        render_naranjo_assessment(report)
    with tabs[3]:
        render_expectedness_assessment(report)
