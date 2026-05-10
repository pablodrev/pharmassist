import os
from sqlmodel import create_engine, SQLModel, Session
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = os.getenv("POSTGRES_PORT")
DB_NAME = os.getenv("POSTGRES_DB")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
print(f"Connecting to {DATABASE_URL}")  # для отладки, не показывайте пароль в проде

# Создаём engine (sync версия для простоты)
engine = create_engine(DATABASE_URL, echo=True)  # echo=True для логов

def create_tables():
    """Создать все таблицы в БД на основе моделей"""
    SQLModel.metadata.create_all(engine)

if __name__ == "__main__":
    create_tables()
    print("Tables created successfully")