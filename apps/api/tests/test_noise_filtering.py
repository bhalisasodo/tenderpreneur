import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.llm.stub import StubLLMProvider


SAMPLE_RAW_BOQ_WITH_BOILERPLATE = """
SCHEDULE OF QUANTITIES - SECTION 1: CIVILS
Page 1 of 12

Notes and Preambles:
The contractor shall inspect the site before submitting the tender.
All workmanship and materials to comply with SANS 1200.
Allow for water and lighting during construction.

Bill No. 1: Earthworks
1.01 | Excavation in earth for foundation trenches not exceeding 2m | 450.0 | m3
1.02 | Selected granular fill compacted in layers | 220.0 | m3
Carried to Collection of Bill No. 1
Brought forward from Page 1

Bill No. 2: Concrete
2.01 | Supply and place 25MPa / 19mm ready-mix concrete in footings | 115.0 | m3
Total of Bill No. 2
Grand Total Carried Forward to Final Summary

Tenderer's Signature: __________________
Date: __________________
Witness: __________________
"""


@pytest.mark.asyncio
async def test_stub_parser_filters_out_boilerplate_and_subtotals():
    """Verify that legal clauses, carried forward subtotals, and signature lines are filtered."""
    provider = StubLLMProvider()
    result = await provider.parse_boq_document(SAMPLE_RAW_BOQ_WITH_BOILERPLATE)

    assert result is not None
    descriptions = [item.description.lower() for item in result.line_items]

    # Verify real items are present
    assert any("excavation" in d for d in descriptions)
    assert any("granular fill" in d for d in descriptions)
    assert any("25mpa" in d for d in descriptions)

    # Verify noise is filtered out
    assert not any("carried to collection" in d for d in descriptions)
    assert not any("brought forward" in d for d in descriptions)
    assert not any("total of bill" in d for d in descriptions)
    assert not any("grand total" in d for d in descriptions)
    assert not any("contractor shall inspect" in d for d in descriptions)
    assert not any("signature" in d for d in descriptions)
    assert not any("page 1 of 12" in d for d in descriptions)


@pytest.mark.asyncio
async def test_bulk_delete_line_items_api(
    db_session: AsyncSession,
    seeded_entities: dict,
    client: AsyncClient,
):
    """Verify contractor can bulk delete unwanted line items in a single request."""
    contractor_org = seeded_entities["contractor_org"]
    contractor_token = seeded_entities["contractor_token"]
    headers = {"Authorization": f"Bearer {contractor_token}"}

    # 1. Create BoQ with items
    create_res = await client.post(
        "/api/v1/boqs",
        headers=headers,
        json={"title": "Bulk Delete Test BoQ", "region": "KwaZulu-Natal"},
    )
    boq_id = create_res.json()["id"]

    # 2. Add 3 line items
    item_ids = []
    for i in range(3):
        res = await client.post(
            f"/api/v1/boqs/{boq_id}/line-items",
            headers=headers,
            json={"description": f"Test Item {i+1}", "quantity": 10.0, "unit": "no"},
        )
        item_ids.append(res.json()["id"])

    # 3. Bulk delete first 2 items
    delete_res = await client.post(
        f"/api/v1/boqs/{boq_id}/line-items/bulk-delete",
        headers=headers,
        json={"line_item_ids": [item_ids[0], item_ids[1]]},
    )
    assert delete_res.status_code == 200
    assert delete_res.json()["deleted_count"] == 2

    # 4. Verify BoQ details only contain the 3rd item
    boq_res = await client.get(f"/api/v1/boqs/{boq_id}", headers=headers)
    remaining_items = boq_res.json()["line_items"]
    assert len(remaining_items) == 1
    assert remaining_items[0]["id"] == item_ids[2]
