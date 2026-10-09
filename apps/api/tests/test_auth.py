import base64
import hashlib

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password


def test_password_verification_supports_existing_hash_formats():
    password = "previously-stored-password"
    salt = b"legacy-password-salt"
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 1_000)
    legacy_hash = "$".join(
        [
            "pbkdf2_sha256",
            "1000",
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(digest).decode("ascii"),
        ]
    )

    assert verify_password(password, legacy_hash)
    assert verify_password(password, hash_password(password))
    assert not verify_password("wrong-password", legacy_hash)


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
async def test_login_rejects_accounts_without_a_password_hash(client: AsyncClient, seeded_entities: dict):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "sales@durbanhub.co.za", "password": "password"},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_deactivated_user_token_is_rejected(
    client: AsyncClient,
    seeded_entities: dict,
    db_session: AsyncSession,
):
    user = seeded_entities["contractor_user"]
    user.is_active = False
    await db_session.commit()

    response = await client.get(
        "/api/v1/boqs",
        headers={"Authorization": f"Bearer {seeded_entities['contractor_token']}"},
    )
    assert response.status_code == 401


def registration_payload(**overrides):
    payload = {
        "organisation_type": "contractor",
        "legal_name": "Example Infrastructure (Pty) Ltd",
        "email": "ADMIN@EXAMPLE.CO.ZA",
        "region": "KwaZulu-Natal",
        "name": "Example Administrator",
        "password": "a-secure-password-2026",
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_contractor_registration_creates_workspace_and_signs_in(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json=registration_payload(trading_name="Example Infrastructure"),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["access_token"]
    assert data["user"]["email"] == "admin@example.co.za"
    assert data["user"]["role"] == "admin"
    assert data["organisation"]["type"] == "contractor"
    assert data["organisation"]["legal_name"] == "Example Infrastructure (Pty) Ltd"
    assert data["supplier_approval_status"] is None

    profile = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert profile.status_code == 200
    assert profile.json()["user"]["email"] == "admin@example.co.za"


@pytest.mark.asyncio
async def test_supplier_registration_creates_pending_review_application(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json=registration_payload(
            organisation_type="supplier",
            email="supplier@example.co.za",
            supplier_categories=["building-materials"],
            supplier_service_regions=["KwaZulu-Natal"],
        ),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["organisation"]["type"] == "supplier"
    assert data["supplier_approval_status"] == "pending"

    profile = await client.get(
        "/api/v1/suppliers/profile",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert profile.status_code == 200
    assert profile.json()["status"] == "pending"
    assert profile.json()["active"] is False
    assert profile.json()["categories"] == ["building-materials"]


@pytest.mark.asyncio
async def test_registration_rejects_duplicate_email_and_weak_password(
    client: AsyncClient, seeded_entities: dict
):
    duplicate = await client.post(
        "/api/v1/auth/register",
        json=registration_payload(email="ESTIMATOR@AMANDLA.CO.ZA"),
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "ACCOUNT_ALREADY_EXISTS"

    weak_password = await client.post(
        "/api/v1/auth/register",
        json=registration_payload(email="new@example.co.za", password="short"),
    )
    assert weak_password.status_code == 422


@pytest.mark.asyncio
async def test_supplier_registration_requires_matching_profile_details(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json=registration_payload(
            organisation_type="supplier",
            email="supplier@example.co.za",
        ),
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "SUPPLIER_PROFILE_REQUIRED"


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ["/auth/register-supplier", "/auth/supplier-registration"])
async def test_legacy_supplier_registration_routes_remain_disabled(client: AsyncClient, route: str):
    response = await client.post(f"/api/v1{route}", json={})
    assert response.status_code == 404


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
