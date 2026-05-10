# PharmAssist Backend API

FastAPI backend для системы анализа сообщений о нежелательных реакциях на лекарственные препараты.

## Структура проекта

```
pharma_backend/
├── api/
│   ├── main.py           # FastAPI приложение
│   └── routes/           # Маршруты (auth, reports, rag, drugs)
├── models/
│   ├── schemas.py        # Pydantic модели (бизнес-логика)
│   ├── schemas_db.py     # SQLModel для БД
│   └── prompt_schemas.py # Схемы для LLM
├── services/             # AI сервисы (случай уже есть)
│   ├── orchestrator.py
│   ├── case_extraction.py
│   ├── ime_service.py
│   ├── naranjo_service.py
│   └── expectedness_service.py
├── core/
│   ├── llm_client.py    # Клиент LLM (Ollama, Yandex)
│   └── rag_engine.py    # RAG для поиска в ИМП
├── auth.py              # JWT аутентификация
├── db.py                # Конфигурация БД
├── api_schemas.py       # Pydantic схемы для API
├── requirements.txt     # Зависимости
├── Dockerfile           # Docker контейнер
├── docker-compose.yaml  # Docker Compose
├── .env.example         # Пример переменных окружения
└── tests/               # Тесты
    ├── conftest.py
    ├── test_health.py
    ├── test_auth.py
    └── test_reports.py
```

## Быстрый старт

### 1. Подготовка

Скопируй `.env.example` в `.env` и отредактируй значения:

```bash
cp .env.example .env
```

### 2. Выбор LLM провайдера

**По умолчанию используется Yandex Cloud API** (рекомендуется для production).

#### ✅ Вариант A: Yandex Cloud API (по умолчанию, рекомендуется)

```env
LLM_PROVIDER=yandex
LLM_MODEL=gpt-4o-mini
YANDEX_CLOUD_API_KEY=<your-api-key>
YANDEX_CLOUD_FOLDER=<your-folder-id>
```

- Получи учетные данные: https://console.cloud.yandex.com/
- Анализ всегда работает, нет необходимости в локальном сервере
- Поддерживаются все функции

#### Вариант B: Локальный Ollama (только для переанализа)

Ollama используется **только** если специалист выбирает её при переанализе отчёта.

```env
LLM_PROVIDER=yandex  # По-прежнему используется Yandex по умолчанию
OLLAMA_BASE_URL=http://localhost:11434  # Адрес локальной Ollama
```

Для использования Ollama при переанализе:

1. Установите Ollama (см. раздел "Локальная Ollama для переанализа" ниже)
2. Запустите: `ollama serve`
3. Скачайте модель: `ollama pull mistral`
4. Специалист сможет выбрать Ollama при переанализе отчёта

### 3. Запуск в Docker

```bash
# Построить и запустить контейнеры
docker-compose up --build

# В другом терминале: инициализировать БД
docker-compose exec backend alembic upgrade head

# Или запустить миграции вручную (они запускаются автоматически при старте)
```

Приложение будет доступно на `http://localhost:8000`

Swagger UI: `http://localhost:8000/docs`

### 3. Локальное развертывание (без Docker)

```bash
# Установить зависимости
pip install -r requirements.txt

# Убедиться, что PostgreSQL запущен
# Отредактировать DATABASE_URL в .env

# Запустить приложение
uvicorn api.main:app --reload

# В другом терминале: запустить тесты
pytest
```

## API Эндпоинты

### Аутентификация

- `POST /api/v1/auth/register` - Регистрация пользователя
- `POST /api/v1/auth/login` - Логин
- `GET /api/v1/auth/users/me` - Профиль текущего пользователя (требует JWT)
- `PATCH /api/v1/auth/users/me/password` - Смена пароля

### Сообщения о НР (Reports)

- `POST /api/v1/reports` - Создать сообщение из текста
- `POST /api/v1/reports/from-form` - Создать из структурированной формы
- `POST /api/v1/reports/extract-from-file` - Извлечь данные из PDF/DOCX
- `GET /api/v1/reports` - Список сообщений (с фильтрами)
- `GET /api/v1/reports/{report_id}` - Детали сообщения
- `GET /api/v1/reports/{report_id}/analysis-status` - Статус анализа
- `PATCH /api/v1/reports/{report_id}/status` - Изменить статус (только specialist)
- `PATCH /api/v1/reports/{report_id}/specialist-review` - Правки специалиста
- `POST /api/v1/reports/{report_id}/finalize` - Финализировать (только specialist)
- `POST /api/v1/reports/{report_id}/reanalyze` - Переанализировать с другой моделью (только specialist)

### Справочник препаратов

- `GET /api/v1/drugs?search=название` - Поиск препаратов

### RAG (База знаний)

- `POST /api/v1/rag/documents` - Загрузить ИМП (только specialist)
- `GET /api/v1/rag/documents` - Список загруженных ИМП
- `DELETE /api/v1/rag/documents/{document_id}` - Удалить ИМП

### Системное

- `GET /health` - Health check

## Примеры использования

### 1. Регистрация и логин

```bash
# Регистрация
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "doctor@example.com",
    "password": "securepassword123",
    "full_name": "Dr. John Smith",
    "role": "reporter"
  }'

# Ответ содержит access_token
```

### 2. Создание сообщения о НР

```bash
curl -X POST http://localhost:8000/api/v1/reports \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "raw_text": "Пациент М., 45 лет, применял Аспирин в дозе 500мг 3 раза в день. На 3-й день приема возникла сильная головная боль и головокружение..."
  }'

# Анализ запустится автоматически с Yandex Cloud API
# Смотрите логи:
# 🔄 Starting analysis for report {id}...
# 💾 Saving case_extraction recommendation
# ✅ All recommendations saved for report {id}
```

### 3. Получение статуса анализа

```bash
curl -X GET http://localhost:8000/api/v1/reports/{report_id}/analysis-status \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. Загрузка ИМП (только для specialist)

```bash
curl -X POST http://localhost:8000/api/v1/rag/documents \
  -H "Authorization: Bearer SPECIALIST_TOKEN" \
  -F "file=@instruction.pdf" \
  -F "drug_name_ru=Аспирин" \
  -F "atc_code=N02BA01"
```

### 5. Переанализ отчёта с другой моделью (только для specialist)

```bash
# Переанализировать с Yandex Cloud API
curl -X POST http://localhost:8000/api/v1/reports/{report_id}/reanalyze \
  -H "Authorization: Bearer SPECIALIST_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "llm_provider": "yandex",
    "llm_model": "gpt-4o-mini"
  }'

# Или с локальным Ollama
curl -X POST http://localhost:8000/api/v1/reports/{report_id}/reanalyze \
  -H "Authorization: Bearer SPECIALIST_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "llm_provider": "ollama",
    "llm_model": "mistral"
  }'
```

**Замечание:** Переанализ перезаписывает предыдущие результаты анализа. Результаты содержат поле `reanalyzed_with` в completeness рекомендации.

## Тестирование

```bash
# Запустить все тесты
pytest

# Запустить конкретный файл
pytest tests/test_auth.py

# Запустить конкретный тест
pytest tests/test_auth.py::test_register

# С покрытием
pytest --cov=api tests/
```

## Структура БД

Основные таблицы:

- `users` - Пользователи (врачи и специалисты)
- `reports` - Сообщения о НР
- `drugs` - Справочник препаратов
- `ai_recommendations` - Рекомендации AI (с типами: case_extraction, ime, naranjo, expectedness, completeness)

## Интеграция с AI сервисами

### Используемые сервисы

- **CaseExtractionService** - Извлечение структурированных данных из текста
- **IMEService** - Проверка клинической значимости по списку EMA IME
- **NaranjoService** - Оценка причинно-следственной связи (алгоритм Наранжо)
- **ExpectednessService** - Оценка предвиденности реакции (с использованием RAG)

### LLM интеграция

По умолчанию используется Yandex Cloud API, но поддерживается также локальный Ollama.

### Логирование

При создании отчёта логи показывают детали анализа с **Yandex Cloud API**:

```
🔧 Initializing LLM: provider=yandex, model=gpt-4o-mini
✅ Yandex Cloud configured: folder=b1gkk3fc...
📝 Creating new report for user 56533bdb...
✅ Report created with ID: 24fb26e9-5f37-42b1-9194...
🔄 Starting analysis for report 24fb26e9-5f37-42b1-9194...
📊 Case extraction: True
💊 Found drug: Аспирин
💾 Saving case_extraction recommendation
💾 Saving ime recommendation
💾 Saving naranjo recommendation
💾 Saving expectedness recommendation
💾 Saving completeness recommendation
✅ All recommendations saved for report 24fb26e9-5f37-42b1-9194
```

**Если анализ не выполняется:**

- Проверьте `YANDEX_CLOUD_API_KEY` и `YANDEX_CLOUD_FOLDER` в `.env`
- Убедитесь что интернет соединение рабочее
- В логах должна быть ошибка подробнее

При переанализе с Ollama:

```
🔄 Reanalyze request for report 24fb26e9-5f37-42b1-9194
   Requested: provider=ollama, model=mistral
🔍 Checking Ollama availability...
✅ Found report 24fb26e9-5f37-42b1-9194, raw_text length: 256 chars
🔧 Creating new LLM client...
✅ Ollama connection verified
✅ New LLM client initialized
🔄 Starting re-analysis with ollama/mistral...
✅ Re-analysis completed successfully
🗑️ Deleting previous recommendations...
✅ Deleted 5 previous recommendations
💾 Saving case_extraction from ollama
...
✅ All new recommendations saved for report 24fb26e9-5f37-42b1-9194
```

**Если переанализ с Ollama не работает:**

```
🔍 Checking Ollama availability...
❌ Ollama connection failed: Connection refused
# Значит Ollama не запущена или недоступна на localhost:11434
```

## Проблемы и вопросы

### 1. Анализ с Yandex Cloud API (по умолчанию)

По умолчанию система использует **Yandex Cloud API**. Убедитесь, что в `.env` установлены:

```env
LLM_PROVIDER=yandex
YANDEX_CLOUD_API_KEY=<ваш-api-ключ>
YANDEX_CLOUD_FOLDER=<ваш-folder-id>
```

Получите учетные данные на https://console.cloud.yandex.com/

### 2. Локальная Ollama для переанализа

Если специалист захочет переанализировать отчёт с локальной моделью Mistral, нужно установить Ollama:

#### Windows (без Docker):

1. **Скачайте Ollama**
   - Перейдите на https://ollama.ai
   - Скачайте инсталлер для Windows

2. **Установите**

   ```bash
   # После установки, Ollama будет доступна как приложение
   ```

3. **Запустите Ollama**

   ```bash
   # Откройте командную строку/PowerShell
   ollama serve

   # Или используйте GUI приложение (скоро появится значок в трее)
   ```

4. **Скачайте модель Mistral**

   ```bash
   # В отдельном терминале
   ollama pull mistral

   # Ответ должен содержать: "pulling model"
   ```

5. **Проверьте доступность**

   ```bash
   curl -X GET http://localhost:11434/api/tags

   # Должен вернуть список доступных моделей
   ```

6. **Используйте в PharmAssist**

   Когда специалист создаёт переанализ с Ollama:

   ```bash
   curl -X POST http://localhost:8000/api/v1/reports/{report_id}/reanalyze \
     -H "Authorization: Bearer SPECIALIST_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "llm_provider": "ollama",
       "llm_model": "mistral"
     }'
   ```

#### Linux/Mac:

```bash
# Установка
curl https://ollama.ai/install.sh | sh

# Запуск
ollama serve

# Скачивание модели
ollama pull mistral

# Проверка
curl http://localhost:11434/api/tags
```

#### Docker:

```bash
# Если вы хотите добавить Ollama в docker-compose позже
docker run -d \
  --name ollama \
  -p 11434:11434 \
  -v ollama:/root/.ollama \
  ollama/ollama:latest

# Скачивание модели в контейнер
docker exec ollama ollama pull mistral
```

### Diagnostics

Если переанализ с Ollama не работает:

1. **Проверьте, запущена ли Ollama**

   ```bash
   curl -I http://localhost:11434/api/tags

   # Должен вернуть: HTTP/1.1 200 OK
   ```

2. **Проверьте логи PharmAssist**

   ```
   ❌ Ollama connection failed: Connection refused
   # Значит, Ollama не запущена на 11434
   ```

3. **Перезагрузите Ollama**
   ```bash
   # Закройте предыдущий процесс
   # Запустите снова
   ollama serve
   ```

### CORS ошибки

По умолчанию CORS разрешен со всех источников (`allow_origins=["*"]`). Для production отредактируй в `api/main.py`:

```python
allow_origins=["https://yourdomain.com"]  # Указать конкретный домен
```

### 2. Асинхронный анализ

Сейчас анализ запускается синхронно при создании отчета. Для production рекомендуется использовать Celery для асинхронной обработки:

```python
# Пример с Celery (не реализовано, но легко добавить)
@app.post("/reports")
async def create_report(...):
    report = Report(...)
    session.add(report)
    await session.commit()

    # Запустить в фоне
    analyze_report_task.delay(report.id)

    return {"id": report.id, "status": "submitted"}
```

### 3. Миграции БД

Используется Alembic. Миграции находятся в `models/migrations/`.

Для создания новой миграции:

```bash
alembic revision --autogenerate -m "Описание изменений"
```

## Развертывание на production

1. Установи production WSGI сервер (Gunicorn):

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 api.main:app
```

2. Отредактируй `SECRET_KEY` в `.env`

3. Используй PostgreSQL вместо SQLite

4. Включи HTTPS и ограничь CORS

5. Используй Celery для асинхронных задач

## Лицензия

Не указана
