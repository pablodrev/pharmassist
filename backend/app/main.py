"""
Pharmacovigilance Analysis MVP
Streamlit entry point: app/main.py
Run: streamlit run app/main.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import pathlib
import streamlit as st

from core.llm_client import LLMClient, DEFAULT_MODEL, DEFAULT_PROVIDER
from core.rag_engine import RAGEngine
from services.orchestrator import AnalysisOrchestrator
from app.components import render_full_report

logging.basicConfig(level=logging.INFO)

st.set_page_config(
    page_title="Фармаконадзор — Анализ НР",
    page_icon="💊",
    layout="wide",
)

st.title("💊 Система анализа сообщений о нежелательных реакциях")
st.caption("MVP · Алгоритм Наранжо · EMA IME · RAG по ИМП · Локальная LLM")

if "rag_engine" not in st.session_state:
    st.session_state.rag_engine = RAGEngine()
if "report" not in st.session_state:
    st.session_state.report = None
if "llm_model" not in st.session_state:
    st.session_state.llm_model = DEFAULT_MODEL
if "llm_provider" not in st.session_state:
    st.session_state.llm_provider = DEFAULT_PROVIDER
if "yandex_model" not in st.session_state:
    st.session_state.yandex_model = "gpt-oss-120b/latest"
if "yandex_folder_id" not in st.session_state:
    st.session_state.yandex_folder_id = os.getenv("YANDEX_CLOUD_FOLDER", "")
if "yandex_api_key" not in st.session_state:
    st.session_state.yandex_api_key = os.getenv("YANDEX_CLOUD_API_KEY", "")
if "case_text_value" not in st.session_state:
    st.session_state.case_text_value = ""

# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Настройки")
    provider_options = ["Ollama", "Yandex Cloud"]
    selected_provider = st.radio(
        "Провайдер LLM:", provider_options,
        index=0 if st.session_state.llm_provider == "ollama" else 1,
        horizontal=True,
        key="llm_provider_selector",
    )
    st.session_state.llm_provider = "yandex" if selected_provider == "Yandex Cloud" else "ollama"

    if st.session_state.llm_provider == "ollama":
        model_options = ["mistral", "phi3", "phi3:mini", "llama3.2", "qwen2.5:3b"]
        selected_model = st.selectbox(
            "Модель LLM (Ollama)", model_options,
            index=model_options.index(st.session_state.llm_model)
            if st.session_state.llm_model in model_options else 0,
        )
        st.session_state.llm_model = selected_model
        if LLMClient(model=selected_model, provider="ollama").is_available():
            st.success(f"✅ Ollama · {selected_model}")
        else:
            st.error("❌ Ollama не запущен\n`ollama serve`")
    else:
        st.session_state.yandex_model = st.text_input(
            "Модель Yandex Cloud",
            value=st.session_state.yandex_model,
            placeholder="gpt-oss-120b/latest",
            key="yandex_model_input",
        )
        st.session_state.yandex_folder_id = st.text_input(
            "YANDEX_CLOUD_FOLDER",
            value=st.session_state.yandex_folder_id,
            help="Folder id вашего проекта в Yandex Cloud",
            key="yandex_folder_input",
        )
        st.session_state.yandex_api_key = st.text_input(
            "YANDEX_CLOUD_API_KEY",
            value=st.session_state.yandex_api_key,
            type="password",
            key="yandex_api_key_input",
        )
        st.session_state.llm_model = st.session_state.yandex_model
        if st.session_state.yandex_folder_id and st.session_state.yandex_api_key:
            st.success(f"✅ Yandex Cloud · {st.session_state.yandex_model}")
        else:
            st.warning("⚠️ Укажите ключ и folder ID для Yandex Cloud")

    st.markdown("---")
    st.header("📄 ИМП (PDF)")
    smp_file = st.file_uploader("Инструкция по МП", type=["pdf"])
    rag = st.session_state.rag_engine
    if smp_file is not None and not rag.is_loaded:
        with st.spinner("Индексирование..."):
            n = rag.load_pdf(smp_file.read())
        st.success(f"✅ {n} фрагментов")
    if rag.is_loaded:
        st.success("✅ RAG активен")
        if st.button("🗑️ Сбросить ИМП"):
            st.session_state.rag_engine = RAGEngine()
            st.rerun()
    else:
        st.warning("⚠️ ИМП не загружена")

    st.markdown("---")
    st.header("📊 EMA IME (CSV)")
    ime_file = st.file_uploader("IME список", type=["csv"], help="MedDRA, PT Name, SOC Name")
    if ime_file is not None:
        tmp = pathlib.Path("ema_ime_list.csv")
        tmp.write_bytes(ime_file.read())
        st.session_state["ime_csv_path"] = str(tmp)
        st.success("✅ IME загружен")
    else:
        default_ime = pathlib.Path(__file__).parent.parent / "data" / "ema_ime_list.csv"
        if default_ime.exists() and "ime_csv_path" not in st.session_state:
            st.session_state["ime_csv_path"] = str(default_ime)
            st.info("ℹ️ Встроенный IME список")
    st.markdown("---")
    st.caption("🔒 Данные обрабатываются локально")

# ── Case input ───────────────────────────────────────────────────────────────
st.subheader("📝 Ввод сообщения о нежелательной реакции")
input_method = st.radio("Способ:", ["Текст", "TXT файл"], horizontal=True)
case_text = ""

if input_method == "Текст":
    case_text = st.text_area(
        "Текст сообщения о НР:", value=st.session_state.case_text_value,
        height=270,
        placeholder="Пациентка, 45 лет. Препарат Х, 10 мг/сут с 01.01.2025. "
                     "Через 3 дня — крапивница. Препарат отменён. Репортёр: врач...",
        key="case_text_area",
    )
else:
    up = st.file_uploader("TXT файл", type=["txt"])
    if up:
        case_text = up.read().decode("utf-8", errors="replace")
        st.text_area("Содержимое:", value=case_text, height=180, disabled=True)

EXAMPLES = {
    "Кейс 1: Апротинин (пирогенная, беременная)":
        "В Департамент безопасности лекарственных средств поступила серия сообщений о побочном "
        "эффекте на препарат апротинин (внутривенное введение в стационаре). "
        "Побочный эффект — пирогенная реакция. Пациентка — женщина, беременная. "
        "Дата начала — 15.07.2025, дата окончания — 16.07.2025. "
        "Исход: улучшение. При первых признаках введение прекращено. Репортёр: врач стационара.",
    "Кейс 2: Деламанид (галлюцинации, ребёнок 4 лет)":
        "Девочка 4 лет, туберкулёз. Деламанид с 05.07.2024. С 25.02.25 — нарушения сна. "
        "С 01.03.25 — ночные галлюцинации. Отмена → симптомы исчезли. "
        "Повторное назначение 21.03.25 → рецидив. Отменён 01.04.25. "
        "Сопутствующие: протионамид, пиразинамид, линезолид, левофлоксацин, циклосерин. "
        "Репортёр: врач.",
    "Кейс 3: Пембролизумаб (токсикодермия, смерть)":
        "Пациентка с меланомой кожи IIB ст. 16.01.2025 — пембролизумаб 200 мг в/в. "
        "17.01.25 — высыпания с зудом. Прогрессирование — буллёзная эритема, десквамация. "
        "Диагноз: токсикодермия эритематозно-буллёзная (синдром Стивенса-Джонсона). "
        "Сепсис, септический шок. Дата смерти: 01.02.2025. Репортёр: врач стационара.",
    "Кейс 6: Бевацизумаб (нейтропения 2 ст.)":
        "Пациентка с НМРЛ. Бевацизумаб в/в, 29.01–10.03.2021. "
        "НР: нейтропения 2 степени. Препарат не отменён. Введён Г-КСФ. "
        "Сопутствующие: атезолизумаб, паклитаксел 175 мг/м². Репортёр: врач.",
}

with st.expander("📚 Тестовые кейсы"):
    cols = st.columns(2)
    for i, (label, text) in enumerate(EXAMPLES.items()):
        with cols[i % 2]:
            if st.button(label, use_container_width=True):
                st.session_state.case_text_value = text
                st.rerun()

if st.session_state.case_text_value and not case_text:
    case_text = st.session_state.case_text_value

# ── Actions ──────────────────────────────────────────────────────────────────
st.markdown("---")
col_btn, col_clear = st.columns([4, 1])
with col_btn:
    analyze_clicked = st.button(
        "🔍 Анализ", type="primary",
        disabled=not case_text.strip(), use_container_width=True,
    )
with col_clear:
    if st.button("🗑️ Сброс", use_container_width=True):
        st.session_state.report = None
        st.session_state.case_text_value = ""
        st.rerun()

if analyze_clicked and case_text.strip():
    if st.session_state.llm_provider == "yandex":
        llm = LLMClient(
            model=st.session_state.llm_model,
            provider="yandex",
            yandex_api_key=st.session_state.yandex_api_key,
            yandex_folder_id=st.session_state.yandex_folder_id,
        )
        if not llm.is_available():
            st.error(
                "❌ Yandex Cloud не настроен. Укажите YANDEX_CLOUD_API_KEY и YANDEX_CLOUD_FOLDER"
            )
            st.stop()
    else:
        llm = LLMClient(model=st.session_state.llm_model, provider="ollama")
        if not llm.is_available():
            st.error("❌ Ollama не запущен. Запустите: `ollama serve`")
            st.stop()

    ime_path = st.session_state.get("ime_csv_path")
    orch = AnalysisOrchestrator(llm=llm, rag=st.session_state.rag_engine, ime_csv_path=ime_path)
    with st.spinner("⏳ Анализ выполняется (30–90 с)..."):
        progress = st.progress(0, "Инициализация...")
        try:
            progress.progress(20, "Извлечение данных кейса...")
            report = orch.analyze(case_text)
            print("Report: ", report)
            st.session_state.report = report
            progress.progress(100, "✅ Готово!")
        except RuntimeError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Ошибка: {e}")
            raise

# ── Results ──────────────────────────────────────────────────────────────────
if st.session_state.report:
    st.markdown("---")
    col_h, col_exp = st.columns([5, 1])
    with col_h:
        st.header("📊 Результаты анализа")
    with col_exp:
        try:
            from utils.report_exporter import export_report_docx
            drug = ""
            if st.session_state.report.case_extraction.suspect_drug:
                drug = st.session_state.report.case_extraction.suspect_drug.name or ""
            docx_bytes = export_report_docx(st.session_state.report, drug)
            st.download_button(
                "📥 DOCX", data=docx_bytes,
                file_name=f"НР_{drug or 'отчет'}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
        except Exception as e:
            st.caption(f"Экспорт: {e}")

    render_full_report(st.session_state.report)
