import io
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_boq_and_manual_line_item(client: AsyncClient, seeded_entities: dict):
    token = seeded_entities["contractor_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create BoQ
    create_res = await client.post(
        "/api/v1/boqs",
        json={
            "title": "Durban Port Expansion",
            "tender_reference": "TNPA-DBN-2026-001",
            "region": "KwaZulu-Natal",
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    boq = create_res.json()
    assert boq["title"] == "Durban Port Expansion"
    boq_id = boq["id"]

    # 2. Add line item manually
    item_res = await client.post(
        f"/api/v1/boqs/{boq_id}/line-items",
        json={
            "source_row_reference": "1.01",
            "description": "50kg Portland Cement bags",
            "unit": "no",
            "quantity": 100.0,
            "category": "building-materials",
            "benchmark_min_minor": 9000,
            "benchmark_max_minor": 12000,
        },
        headers=headers,
    )
    assert item_res.status_code == 201
    item = item_res.json()
    assert item["description"] == "50kg Portland Cement bags"
    assert item["quantity"] == 100.0

    # 3. Correct / Edit line item
    item_id = item["id"]
    edit_res = await client.patch(
        f"/api/v1/boqs/{boq_id}/line-items/{item_id}",
        json={"quantity": 150.0, "unit": "bags"},
        headers=headers,
    )
    assert edit_res.status_code == 200
    updated_item = edit_res.json()
    assert updated_item["quantity"] == 150.0
    assert updated_item["unit"] == "bags"


@pytest.mark.asyncio
async def test_parse_boq_pasted_text(client: AsyncClient, seeded_entities: dict):
    token = seeded_entities["contractor_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create BoQ
    create_res = await client.post(
        "/api/v1/boqs",
        json={"title": "Test Paste BoQ", "region": "KwaZulu-Natal"},
        headers=headers,
    )
    boq_id = create_res.json()["id"]

    # Parse with structured text
    pasted_content = (
        "Item | Description | Quantity | Unit\n"
        "1.1 | Ready-mix concrete 25MPa for foundations | 80 | m3\n"
        "1.2 | Excavation in hard rock not exceeding 1.5m deep | 120 | m3\n"
        "1.3 | Safety boots and hardhats for site workers | 20 | no\n"
    )

    parse_res = await client.post(
        f"/api/v1/boqs/{boq_id}/parse",
        json={"pasted_text": pasted_content},
        headers=headers,
    )
    assert parse_res.status_code == 200
    parsed_boq = parse_res.json()
    assert parsed_boq["status"] == "parsed"
    assert len(parsed_boq["line_items"]) == 3

    categories = [i["category"] for i in parsed_boq["line_items"]]
    assert "concrete" in categories
    assert "earthworks" in categories
    assert "ppe" in categories


@pytest.mark.asyncio
async def test_tenant_isolation_boqs(client: AsyncClient, seeded_entities: dict):
    contractor_token = seeded_entities["contractor_token"]
    other_token = seeded_entities["other_token"]

    # Contractor 1 creates BoQ
    res = await client.post(
        "/api/v1/boqs",
        json={"title": "Private Secret Tender", "region": "KwaZulu-Natal"},
        headers={"Authorization": f"Bearer {contractor_token}"},
    )
    boq_id = res.json()["id"]

    # Contractor 2 tries to access it -> 404
    rival_res = await client.get(
        f"/api/v1/boqs/{boq_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert rival_res.status_code == 404
