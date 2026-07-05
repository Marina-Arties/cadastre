import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app
from app.models.user import User

TEST_DB_URL = "sqlite+aiosqlite:///file:test_db?mode=memory&cache=shared&uri=true"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    async_session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(test_engine, db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(client):
    resp = await client.post("/api/auth/register", json={
        "email": "test@test.com",
        "password": "Test1234",
        "nickname": "testuser",
    })
    data = resp.json()
    return {"Authorization": f"Bearer {data['access_token']}"}


@pytest_asyncio.fixture
async def admin_headers(client, db_session):
    resp = await client.post("/api/auth/register", json={
        "email": "admintest@test.com",
        "password": "Admin1234",
        "nickname": "admintest",
    })
    data = resp.json()
    user_id = data["user"]["id"]
    result = await db_session.execute(select(User).where(User.id == user_id))
    admin = result.scalar_one()
    admin.is_admin = True
    await db_session.commit()
    return {"Authorization": f"Bearer {data['access_token']}"}
