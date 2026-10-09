import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_supplier_approval_requires_platform_operator(
    client: AsyncClient,
    seeded_entities: dict,
    pending_supplier: dict,
):
    supplier_id = pending_supplier["organisation"].id
    contractor_headers = {"Authorization": f"Bearer {seeded_entities['contractor_token']}"}
    operator_headers = {"Authorization": f"Bearer {seeded_entities['operator_token']}"}

    denied = await client.post(
        f"/api/v1/suppliers/{supplier_id}/approve",
        json={"reason": "Should not be contractor-approved"},
        headers=contractor_headers,
    )
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "OPERATOR_REQUIRED"

    queue = await client.get("/api/v1/suppliers/review", headers=operator_headers)
    assert queue.status_code == 200
    assert any(item["organisation_id"] == supplier_id for item in queue.json())

    approved = await client.post(
        f"/api/v1/suppliers/{supplier_id}/approve",
        json={"reason": "Verified supplier for the controlled pilot."},
        headers=operator_headers,
    )
    assert approved.status_code == 200
    assert approved.json()["approval_status"] == "approved"
    assert approved.json()["active"] is True


@pytest.mark.asyncio
async def test_supplier_cannot_self_activate_profile(client: AsyncClient, pending_supplier: dict):
    response = await client.post(
        "/api/v1/suppliers/profile",
        json={
            "categories": ["concrete"],
            "service_regions": ["Durban", "KwaZulu-Natal"],
            "preferred_contact_method": "email",
            "active": True,
        },
        headers={"Authorization": f"Bearer {pending_supplier['token']}"},
    )
    assert response.status_code == 200
    assert response.json()["active"] is False
    assert response.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_approved_supplier_profile_update_preserves_activation(
    client: AsyncClient, seeded_entities: dict
):
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
    assert response.json()["status"] == "approved"
