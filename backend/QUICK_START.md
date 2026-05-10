# 🚀 Быстрый старт Backend

## Первый запуск (требует сборку)

```bash
# Перейти в папку
cd pharma_backend

# Убедиться что .env файл создан
# (если его нет, скопируй .env.example)
ls .env

# Очистить старые контейнеры (если были)
docker compose down -v

# Сборка и запуск
docker compose up --build

# Ждем логов вроде:
# pharma-backend  | INFO:     Application startup complete
```

**Это займет ~3-5 минут** (установка зависимостей)

---

## Последующие запуски (БЕЗ пересборки!)

```bash
# Просто запусти контейнеры
docker compose up

# Это займет ~5 секунд! ⚡
```

### Код обновляется автоматически!

Благодаря volume в docker-compose.yaml:
- Изменения в `api/`, `tests/`, `auth.py`, `db.py`, `api_schemas.py` **моментально отражаются** в контейнере
- Uvicorn будет перезагружать приложение автоматически (благодаря `--reload`)

### Пример редактирования:

```python
# 1. Отредактируй файл (например, api/routes/auth.py)
# 2. Сохрани (Ctrl+S)
# 3. Посмотри логи:
docker compose logs -f backend

# 4. Увидишь:
# pharma-backend  | INFO:     Application startup complete
# (приложение перезагрузилось автоматически)
```

---

## Когда нужна пересборка?

Пересобирать контейнер нужно ТОЛЬКО если:

1. ✅ **Добавил новый пакет в requirements.txt**
   ```bash
   docker compose up --build
   ```

2. ✅ **Изменил Dockerfile**
   ```bash
   docker compose up --build
   ```

3. ✅ **Хочешь очистить все с нуля**
   ```bash
   docker compose down -v
   docker compose up --build
   ```

---

## Полезные команды

### Посмотреть логи
```bash
# Все сервисы
docker compose logs -f

# Только backend
docker compose logs -f backend

# Только БД
docker compose logs -f db
```

### Перезапустить приложение
```bash
# Остановить контейнеры (не удаляя данные)
docker compose stop

# Запустить опять
docker compose start
```

### Полная очистка
```bash
# Удалить все контейнеры и volumes (БД будет удалена!)
docker compose down -v

# Запустить с нуля
docker compose up --build
```

### Запустить команду внутри контейнера
```bash
# Запустить pytest
docker compose exec backend pytest -v

# Запустить python команду
docker compose exec backend python -c "import fastapi; print(fastapi.__version__)"

# Зайти в shell
docker compose exec backend bash
```

---

## Проверка работы

```bash
# Health check
curl http://localhost:8000/health

# Swagger UI
# Открой в браузере: http://localhost:8000/docs
```

---

## Проблемы?

### Port 5432 занят
```bash
# Найди процесс на port 5432
lsof -i :5432

# Убей процесс (на Windows: taskkill /PID <PID> /F)
kill -9 <PID>
```

### Хочу изменить port
В docker-compose.yaml измени:
```yaml
ports:
  - "8000:8000"  # левое число = port на хосте
  - "5432:5432"  # левое число = port на хосте
```

### Логи говорят об ошибке
```bash
# Посмотри полные логи
docker compose logs

# Может быть нужна пересборка
docker compose up --build
```

---

## Summary

| Действие | Команда | Время |
|----------|---------|-------|
| Первый запуск | `docker compose up --build` | ~3-5 мин |
| Обычный запуск | `docker compose up` | ~5 сек |
| Добавил пакет | `docker compose up --build` | ~1-2 мин |
| Посмотреть логи | `docker compose logs -f` | - |
| Остановить | `docker compose stop` | - |
| Удалить все | `docker compose down -v` | - |

**Наслаждайся быстрой разработкой! 🚀**
