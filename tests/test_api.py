"""
Tests — run with:  pytest tests/ -v
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings

# Use an in-memory SQLite database for tests (no Supabase needed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(bind=test_engine, expire_on_commit=False)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ── Helpers ──────────────────────────────────────────────────────────

STUDENT_DATA = {
    "first_name": "Test",
    "last_name": "User",
    "email": "test@student.edu.zm",
    "student_number": "MUL2024001",
    "password": "testpass1",
    "program": "ICT",
    "year_of_study": 2,
}

async def register_and_verify(client: AsyncClient) -> dict:
    """Register a student, manually verify email, return login tokens."""
    await client.post("/api/v1/auth/register", json=STUDENT_DATA)

    # Manually mark email as verified in DB
    async with TestSessionLocal() as db:
        from sqlalchemy import select, update
        from app.models.student import Student
        await db.execute(
            update(Student)
            .where(Student.email == STUDENT_DATA["email"])
            .values(email_verified=True, is_verified=True, email_verification_token=None)
        )
        await db.commit()

    # Login
    response = await client.post("/api/v1/auth/login", json={
        "email": STUDENT_DATA["email"],
        "password": STUDENT_DATA["password"],
    })
    return response.json()


# ── Auth Tests ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    response = await client.post("/api/v1/auth/register", json=STUDENT_DATA)
    assert response.status_code == 201
    assert "Registration successful" in response.json()["message"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    await client.post("/api/v1/auth/register", json=STUDENT_DATA)
    response = await client.post("/api/v1/auth/register", json=STUDENT_DATA)
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_before_verify(client: AsyncClient):
    await client.post("/api/v1/auth/register", json=STUDENT_DATA)
    response = await client.post("/api/v1/auth/login", json={
        "email": STUDENT_DATA["email"],
        "password": STUDENT_DATA["password"],
    })
    assert response.status_code == 403
    assert "verify" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    tokens = await register_and_verify(client)
    assert "access_token" in tokens
    assert "refresh_token" in tokens


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient):
    tokens = await register_and_verify(client)
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == STUDENT_DATA["email"]


# ── Group Tests ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_group(client: AsyncClient):
    tokens = await register_and_verify(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    response = await client.post("/api/v1/groups/", json={
        "group_name": "ICT312 Study Squad",
        "description": "Weekly revision",
        "privacy_status": "public",
        "max_members": 20,
    }, headers=headers)

    assert response.status_code == 201
    data = response.json()
    assert data["group_name"] == "ICT312 Study Squad"
    assert data["member_count"] == 1   # creator auto-joined
    assert data["is_member"] is True


@pytest.mark.asyncio
async def test_list_groups(client: AsyncClient):
    tokens = await register_and_verify(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    await client.post("/api/v1/groups/", json={
        "group_name": "Group One",
        "privacy_status": "public",
    }, headers=headers)

    response = await client.get("/api/v1/groups/", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
