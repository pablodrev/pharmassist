# 🚀 Запуск PharmAssist Backend

## Требования

- Docker и Docker Compose
- ИЛИ Python 3.11+ и PostgreSQL

## Вариант 1: Docker (рекомендуется)

### Шаг 1: Подготовка

```bash
cd pharma_backend

# Скопировать конфиг переменных окружения
cp .env.example .env

# По необходимости отредактировать .env
# (обычно значения по умолчанию подходят для локальной разработки)
```

### Шаг 2: Запуск

**На Windows:**
```bash
run-docker.bat
```

**На Linux/Mac:**
```bash
bash run-docker.sh
```

**Или вручную:**
```bash
docker-compose up --build
```

### Шаг 3: Проверка

Когда контейнеры запустятся:

- API будет доступен: **http://localhost:8000**
- Swagger UI: **http://localhost:8000/docs**
- Health check: **http://localhost:8000/health**

## Вариант 2: Локальное развертывание

### Шаг 1: Установка зависимостей

```bash
# Убедиться, что Python 3.11+ установлен
python --version

# Установить зависимости
pip install -r requirements.txt
```

### Шаг 2: Подготовка БД

Убедиться, что PostgreSQL запущен и доступен. Отредактировать `.env`:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/pharmadb
```

### Шаг 3: Запуск приложения

```bash
uvicorn api.main:app --reload
```

Приложение будет доступно на **http://localhost:8000**

## Запуск тестов

```bash
# Все тесты
pytest

# С покрытием
pytest --cov=api tests/

# Конкретный файл
pytest tests/test_auth.py -v
```

## Проверка API

### 1. Health Check

```bash
curl http://localhost:8000/health
```

Ожидается ответ:
```json
{"status": "ok"}
```

### 2. Регистрация пользователя

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "doctor@example.com",
    "password": "securepassword123",
    "full_name": "Dr. John Smith",
    "role": "reporter"
  }'
```

Ответ содержит токен:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "...",
    "email": "doctor@example.com",
    "full_name": "Dr. John Smith",
    "role": "reporter"
  }
}
```

### 3. Создание сообщения о НР

```bash
curl -X POST http://localhost:8000/api/v1/reports \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "raw_text": "Пациент М., 45 лет, применял Аспирин 500мг 3 раза в день. На 3-й день возникла сильная головная боль..."
  }'
```

Ответ:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "submitted"
}
```

### 4. Проверка статуса анализа

```bash
curl -X GET http://localhost:8000/api/v1/reports/550e8400-e29b-41d4-a716-446655440000/analysis-status \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Swagger UI

Откройте **http://localhost:8000/docs** в браузере. Здесь можно:
- Просмотреть все эндпоинты
- Получить токен и его использовать для тестирования
- Отправлять запросы через web-интерфейс

## Решение проблем

### Ошибка "Port 5444 is already in use"

Измени порт в `.env` или останови другой PostgreSQL:

```bash
# Linux/Mac
lsof -i :5444
kill -9 <PID>

# Windows
netstat -ano | findstr :5444
taskkill /PID <PID> /F
```

### Ошибка подключения к БД

Проверить, что PostgreSQL контейнер запустился:

```bash
docker-compose ps
```

Убедиться, что в `.env` правильный `DATABASE_URL`

### LLM не доступна

Если получаешь ошибку про Ollama, убедись что:
1. Ollama запущена (`ollama serve`)
2. Модель загружена (`ollama pull mistral`)
3. Порт 11434 доступен

## Структура эндпоинтов

```
POST   /api/v1/auth/register              Регистрация
POST   /api/v1/auth/login                 Логин
GET    /api/v1/auth/users/me              Профиль (JWT обязателен)
PATCH  /api/v1/auth/users/me/password     Смена пароля

POST   /api/v1/reports                    Создать отчет из текста
POST   /api/v1/reports/from-form          Создать из формы
POST   /api/v1/reports/extract-from-file  Извлечь из PDF/DOCX
GET    /api/v1/reports                    Список отчетов
GET    /api/v1/reports/{id}               Детали отчета
GET    /api/v1/reports/{id}/analysis-status  Статус анализа
PATCH  /api/v1/reports/{id}/status        Изменить статус (только specialist)
PATCH  /api/v1/reports/{id}/specialist-review  Комментарии специалиста
POST   /api/v1/reports/{id}/finalize      Финализировать

GET    /api/v1/drugs                      Поиск препаратов

POST   /api/v1/rag/documents              Загрузить ИМП (specialist)
GET    /api/v1/rag/documents              Список ИМП
DELETE /api/v1/rag/documents/{id}         Удалить ИМП

GET    /health                            Health check
```

## Следующие шаги

Когда backend запущен:
1. Тестируй эндпоинты в Swagger UI (http://localhost:8000/docs)
2. Получи токен и используй его для тестирования
3. Интегрируй с фронтенд на React

## Поддержка

При возникновении ошибок:
1. Проверь логи контейнера: `docker-compose logs backend`
2. Посмотри на примеры в `API_README.md`
3. Запусти тесты: `pytest -v`
