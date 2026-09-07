import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_demo_tenants_endpoint(client: AsyncClient, seeded_entities: dict):
    """Verify demo-tenants endpoint lists all seeded contractor and supplier users."""
    res = await client.get("/api/v1/auth/demo-tenants")
    assert res.status_code == 200
    tenants = res.json()
    assert len(tenants) >= 3

    org_types = [t["organisation"]["type"] for t in tenants]
    assert "contractor" in org_types
    assert "supplier" in org_types

    emails = [t["email"] for t in tenants]
    assert any("amandla" in e for e in emails)
    assert any("durban" in e for e in emails)


@pytest.mark.asyncio
async def test_auto_select_best_quotes_endpoint(
    db_session: AsyncSession,
    seeded_entities: dict,
    client: AsyncClient,
):
    """Verify auto-select picks the lowest submitted quote across items."""
    contractor_token = seeded_entities["contractor_token"]
    supplier1_token = seeded_entities["supplier1_token"]
    supplier2_token = seeded_entities["supplier2_token"]
    contractor_headers = {"Authorization": f"Bearer {contractor_token}"}
    supplier1_headers = {"Authorization": f"Bearer {supplier1_token}"}
    supplier2_headers = {"Authorization": f"Bearer {supplier2_token}"}

    # 1. Contractor creates BoQ and line item
    boq_res = await client.post(
        "/api/v1/boqs",
        headers=contractor_headers,
        json={"title": "Auto Select Demo Tender", "region": "KwaZulu-Natal"},
    )
    boq_id = boq_res.json()["id"]

    item_res = await client.post(
        f"/api/v1/boqs/{boq_id}/line-items",
        headers=contractor_headers,
        json={"description": "25MPa Ready-Mix Concrete", "quantity": 100.0, "unit": "m3", "category": "concrete"},
    )
    item_id = item_res.json()["id"]

    # 2. Broadcast quote request
    qr_res = await client.post(
        "/api/v1/quote-requests",
        headers=contractor_headers,
        json={"line_item_id": item_id, "response_deadline": "2026-12-31T23:59:59Z"},
    )
    qr_id = qr_res.json()["id"]
    await client.post(f"/api/v1/quote-requests/{qr_id}/broadcast", headers=contractor_headers)

    # 3. Supplier 1 submits quote @ R110 (11000 cents)
    res1 = await client.post(
        f"/api/v1/quote-requests/{qr_id}/quotes",
        headers=supplier1_headers,
        json={"unit_price_minor": 11000, "lead_time_days": 2, "notes": "Includes delivery"},
    )
    assert res1.status_code == 201

    # 4. Supplier 2 submits competing quote @ R95 (9500 cents) - cheaper!
    res2 = await client.post(
        f"/api/v1/quote-requests/{qr_id}/quotes",
        headers=supplier2_headers,
        json={"unit_price_minor": 9500, "lead_time_days": 1, "notes": "Express delivery"},
    )
    assert res2.status_code == 201

    # 5. Contractor triggers auto-select best quotes
    auto_res = await client.post(
        f"/api/v1/boqs/{boq_id}/auto-select-best-quotes",
        headers=contractor_headers,
    )
    assert auto_res.status_code == 200
    auto_data = auto_res.json()
    assert auto_data["selected_count"] == 1
    # 100 qty * 9500 cents = 950000 cents
    assert auto_data["total_priced_minor"] == 950000

    # 6. Verify item is priced from quote
    comparison_res = await client.get(f"/api/v1/boqs/{boq_id}/quote-comparison", headers=contractor_headers)
    assert comparison_res.status_code == 200
    comp_data = comparison_res.json()
    priced_item = comp_data["line_items"][0]
    assert priced_item["final_price_minor"] == 9500
    assert priced_item["selected_quote"]["unit_price_minor"] == 9500
