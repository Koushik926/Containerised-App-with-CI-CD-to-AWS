import uuid
from typing import TYPE_CHECKING

import pytest
from httpx import AsyncClient

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def unique_email() -> str:
    return f"test-{uuid.uuid4().hex[:8]}@example.com"


class TestRegister:
    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient) -> None:
        email = unique_email()
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "securepassword123",
                "full_name": "New User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == email
        assert data["full_name"] == "New User"
        assert data["is_active"] is True
        assert "id" in data
        assert "hashed_password" not in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient) -> None:
        email = unique_email()
        user_data = {
            "email": email,
            "password": "testpassword123",
            "full_name": "Test User",
        }
        await client.post("/api/v1/auth/register", json=user_data)

        response = await client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 400
        assert response.json()["detail"] == "Email already registered"

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "securepassword123",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_short_password(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email(),
                "password": "short",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_without_full_name(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email(),
                "password": "securepassword123",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["full_name"] is None


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient) -> None:
        email = unique_email()
        password = "testpassword123"
        await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": "Test"},
        )

        response = await client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": password},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient) -> None:
        email = unique_email()
        await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpassword123", "full_name": "Test"},
        )

        response = await client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Incorrect email or password"

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "nonexistent@example.com", "password": "anypassword"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_json_success(self, client: AsyncClient) -> None:
        email = unique_email()
        password = "testpassword123"
        await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": "Test"},
        )

        response = await client.post(
            "/api/v1/auth/login/json",
            json={"email": email, "password": password},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    @pytest.mark.asyncio
    async def test_login_json_wrong_password(self, client: AsyncClient) -> None:
        email = unique_email()
        await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpassword123", "full_name": "Test"},
        )

        response = await client.post(
            "/api/v1/auth/login/json",
            json={"email": email, "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Incorrect email or password"


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_get_me_success(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        registered_user: dict[str, str],
    ) -> None:
        response = await client.get("/api/v1/users/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == registered_user["email"]
        assert data["full_name"] == registered_user["full_name"]

    @pytest.mark.asyncio
    async def test_get_me_no_token(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_invalid_token(self, client: AsyncClient) -> None:
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_expired_token(self, client: AsyncClient) -> None:
        expired_token = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxMDAwMDAwMDAwfQ.invalid"
        )
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_nonexistent_user_id(self, client: AsyncClient) -> None:
        from app.core.security import create_access_token

        token = create_access_token(subject="99999")
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_non_integer_subject(self, client: AsyncClient) -> None:
        from app.core.security import create_access_token

        token = create_access_token(subject="not-an-integer")
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_inactive_user(
        self, client: AsyncClient, db_session: "AsyncSession"
    ) -> None:
        from app.core.security import create_access_token
        from app.schemas.user import UserCreate
        from app.services.user import create_user

        user_in = UserCreate(
            email="inactive-user@example.com",
            password="testpassword123",
            full_name="Inactive User",
        )
        user = await create_user(db_session, user_in)
        user.is_active = False
        await db_session.commit()

        token = create_access_token(subject=str(user.id))
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Inactive user"
