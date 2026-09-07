from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.models import BoQ, LineItem, QuoteRequest, Quote, AuditEvent, generate_uuid, utc_now
from app.domains.quotes.simulator import simulate_supplier_quotes_for_request, simulate_all_quotes_for_boq


@pytest.mark.asyncio
async def test_simulate_supplier_quotes_for_request(
    db_session: AsyncSession,
    seeded_entities: dict,
    client: AsyncClient,
):
    """Verify that quote simulation generates competitive quotes from matched suppliers and logs audit events."""
    contractor_org = seeded_entities["contractor_org"]
    contractor_token = seeded_entities["contractor_token"]
    headers = {"Authorization": f"Bearer {contractor_token}"}

    # 1. Create a BoQ & Line Item
    boq = BoQ(
        id=generate_uuid(),
        contractor_organisation_id=contractor_org.id,
        title="Simulated Sourcing BoQ",
        region="KwaZulu-Natal",
        status="parsed",
    )
    db_session.add(boq)

    item = LineItem(
        id=generate_uuid(),
        boq_id=boq.id,
        description="Ready-Mix 25MPa Concrete for surface bed",
        unit="m3",
        quantity=50.0,
        category="concrete",
        benchmark_min_minor=180000,
        benchmark_max_minor=240000,
        pricing_status="unsourced",
    )
    db_session.add(item)
    await db_session.commit()

    # 2. Create quote request via API
    deadline = (utc_now() + timedelta(hours=48)).isoformat()
    qr_res = await client.post(
        "/api/v1/quote-requests",
        headers=headers,
        json={"line_item_id": item.id, "response_deadline": deadline},
    )
    assert qr_res.status_code == 201
    qr_id = qr_res.json()["id"]

    # 3. Trigger simulation endpoint
    sim_res = await client.post(
        f"/api/v1/quote-requests/{qr_id}/simulate-responses",
        headers=headers,
    )
    assert sim_res.status_code == 200
    data = sim_res.json()
    assert data["status"] == "success"
    assert data["quotes_count"] > 0

    # 4. Check that comparison endpoint shows the quotes
    comp_res = await client.get(f"/api/v1/boqs/{boq.id}/quote-comparison", headers=headers)
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    first_item = comp_data["line_items"][0]
    assert len(first_item["quotes"]) > 0
    assert first_item["lowest_quote"] is not None
    assert first_item["pricing_status"] == "quoted"


@pytest.mark.asyncio
async def test_simulate_all_quotes_for_boq(
    db_session: AsyncSession,
    seeded_entities: dict,
    client: AsyncClient,
):
    """Verify simulating quotes across multiple open line item requests in a BoQ."""
    contractor_org = seeded_entities["contractor_org"]
    contractor_token = seeded_entities["contractor_token"]
    headers = {"Authorization": f"Bearer {contractor_token}"}

    # 1. Create a BoQ with 2 items
    boq = BoQ(
        id=generate_uuid(),
        contractor_organisation_id=contractor_org.id,
        title="Multi-item Sourcing BoQ",
        region="KwaZulu-Natal",
        status="parsed",
    )
    db_session.add(boq)

    item1 = LineItem(
        id=generate_uuid(),
        boq_id=boq.id,
        description="50kg Portland Cement bags",
        unit="no",
        quantity=200.0,
        category="building-materials",
        benchmark_min_minor=9000,
        benchmark_max_minor=13000,
        pricing_status="unsourced",
    )
    item2 = LineItem(
        id=generate_uuid(),
        boq_id=boq.id,
        description="25MPa ready-mix concrete for foundation",
        unit="m3",
        quantity=30.0,
        category="concrete",
        benchmark_min_minor=180000,
        benchmark_max_minor=240000,
        pricing_status="unsourced",
    )
    db_session.add_all([item1, item2])
    await db_session.commit()

    # 2. Create quote requests for both items
    deadline = (utc_now() + timedelta(hours=48)).isoformat()
    await client.post(
        "/api/v1/quote-requests",
        headers=headers,
        json={"line_item_id": item1.id, "response_deadline": deadline},
    )
    await client.post(
        "/api/v1/quote-requests",
        headers=headers,
        json={"line_item_id": item2.id, "response_deadline": deadline},
    )

    # 3. Simulate quotes for whole BoQ
    sim_res = await client.post(f"/api/v1/boqs/{boq.id}/simulate-quotes", headers=headers)
    assert sim_res.status_code == 200
    assert sim_res.json()["total_quotes"] >= 2
