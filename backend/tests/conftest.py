import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch

# Pre-import all models so SQLAlchemy registry is populated correctly
from app.models.user import User
from app.models.workspace import Workspace
from app.models.chat import ChatSession, Message
from app.models.audit import AuditLog
from app.models.integration import Integration
from app.models.document import IndexedDocument

# Force SQLite for tests BEFORE importing anything that might initialize the DB with Postgres
with patch("app.core.config.Settings.SQLALCHEMY_DATABASE_URI", "sqlite+aiosqlite:///:memory:"):
    from app.main import app
    from app.db.session import engine
    from app.db.base_class import Base

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
