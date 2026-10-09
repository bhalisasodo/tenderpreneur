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
async def test_login_rejects_invalid_password(client: AsyncClient, seeded_entities: dict):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "estimator@amandla.co.za", "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_supplier_registration_starts_pending_for_durban(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/supplier-registration",
        json={
            "legal_name": "Durban Coastal Aggregates",
            "trading_name": "Coastal Aggregates",
            "contact_name": "Thandi Mkhize",
            "email": "thandi@coastalaggregates.co.za",
            "phone": "+27310000000",
            "password": "a-secure-password",
            "categories": ["concrete"],
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "pending_approval"

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "thandi@coastalaggregates.co.za", "password": "a-secure-password"},
    )
    assert login.status_code == 403
    assert login.json()["detail"]["code"] == "SUPPLIER_PENDING_APPROVAL"


@pytest.mark.asyncio
async def test_supplier_registration_rejects_duplicate_email(client: AsyncClient, seeded_entities: dict):
    response = await client.post(
        "/api/v1/auth/supplier-registration",
        json={
            "legal_name": "Duplicate Supplier",
            "contact_name": "Duplicate Contact",
            "email": "estimator@amandla.co.za",
            "phone": "+27310000001",
            "password": "a-secure-password",
            "categories": ["concrete"],
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "EMAIL_ALREADY_REGISTERED"


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
