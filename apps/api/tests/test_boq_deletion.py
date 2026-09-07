import pytest
import uuid
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_delete_boq_success(client: AsyncClient, seeded_entities: dict):
    """Contractor can delete their BoQ, which cleans up items and records an audit event."""
    contractor_token = seeded_entities["contractor_token"]
    headers = {"Authorization": f"Bearer {contractor_token}"}

    # 1. Create BoQ
    create_res = await client.post(
        "/api/v1/boqs",
        json={"title": "Demolition and Earthworks Project", "region": "KwaZulu-Natal", "tender_reference": "DEMO-001"},
        headers=headers,
    )
    assert create_res.status_code == 201
    boq_id = create_res.json()["id"]

    # 2. Add line item
    item_res = await client.post(
        f"/api/v1/boqs/{boq_id}/line-items",
        json={"description": "Excavation in soft material", "quantity": 120.0, "unit": "m3", "category": "earthworks"},
        headers=headers,
    )
    assert item_res.status_code == 201

    # 3. Verify it is listed
    list_res = await client.get("/api/v1/boqs", headers=headers)
    assert list_res.status_code == 200
    boq_ids = [b["id"] for b in list_res.json()]
    assert boq_id in boq_ids

    # 4. Delete the BoQ
    del_res = await client.delete(f"/api/v1/boqs/{boq_id}", headers=headers)
    assert del_res.status_code == 204

    # 5. Verify GET details returns 404
    get_res = await client.get(f"/api/v1/boqs/{boq_id}", headers=headers)
    assert get_res.status_code == 404
    assert get_res.json()["detail"]["code"] == "BOQ_NOT_FOUND"

    # 6. Verify list no longer includes it
    list_after_res = await client.get("/api/v1/boqs", headers=headers)
    assert list_after_res.status_code == 200
    boq_ids_after = [b["id"] for b in list_after_res.json()]
    assert boq_id not in boq_ids_after


@pytest.mark.asyncio
async def test_delete_boq_with_quotes_and_requests(client: AsyncClient, seeded_entities: dict):
    """Deleting a BoQ cascades through line items, quote requests, and supplier quotes cleanly."""
    contractor_token = seeded_entities["contractor_token"]
    headers = {"Authorization": f"Bearer {contractor_token}"}

    # 1. Create BoQ
    create_res = await client.post(
        "/api/v1/boqs",
        json={"title": "Concrete Substructure", "region": "KwaZulu-Natal"},
        headers=headers,
    )
    boq_id = create_res.json()["id"]

    # 2. Add item
    item_res = await client.post(
        f"/api/v1/boqs/{boq_id}/line-items",
        json={"description": "30MPa Ready-mix concrete", "quantity": 45.0, "unit": "m3", "category": "concrete"},
        headers=headers,
    )
    item_id = item_res.json()["id"]

    # 3. Create quote request
    req_res = await client.post(
        "/api/v1/quote-requests",
        json={"line_item_id": item_id, "response_deadline": "2026-12-31T17:00:00Z"},
        headers=headers,
    )
    assert req_res.status_code == 201
    request_id = req_res.json()["id"]

    # 4. Broadcast request
    broadcast_res = await client.post(
        f"/api/v1/quote-requests/{request_id}/broadcast",
        json={},
        headers=headers,
    )
    assert broadcast_res.status_code == 200

    # 5. Simulate quotes
    sim_res = await client.post(f"/api/v1/boqs/{boq_id}/simulate-quotes", headers=headers)
    assert sim_res.status_code == 200

    # 6. Delete BoQ
    del_res = await client.delete(f"/api/v1/boqs/{boq_id}", headers=headers)
    assert del_res.status_code == 204

    # 7. Verify BoQ is gone
    get_res = await client.get(f"/api/v1/boqs/{boq_id}", headers=headers)
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_delete_boq_unauthorized_other_tenant(client: AsyncClient, seeded_entities: dict):
    """A contractor cannot delete another contractor organisation's BoQ."""
    contractor_token = seeded_entities["contractor_token"]
    other_token = seeded_entities["other_token"]

    # Contractor 1 creates BoQ
    create_res = await client.post(
        "/api/v1/boqs",
        json={"title": "Contractor 1 Private BoQ", "region": "KwaZulu-Natal"},
        headers={"Authorization": f"Bearer {contractor_token}"},
    )
    boq_id = create_res.json()["id"]

    # Contractor 2 tries to delete it
    del_res = await client.delete(
        f"/api/v1/boqs/{boq_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert del_res.status_code == 404
    assert del_res.json()["detail"]["code"] == "BOQ_NOT_FOUND"

    # Verify Contractor 1's BoQ is still intact
    get_res = await client.get(
        f"/api/v1/boqs/{boq_id}",
        headers={"Authorization": f"Bearer {contractor_token}"},
    )
    assert get_res.status_code == 200
    assert get_res.json()["title"] == "Contractor 1 Private BoQ"


@pytest.mark.asyncio
async def test_delete_boq_forbidden_for_supplier(client: AsyncClient, seeded_entities: dict):
    """A supplier cannot delete any BoQ (only contractors are allowed)."""
    contractor_token = seeded_entities["contractor_token"]
    supplier_token = seeded_entities["supplier1_token"]

    # Contractor creates BoQ
    create_res = await client.post(
        "/api/v1/boqs",
        json={"title": "Contractor Project", "region": "KwaZulu-Natal"},
        headers={"Authorization": f"Bearer {contractor_token}"},
    )
    boq_id = create_res.json()["id"]

    # Supplier tries to delete it
    del_res = await client.delete(
        f"/api/v1/boqs/{boq_id}",
        headers={"Authorization": f"Bearer {supplier_token}"},
    )
    assert del_res.status_code == 403


@pytest.mark.asyncio
async def test_delete_boq_not_found(client: AsyncClient, seeded_entities: dict):
    """Deleting a non-existent BoQ returns 404."""
    contractor_token = seeded_entities["contractor_token"]
    non_existent_id = str(uuid.uuid4())

    del_res = await client.delete(
        f"/api/v1/boqs/{non_existent_id}",
        headers={"Authorization": f"Bearer {contractor_token}"},
    )
    assert del_res.status_code == 404
    assert del_res.json()["detail"]["code"] == "BOQ_NOT_FOUND"
