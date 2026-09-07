"""
Tenderpreneur MVP Procurement Loop Test
======================================
Automated end-to-end acceptance test for the complete MVP procurement loop:
1. Health Check
2. Contractor Persona Authentication (Sipho Ndlovu - Amandla Civils)
3. BoQ Creation (Ethekwini Clinic New Outpatient Facility)
4. Raw Schedule of Quantities Ingestion & AI Parsing
5. Manual Line-Item Correction (75 -> 90 m3)
6. Quote Request Creation (48h deadline) & Regional Broadcast
7. Supplier 1 Quote Submission (AfriReady Concrete: R1,950/m3, 2-day lead time)
8. Supplier 2 Competing Quote Submission (Durban Builders Hub: R1,890/m3, 5-day lead time)
9. Contractor Quote Comparison Matrix (Lowest Price & Fastest Delivery Badges)
10. Contractor Quote Selection (Supplier 1 for fast turnaround)
11. Manual Price Override with Mandatory Audit Justification
12. Priced BoQ Exports Generation & Verification (Excel .xlsx & PDF)
13. Non-Repudiable Immutable Audit Trail Verification
"""

from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_mvp_procurement_loop(client: AsyncClient, seeded_entities: dict):
    contractor_token = seeded_entities["contractor_token"]
    supplier1_token = seeded_entities["supplier1_token"]
    supplier2_token = seeded_entities["supplier2_token"]

    c_headers = {"Authorization": f"Bearer {contractor_token}"}
    s1_headers = {"Authorization": f"Bearer {supplier1_token}"}
    s2_headers = {"Authorization": f"Bearer {supplier2_token}"}

    # 1. Health check
    health_res = await client.get("/health")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "ok"

    # 2. Contractor identity verification
    me_res = await client.get("/api/v1/auth/me", headers=c_headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["user"]["role"] == "admin"
    assert me_data["organisation"]["type"] == "contractor"

    # 3. Create BoQ
    boq_res = await client.post(
        "/api/v1/boqs",
        json={
            "title": "Ethekwini Clinic New Outpatient Facility & Access Road",
            "tender_reference": "ETH-2026-CLN-09",
            "tender_deadline": (datetime.now(timezone.utc) + timedelta(days=14)).isoformat(),
            "region": "KwaZulu-Natal",
        },
        headers=c_headers,
    )
    assert boq_res.status_code == 201
    boq = boq_res.json()
    boq_id = boq["id"]
    assert boq["title"] == "Ethekwini Clinic New Outpatient Facility & Access Road"
    assert boq["status"] == "draft"

    # 4. Ingest & Parse Raw Scope Text
    raw_scope = (
        "BILL NO. 1: EARTHWORKS & PRELIMINARIES\n"
        "1.01 | Site clearance and bulk excavation in earth for pipeline trenches | 850.0 | m3\n"
        "1.02 | 25MPa ready-mix concrete for foundation strip footings | 75.0 | m3\n"
        "1.03 | Supply and lay 160mm Class 34 heavy duty uPVC sewer pipes | 520.0 | m\n"
        "1.04 | Double Roman concrete roof tiles on timber trusses | 210.0 | m2\n"
        "1.05 | Supply high-visibility reflective safety vests and hard hats | 50.0 | no\n"
    )
    parse_res = await client.post(
        f"/api/v1/boqs/{boq_id}/parse",
        json={"pasted_text": raw_scope},
        headers=c_headers,
    )
    assert parse_res.status_code == 200
    parsed_boq = parse_res.json()
    assert parsed_boq["status"] == "parsed"
    assert len(parsed_boq["line_items"]) == 5

    line_items = parsed_boq["line_items"]
    concrete_item = next(i for i in line_items if i["category"] == "concrete")
    earthworks_item = next(i for i in line_items if i["category"] == "earthworks")
    assert concrete_item["quantity"] == 75.0

    # 5. Manual Line-Item Correction
    patch_res = await client.patch(
        f"/api/v1/boqs/{boq_id}/line-items/{concrete_item['id']}",
        json={"quantity": 90.0, "unit": "m3"},
        headers=c_headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["quantity"] == 90.0

    # 6. Quote Request Creation & Regional Broadcast
    deadline_48h = (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat()
    qr_res = await client.post(
        "/api/v1/quote-requests",
        json={"line_item_id": concrete_item["id"], "response_deadline": deadline_48h},
        headers=c_headers,
    )
    assert qr_res.status_code == 201
    qr_id = qr_res.json()["id"]

    broadcast_res = await client.post(
        f"/api/v1/quote-requests/{qr_id}/broadcast",
        headers=c_headers,
    )
    assert broadcast_res.status_code == 200
    assert broadcast_res.json()["supplier_count"] >= 1

    # 7. Supplier 1 Quote Submission (AfriReady Concrete)
    s1_quote_res = await client.post(
        f"/api/v1/quote-requests/{qr_id}/quotes",
        json={
            "unit_price_minor": 195000,
            "currency": "ZAR",
            "lead_time_days": 2,
            "notes": "25MPa 19mm stone. Includes retarder additive.",
        },
        headers=s1_headers,
    )
    assert s1_quote_res.status_code == 201
    q1 = s1_quote_res.json()
    assert q1["unit_price_minor"] == 195000
    assert q1["lead_time_days"] == 2

    # 8. Supplier 2 Competing Quote Submission (Durban Builders Hub)
    s2_quote_res = await client.post(
        f"/api/v1/quote-requests/{qr_id}/quotes",
        json={
            "unit_price_minor": 189000,
            "currency": "ZAR",
            "lead_time_days": 5,
            "notes": "Bulk supply discount. 5 working days lead time.",
        },
        headers=s2_headers,
    )
    assert s2_quote_res.status_code == 201
    q2 = s2_quote_res.json()
    assert q2["unit_price_minor"] == 189000
    assert q2["lead_time_days"] == 5

    # 9. Contractor Quote Comparison Matrix
    matrix_res = await client.get(
        f"/api/v1/boqs/{boq_id}/quote-comparison",
        headers=c_headers,
    )
    assert matrix_res.status_code == 200
    matrix = matrix_res.json()
    comp_concrete = next(i for i in matrix["line_items"] if i["line_item_id"] == concrete_item["id"])
    assert comp_concrete["lowest_quote"]["unit_price_minor"] == 189000
    assert comp_concrete["fastest_quote"]["lead_time_days"] == 2

    # 10. Contractor Selects Winning Quote
    select_res = await client.post(
        f"/api/v1/quote-requests/{qr_id}/select",
        json={"quote_id": q1["id"]},
        headers=c_headers,
    )
    assert select_res.status_code == 200
    selected_item = select_res.json()
    assert selected_item["pricing_status"] == "selected"
    assert selected_item["final_price_minor"] == 195000  # R1,950.00 / m3 unit rate
    assert selected_item["selected_quote"]["id"] == q1["id"]

    # 11. Manual Price Override with Mandatory Reason
    override_rate = 18000  # R180.00/m3
    override_res = await client.post(
        f"/api/v1/boqs/{boq_id}/line-items/{earthworks_item['id']}/price-override",
        json={
            "price_minor": override_rate,
            "currency": "ZAR",
            "reason": "Contractor utilizing owned Caterpillar 320D excavator fleet at internal plant charge-out rate.",
        },
        headers=c_headers,
    )
    assert override_res.status_code == 200
    overridden_item = override_res.json()
    assert overridden_item["pricing_status"] == "manually_priced"
    assert overridden_item["final_price_minor"] == override_rate

    # 12. Generate Priced BoQ Exports (Excel & PDF)
    # Excel
    xlsx_res = await client.post(
        f"/api/v1/boqs/{boq_id}/exports",
        json={"format": "xlsx"},
        headers=c_headers,
    )
    assert xlsx_res.status_code == 200
    xlsx_data = xlsx_res.json()
    assert "download_url" in xlsx_data
    xlsx_download = await client.get(xlsx_data["download_url"], headers=c_headers)
    assert xlsx_download.status_code == 200
    assert len(xlsx_download.content) > 1000

    # PDF
    pdf_res = await client.post(
        f"/api/v1/boqs/{boq_id}/exports",
        json={"format": "pdf"},
        headers=c_headers,
    )
    assert pdf_res.status_code == 200
    pdf_data = pdf_res.json()
    assert "download_url" in pdf_data
    pdf_download = await client.get(pdf_data["download_url"], headers=c_headers)
    assert pdf_download.status_code == 200
    assert len(pdf_download.content) > 1000

    # 13. Audit Trail Inspection
    audit_res = await client.get(f"/api/v1/boqs/{boq_id}/audit", headers=c_headers)
    assert audit_res.status_code == 200
    events = audit_res.json()
    actions = [e["action"] for e in events]

    assert "boq.created" in actions
    assert "boq.parsed" in actions
    assert "line_item.edited" in actions
    assert "quote_request.created" in actions
    assert "quote_request.broadcast" in actions
    assert "quote.submitted" in actions
    assert "quote.selected" in actions
    assert "line_item.price_overridden" in actions
    assert "export.generated" in actions
