import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_audit_trail_recorded(client: AsyncClient, seeded_entities: dict):
    contractor_token = seeded_entities["contractor_token"]
    headers = {"Authorization": f"Bearer {contractor_token}"}

    # 1. Create BoQ
    boq_res = await client.post(
        "/api/v1/boqs",
        json={"title": "Audit Test Project", "region": "KwaZulu-Natal"},
        headers=headers,
    )
    boq_id = boq_res.json()["id"]

    # 2. Add line item
    item_res = await client.post(
        f"/api/v1/boqs/{boq_id}/line-items",
        json={"description": "Plumbing pipes 110mm", "quantity": 50.0, "unit": "m", "category": "plumbing"},
        headers=headers,
    )
    item_id = item_res.json()["id"]

    # 3. Override price
    await client.post(
        f"/api/v1/boqs/{boq_id}/line-items/{item_id}/price-override",
        json={"price_minor": 4500, "reason": "Local manufacturer agreement"},
        headers=headers,
    )

    # 4. Check audit trail
    audit_res = await client.get(f"/api/v1/boqs/{boq_id}/audit", headers=headers)
    assert audit_res.status_code == 200
    events = audit_res.json()
    actions = [e["action"] for e in events]
    assert "boq.created" in actions
    assert "line_item.created" in actions
    assert "line_item.price_overridden" in actions
