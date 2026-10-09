import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_supplier_registration_requires_operator_approval(client: AsyncClient, seeded_entities: dict):
    registration = await client.post(
        "/api/v1/auth/supplier-registration",
        json={
            "legal_name": "Durban Concrete Exchange",
            "contact_name": "Ayanda Khumalo",
            "email": "ayanda@durbanconcrete.co.za",
            "phone": "+27820000003",
            "password": "a-secure-password",
            "categories": ["concrete"],
        },
    )
    assert registration.status_code == 201
    supplier_id = registration.json()["organisation_id"]

    denied = await client.post(
        f"/api/v1/suppliers/{supplier_id}/approve",
        json={"reason": "Should not be contractor-approved"},
        headers={"Authorization": f"Bearer {seeded_entities['contractor_token']}"},
    )
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "OPERATOR_REQUIRED"

    queue = await client.get(
        "/api/v1/suppliers/review",
        headers={"Authorization": f"Bearer {seeded_entities['operator_token']}"},
    )
    assert queue.status_code == 200
    assert any(item["organisation_id"] == supplier_id for item in queue.json())

    approved = await client.post(
        f"/api/v1/suppliers/{supplier_id}/approve",
        json={"reason": "Verified Durban concrete supplier for pilot."},
        headers={"Authorization": f"Bearer {seeded_entities['operator_token']}"},
    )
    assert approved.status_code == 200
    assert approved.json()["approval_status"] == "approved"
    assert approved.json()["active"] is True


@pytest.mark.asyncio
async def test_supplier_cannot_self_activate_profile(client: AsyncClient, seeded_entities: dict):
    response = await client.post(
        "/api/v1/suppliers/profile",
        json={
            "categories": ["concrete"],
            "service_regions": ["Durban", "KwaZulu-Natal"],
            "preferred_contact_method": "email",
            "active": True,
        },
        headers={"Authorization": f"Bearer {seeded_entities['supplier1_token']}"},
    )
    assert response.status_code == 200
    assert response.json()["active"] is True
    assert response.json()["approval_status"] == "approved"