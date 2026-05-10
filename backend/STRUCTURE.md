# 📋 Структура нового FastAPI backend

## Созданные файлы

### Основное приложение
- **`api/main.py`** - FastAPI приложение с маршрутами и CORS
- **`api/routes/`** - Маршруты приложения:
  - `auth.py` - Аутентификация (register, login, users/me, password change)
  - `reports.py` - Сообщения о НР (CRUD, анализ, статусы)
  - `drugs.py` - Поиск препаратов
  - `rag.py` - Управление базой знаний (ИМП)

### Конфигурация и утилиты
- **`db.py`** - Конфигурация БД (PostgreSQL + asyncpg)
- **`auth.py`** - JWT аутентификация и хеширование паролей
- **`api_schemas.py`** - Pydantic модели для API запросов/ответов

### Docker и развертывание
- **`Dockerfile`** - Образ контейнера для backend
- **`docker-compose.yaml`** - Оркестрация (backend + PostgreSQL)
- **`.env.example`** - Пример переменных окружения
- **`run-docker.sh`** / **`run-docker.bat`** - Скрипты для запуска

### Тесты
- **`tests/`** - Тестовое покрытие:
  - `conftest.py` - Фикстуры и конфигурация (база данных, клиент)
  - `test_health.py` - Тесты health check
  - `test_auth.py` - Тесты аутентификации (register, login, password change)
  - `test_reports.py` - Тесты создания и управления отчетами
- **`pytest.ini`** - Конфигурация pytest

### Документация
- **`API_README.md`** - Полная документация API с примерами
- **`STARTUP.md`** - Инструкции по запуску (Docker и локально)

## Интеграция с существующим кодом

Используются существующие сервисы:
- `services/orchestrator.py` - Оркестратор анализа
- `services/case_extraction.py` - Извлечение данных
- `services/ime_service.py` - Проверка клинической значимости
- `services/naranjo_service.py` - Оценка причинности
- `services/expectedness_service.py` - Оценка предвиденности

## Ключевые возможности

### Аутентификация
- ✅ JWT токены
- ✅ Хеширование паролей (bcrypt)
- ✅ Роли (reporter, specialist)
- ✅ Защита эндпоинтов

### Сообщения о НР (Reports)
- ✅ Создание из текста
- ✅ Создание из структурированной формы
- ✅ Извлечение из PDF/DOCX
- ✅ AI анализ (интеграция с сервисами)
- ✅ Фильтрация (по статусу, дате, тяжести)
- ✅ Правки специалиста

### Управление БЗ (RAG)
- ✅ Загрузка ИМП (PDF/DOCX)
- ✅ Индексирование в RAG
- ✅ Список загруженных ИМП
- ✅ Удаление документов

### Справочник
- ✅ Поиск препаратов по названию

## Использование

### Быстрый старт (Docker)
```bash
docker-compose up --build
# Приложение на http://localhost:8000
# Swagger UI на http://localhost:8000/docs
```

### Локально
```bash
pip install -r requirements.txt
uvicorn api.main:app --reload
```

### Тесты
```bash
pytest
pytest --cov=api tests/
```

## Примечания

### Архитектура
- Асинхронный код (async/await)
- SQLAlchemy ORM с asyncpg
- Pydantic для валидации
- JWT для аутентификации

### Упрощения для разработки
- AI анализ запускается синхронно при создании отчета
- CORS разрешен со всех источников (меняется в production)
- SQLite для тестов, PostgreSQL для production
- Простой RAG без сложной оптимизации

### Что нужно улучшить
- [ ] Асинхронные задачи (Celery) для AI анализа
- [ ] Кэширование результатов
- [ ] WebSocket для real-time обновлений статуса
- [ ] Rate limiting
- [ ] Логирование в файл
- [ ] Миграции (Alembic)

## Файлы для удаления/переместить

После перехода на FastAPI можно удалить старый Streamlit код:
- `app/main.py` (старый Streamlit)
- `app/components.py`

Или оставить для параллельной разработки.

## Контрольный список перед production

- [ ] Установить SECRET_KEY в `.env`
- [ ] Отредактировать CORS (allow_origins)
- [ ] Добавить логирование
- [ ] Настроить миграции БД
- [ ] Добавить rate limiting
- [ ] Включить HTTPS
- [ ] Использовать Gunicorn вместо uvicorn
- [ ] Настроить Celery для асинхронных задач
- [ ] Добавить мониторинг ошибок (Sentry)
