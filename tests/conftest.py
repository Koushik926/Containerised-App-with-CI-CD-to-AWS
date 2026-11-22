import asyncio
import uuid
from collections.abc import AsyncGenerator, Generator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app

settings = get_settings()

test_engine = create_async_engine(
    str(settings.database_url),
    echo=False,
    pool_pre_ping=True,
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_database() -> AsyncGenerator[None, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def unique_email() -> str:
    return f"test-{uuid.uuid4().hex[:8]}@example.com"


@pytest.fixture
def test_user_data(unique_email: str) -> dict[str, str]:
    return {
        "email": unique_email,
        "password": "testpassword123",
        "full_name": "Test User",
    }


@pytest.fixture
def test_user_data_2() -> dict[str, str]:
    return {
        "email": f"test2-{uuid.uuid4().hex[:8]}@example.com",
        "password": "testpassword456",
        "full_name": "Test User 2",
    }


@pytest.fixture
async def registered_user(client: AsyncClient, test_user_data: dict[str, str]) -> dict[str, str]:
    response = await client.post("/api/v1/auth/register", json=test_user_data)
    assert response.status_code == 201
    return test_user_data


@pytest.fixture
async def auth_headers(client: AsyncClient, registered_user: dict[str, str]) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def registered_user_2(
    client: AsyncClient, test_user_data_2: dict[str, str]
) -> dict[str, str]:
    response = await client.post("/api/v1/auth/register", json=test_user_data_2)
    assert response.status_code == 201
    return test_user_data_2


@pytest.fixture
async def auth_headers_user2(
    client: AsyncClient, registered_user_2: dict[str, str]
) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": registered_user_2["email"],
            "password": registered_user_2["password"],
        },
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
