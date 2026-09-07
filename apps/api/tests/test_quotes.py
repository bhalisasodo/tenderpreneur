from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_quote_flow_and_server_deadline_enforcement(client: AsyncClient, seeded_entities: dict):
    contractor_token = seeded_entities["contractor_token"]
    supplier1_token = seeded_entities["supplier1_token"]
    c_headers = {"Authorization": f"Bearer {contractor_token}"}
    s_headers = {"Authorization": f"Bearer {supplier1_token}"}

    # 1. Create BoQ and Line Item
    boq_res = await client.post(
        "/api/v1/boqs",
        json={"title": "Tender Quote Test", "region": "KwaZulu-Natal"},
        headers=c_headers,
    )
    boq_id = boq_res.json()["id"]

    item_res = await client.post(
        f"/api/v1/boqs/{boq_id}/line-items",
        json={
            "description": "50kg All-Purpose Cement",
            "unit": "no",
            "quantity": 100.0,
            "category": "building-materials",
        },
        headers=c_headers,
    )
    item_id = item_res.json()["id"]

    # 2. Create Quote Request with future deadline
    future_deadline = (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat()
    qr_res = await client.post(
        "/api/v1/quote-requests",
        json={"line_item_id": item_id, "response_deadline": future_deadline},
        headers=c_headers,
    )
    assert qr_res.status_code == 201
    qr_id = qr_res.json()["id"]

    # 3. Broadcast to matched suppliers
    broadcast_res = await client.post(
        f"/api/v1/quote-requests/{qr_id}/broadcast",
        headers=c_headers,
    )
    assert broadcast_res.status_code == 200

    # 4. Supplier checks inbox
    inbox_res = await client.get("/api/v1/suppliers/quote-requests", headers=s_headers)
    assert inbox_res.status_code == 200
    inbox_items = inbox_res.json()
    assert any(req["id"] == qr_id for req in inbox_items)

    # 5. Supplier submits valid quote on time
    quote_res = await client.post(
        f"/api/v1/quote-requests/{qr_id}/quotes",
        json={
            "unit_price_minor": 10500,  # R105.00
            "currency": "ZAR",
            "lead_time_days": 2,
            "notes": "Direct from Durban depot",
        },
        headers=s_headers,
    )
    assert quote_res.status_code == 201
    quote = quote_res.json()
    assert quote["unit_price_minor"] == 10500
    assert quote["total_price_minor"] == 1050000  # R10,500.00 (100 * 10500)
    quote_id = quote["id"]

    # 6. Contractor checks comparison
    comp_res = await client.get(f"/api/v1/boqs/{boq_id}/quote-comparison", headers=c_headers)
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    li_comp = comp_data["line_items"][0]
    assert len(li_comp["quotes"]) == 1
    assert li_comp["lowest_quote"]["unit_price_minor"] == 10500

    # 7. Contractor selects quote
    select_res = await client.post(
        f"/api/v1/quote-requests/{qr_id}/select",
        json={"quote_id": quote_id},
        headers=c_headers,
    )
    assert select_res.status_code == 200
    assert select_res.json()["final_price_minor"] == 10500
    assert select_res.json()["pricing_status"] == "selected"

    # 8. Contractor applies manual price override
    override_res = await client.post(
        f"/api/v1/boqs/{boq_id}/line-items/{item_id}/price-override",
        json={
            "price_minor": 9800,  # R98.00 negotiated rate
            "currency": "ZAR",
            "reason": "Executive supplier discount applied",
        },
        headers=c_headers,
    )
    assert override_res.status_code == 200
    assert override_res.json()["final_price_minor"] == 9800
    assert override_res.json()["pricing_status"] == "manually_priced"


@pytest.mark.asyncio
async def test_deadline_expired_rejection(client: AsyncClient, seeded_entities: dict):
    contractor_token = seeded_entities["contractor_token"]
    supplier1_token = seeded_entities["supplier1_token"]
    c_headers = {"Authorization": f"Bearer {contractor_token}"}
    s_headers = {"Authorization": f"Bearer {supplier1_token}"}

    boq_res = await client.post(
        "/api/v1/boqs",
        json={"title": "Deadline BoQ", "region": "KwaZulu-Natal"},
        headers=c_headers,
    )
    boq_id = boq_res.json()["id"]

    item_res = await client.post(
        f"/api/v1/boqs/{boq_id}/line-items",
        json={"description": "Timber", "category": "roofing"},
        headers=c_headers,
    )
    item_id = item_res.json()["id"]

    # Create request with very short 1 second deadline
    almost_past_deadline = (datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat()
    qr_res = await client.post(
        "/api/v1/quote-requests",
        json={"line_item_id": item_id, "response_deadline": almost_past_deadline},
        headers=c_headers,
    )
    qr_id = qr_res.json()["id"]

    await client.post(f"/api/v1/quote-requests/{qr_id}/broadcast", headers=c_headers)

    # Wait for deadline to expire
    import asyncio
    await asyncio.sleep(1.5)

    # Attempt to submit after deadline
    late_res = await client.post(
        f"/api/v1/quote-requests/{qr_id}/quotes",
        json={"unit_price_minor": 5000},
        headers=s_headers,
    )
    assert late_res.status_code == 422
    assert late_res.json()["detail"]["code"] == "DEADLINE_EXPIRED"
