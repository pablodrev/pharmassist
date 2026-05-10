# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

Pharmacovigilance Analysis Backend — a FastAPI service that analyzes adverse drug reaction (ADR) reports through an AI pipeline. It extracts structured case data from free text, assesses clinical significance (EMA IME list), calculates Naranjo causality scores, and checks expectedness via RAG over uploaded drug instruction documents.

## Commands

### Docker (recommended)
```bash
docker-compose up --build    # First run (~3-5 min, pulls images and builds)
docker-compose up            # Subsequent runs (~5 sec)
docker-compose logs -f backend
docker-compose exec backend alembic upgrade head   # Run DB migrations
```

### Local development
```bash
pip install -r requirements.txt
uvicorn api.main:app --reload
```

### Tests
```bash
pytest                                     # All tests
pytest tests/test_auth.py -v              # Single file
pytest --cov=api tests/                   # With coverage
docker-compose exec backend pytest -v     # In container
```

### Streamlit UI (legacy)
```bash
streamlit run app/main.py
```

The API is available at `http://localhost:8000`, Swagger UI at `http://localhost:8000/docs`.

## Architecture

Three-tier structure:

**`api/`** — FastAPI routes. Four modules: `auth`, `reports`, `rag`, `drugs`. Entry point is `api/main.py` (lifespan, CORS, route registration). All endpoints are under `/api/v1/`.

**`services/`** — AI/ML analysis pipeline:
- `orchestrator.py` runs the pipeline sequentially: case extraction → IME check → Naranjo → expectedness
- `case_extraction.py` calls the LLM to extract structured data (patient, reporter, drug, ADR)
- `ime_service.py` checks extracted ADRs against the EMA Important Medical Events list (`data/ema_ime_list.csv`) using pre-built embeddings
- `naranjo_service.py` implements the deterministic Naranjo algorithm
- `expectedness_service.py` queries the RAG engine to check if the ADR is expected per the drug instruction

**`core/`** — Infrastructure:
- `llm_client.py` abstracts LLM backends: Yandex Cloud (production, uses OpenAI SDK) and Ollama (local dev). Provider selected via `LLM_PROVIDER` env var.
- `rag_engine.py` builds a FAISS index from uploaded PDF/DOCX documents for expectedness lookup. Uses `sentence-transformers` (`paraphrase-multilingual-MiniLM-L12-v2`).

**`models/`**:
- `schemas_db.py` — SQLModel ORM: `User`, `Drug`, `Report`, `AIRecommendation`
- `schemas.py` — Pydantic domain models for the analysis pipeline (case data, Naranjo result, etc.)
- `prompt_schemas.py` — LLM input/output contracts

**`migrations/`** — Alembic. Currently one skeleton migration (`5ab71ed64827`). Run `alembic upgrade head` to apply.

## LLM Providers

Set `LLM_PROVIDER=yandex` (default) or `LLM_PROVIDER=ollama` in `.env`. Yandex Cloud requires `YANDEX_CLOUD_FOLDER` and `YANDEX_CLOUD_API_KEY`. Ollama requires `OLLAMA_BASE_URL` and a locally pulled model (recommended: `mistral`, `phi3`, or `phi3:mini`).

## Key env vars (see `.env.example`)

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...` |
| `SECRET_KEY` | JWT signing key |
| `LLM_PROVIDER` | `yandex` or `ollama` |
| `LLM_MODEL` | Model name for the chosen provider |
| `YANDEX_CLOUD_FOLDER` / `YANDEX_CLOUD_API_KEY` | Yandex Cloud credentials |
| `OLLAMA_BASE_URL` | Ollama endpoint URL |

## Testing setup

`pytest.ini` sets `asyncio_mode = auto`. Tests use `aiosqlite` (in-memory SQLite) so no Postgres is needed for unit tests. Fixtures are in `tests/conftest.py`. The three test files cover: health endpoint, auth/JWT, and report CRUD + analysis.

## Data files

`data/ema_ime_list.csv` and `data/good_list.txt` are static reference lists. Pre-built numpy embedding files (`.npy`) are loaded at startup by `ime_service.py` — regenerate them if you update the CSVs.
