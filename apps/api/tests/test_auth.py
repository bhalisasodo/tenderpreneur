import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, seeded_entities: dict):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "estimator@amandla.co.za", "password": "password"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "estimator@amandla.co.za"
    assert data["organisation"]["type"] == "contractor"


@pytest.mark.asyncio
async def test_login_invalid_email(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@domain.co.za", "password": "password"},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_get_current_user_profile(client: AsyncClient, seeded_entities: dict):
    token = seeded_entities["contractor_token"]
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == "estimator@amandla.co.za"
    assert data["organisation"]["legal_name"] == "Amandla Civils (Pty) Ltd"


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient):
    response = await client.get("/api/v1/boqs")
    assert response.status_code == 401
