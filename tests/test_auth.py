import uuid

import pytest
from httpx import AsyncClient


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
