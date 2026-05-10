"""Test configuration and fixtures."""

# ------------------------------------------------------------------
# Teach SQLite's DDL compiler to render PostgreSQL's JSONB type as TEXT.
# Python-level JSON encoding/decoding still happens via the JSONB type's
# bind_processor / result_processor (inherited from SQLAlchemy's JSON type).
# This must be imported before SQLModel/models are imported.
# ------------------------------------------------------------------
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler  # noqa: E402


def _visit_JSONB(self, type_, **kw):  # noqa: N802
    return "TEXT"


SQLiteTypeCompiler.visit_JSONB = _visit_JSONB
# ------------------------------------------------------------------

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
import os

from api.main import app
from db import get_session
from auth import create_access_token
from models.schemas_db import Drug
from datetime import timedelta
from uuid import uuid4


# Create test database URL
TEST_DB_URL = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")

# Create async engine for tests
test_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    echo=False
)

test_session_maker = sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def override_get_session():
    """Override database session for tests."""
    async with test_session_maker() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def test_db():
    """Create test database."""
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest.fixture(scope="function")
def client(test_db):
    """Create test client."""
    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def reporter_token():
    """Create reporter JWT token."""
    user_id = str(uuid4())
    token = create_access_token(
        data={"sub": user_id, "role": "reporter"},
        expires_delta=timedelta(minutes=30)
    )
    return token, user_id


@pytest.fixture
def specialist_token():
    """Create specialist JWT token."""
    user_id = str(uuid4())
    token = create_access_token(
        data={"sub": user_id, "role": "specialist"},
        expires_delta=timedelta(minutes=30)
    )
    return token, user_id


@pytest_asyncio.fixture
async def drugs_in_db(test_db):
    """Insert a set of test drugs directly into the test database."""
    async with test_session_maker() as session:
        entries = [
            Drug(name_ru="Аспирин", name_en="Aspirin", atc_code="B01AC06"),
            Drug(name_ru="Ибупрофен", name_en="Ibuprofen", atc_code="M01AE01"),
            Drug(name_ru="Парацетамол", name_en="Paracetamol", atc_code="N02BE01"),
        ]
        for drug in entries:
            session.add(drug)
        await session.commit()
    return entries
