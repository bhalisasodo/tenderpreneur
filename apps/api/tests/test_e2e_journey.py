from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_contractor_supplier_procurement_journey(client: AsyncClient, seeded_entities: dict):
    """
    End-to-End User Journey Test conforming to source build brief & AGENTS.md:
    Contractor creates BoQ -> uploads/pastes scope -> parser structures line items ->
    contractor corrects line item -> contractor broadcasts quote request to matched suppliers ->
    supplier submits mobile quote on time -> contractor compares quotes (lowest/fastest) ->
    contractor selects quote -> contractor overrides another item price with reason ->
    priced BoQ is exported to Excel & PDF -> audit trail remains inspectable.
    """
    contractor_token = seeded_entities["contractor_token"]
    supplier1_token = seeded_entities["supplier1_token"]
    supplier2_token = seeded_entities["supplier2_token"]

    c_headers = {"Authorization": f"Bearer {contractor_token}"}
    s1_headers = {"Authorization": f"Bearer {supplier1_token}"}
    s2_headers = {"Authorization": f"Bearer {supplier2_token}"}

    # STEP 1: Contractor creates BoQ
    boq_res = await client.post(
        "/api/v1/boqs",
        json={
            "title": "Ethekwini Clinic New Outpatient Facility",
            "tender_reference": "ETH-2026-CLN-09",
            "region": "KwaZulu-Natal",
        },
        headers=c_headers,
    )
    assert boq_res.status_code == 201
    boq = boq_res.json()
    boq_id = boq["id"]
    assert boq["status"] == "draft"

    # STEP 2: Ingest & Parse document / scope
    scope_text = (
        "Item | Description | Quantity | Unit\n"
        "1.01 | 25MPa ready-mix concrete for foundation strip footings | 60 | m3\n"
        "1.02 | 50kg Portland cement bags for brickwork mortar | 300 | no\n"
        "1.03 | Structural excavation not exceeding 2m in loose soil | 150 | m3\n"
    )
    parse_res = await client.post(
        f"/api/v1/boqs/{boq_id}/parse",
        json={"pasted_text": scope_text},
        headers=c_headers,
    )
    assert parse_res.status_code == 200
    parsed_boq = parse_res.json()
    assert parsed_boq["status"] == "parsed"
    assert len(parsed_boq["line_items"]) == 3

    items = parsed_boq["line_items"]
    item_concrete = next(i for i in items if i["category"] == "concrete")
    item_cement = next(i for i in items if i["category"] == "building-materials")
    item_earth = next(i for i in items if i["category"] == "earthworks")

    # STEP 3: Contractor manually corrects parsed line item
    edit_res = await client.patch(
        f"/api/v1/boqs/{boq_id}/line-items/{item_concrete['id']}",
        json={"quantity": 75.0, "unit": "m3"},
        headers=c_headers,
    )
    assert edit_res.status_code == 200
    assert edit_res.json()["quantity"] == 75.0

    # STEP 4: Match suppliers and broadcast quote request for concrete
    future_deadline = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    qr_res = await client.post(
        "/api/v1/quote-requests",
        json={"line_item_id": item_concrete["id"], "response_deadline": future_deadline},
        headers=c_headers,
    )
    assert qr_res.status_code == 201
    qr_id = qr_res.json()["id"]

    broadcast_res = await client.post(
        f"/api/v1/quote-requests/{qr_id}/broadcast",
        headers=c_headers,
    )
    assert broadcast_res.status_code == 200

    # STEP 5: Multiple suppliers receive and submit competitive quotes
    # Supplier 1 submits quote (R2,100 / m3)
    s1_quote = await client.post(
        f"/api/v1/quote-requests/{qr_id}/quotes",
        json={
            "unit_price_minor": 210000,
            "currency": "ZAR",
            "lead_time_days": 3,
            "notes": "Includes retarder additive",
        },
        headers=s1_headers,
    )
    assert s1_quote.status_code == 201

    # Supplier 2 submits cheaper quote (R1,950 / m3)
    s2_quote = await client.post(
        f"/api/v1/quote-requests/{qr_id}/quotes",
        json={
            "unit_price_minor": 195000,
            "currency": "ZAR",
            "lead_time_days": 1,
            "notes": "Pump truck available on site",
        },
        headers=s2_headers,
    )
    assert s2_quote.status_code == 201
    s2_quote_id = s2_quote.json()["id"]

    # STEP 6: Contractor compares quotes in matrix
    comp_res = await client.get(f"/api/v1/boqs/{boq_id}/quote-comparison", headers=c_headers)
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    comp_concrete = next(c for c in comp_data["line_items"] if c["line_item_id"] == item_concrete["id"])
    assert len(comp_concrete["quotes"]) == 2
    assert comp_concrete["lowest_quote"]["unit_price_minor"] == 195000
    assert comp_concrete["fastest_quote"]["lead_time_days"] == 1

    # STEP 7: Contractor selects winning quote (Supplier 2)
    select_res = await client.post(
        f"/api/v1/quote-requests/{qr_id}/select",
        json={"quote_id": s2_quote_id},
        headers=c_headers,
    )
    assert select_res.status_code == 200
    assert select_res.json()["final_price_minor"] == 195000

    # STEP 8: Contractor manually overrides cement item price with audit reason
    override_res = await client.post(
        f"/api/v1/boqs/{boq_id}/line-items/{item_cement['id']}/price-override",
        json={
            "price_minor": 9400,  # R94.00
            "currency": "ZAR",
            "reason": "Contractor bulk account credit with local merchant",
        },
        headers=c_headers,
    )
    assert override_res.status_code == 200
    assert override_res.json()["final_price_minor"] == 9400

    # Override earthworks item
    await client.post(
        f"/api/v1/boqs/{boq_id}/line-items/{item_earth['id']}/price-override",
        json={"price_minor": 7500, "reason": "Internal plant rate"},
        headers=c_headers,
    )

    # STEP 9: Export submission-ready priced BoQ (Excel + PDF)
    excel_export = await client.post(
        f"/api/v1/boqs/{boq_id}/exports",
        json={"format": "xlsx"},
        headers=c_headers,
    )
    assert excel_export.status_code == 200
    assert "download_url" in excel_export.json()

    pdf_export = await client.post(
        f"/api/v1/boqs/{boq_id}/exports",
        json={"format": "pdf"},
        headers=c_headers,
    )
    assert pdf_export.status_code == 200

    # STEP 10: Verify complete inspectable audit trail
    audit_res = await client.get(f"/api/v1/boqs/{boq_id}/audit", headers=c_headers)
    assert audit_res.status_code == 200
    audit_events = audit_res.json()
    actions = [e["action"] for e in audit_events]
    assert "boq.created" in actions
    assert "boq.parsed" in actions
    assert "line_item.edited" in actions
    assert "quote_request.created" in actions
    assert "quote_request.broadcast" in actions
    assert "quote.selected" in actions
    assert "line_item.price_overridden" in actions
    assert "export.generated" in actions
