import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import AuditEvent
from app.core.security import create_rfq_access_token


@pytest.mark.asyncio
async def test_public_registration_creates_supplier_application_pending_review(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "organisation_type": "supplier",
            "legal_name": "New Durban Supplier (Pty) Ltd",
            "email": "new-supplier@example.co.za",
            "phone": "+27820000000",
            "region": "KwaZulu-Natal",
            "name": "Supplier Contact",
            "password": "SupplierPassword2026!",
            "supplier_categories": ["building-materials"],
            "supplier_service_regions": ["KwaZulu-Natal"],
        },
    )
    assert response.status_code == 201
    registration = response.json()
    assert registration["supplier_approval_status"] == "pending"

    profile = await client.get(
        "/api/v1/suppliers/profile",
        headers={"Authorization": f"Bearer {registration['access_token']}"},
    )
    assert profile.status_code == 200
    assert profile.json()["status"] == "pending"
    assert profile.json()["active"] is False

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "new-supplier@example.co.za", "password": "SupplierPassword2026!"},
    )
    assert login.status_code == 200
    assert login.json()["supplier_approval_status"] == "pending"


@pytest.mark.asyncio
async def test_supplier_approval_is_required_for_matching_and_delivery(
    client: AsyncClient, seeded_entities: dict, pending_supplier: dict
):
    contractor_token = seeded_entities["contractor_token"]
    operator_token = seeded_entities["platform_admin_token"]
    supplier_org_id = pending_supplier["organisation"].id
    supplier_token = pending_supplier["token"]

    matching_res = await client.get(
        "/api/v1/suppliers/match?category=building-materials&region=eThekwini",
        headers={"Authorization": f"Bearer {contractor_token}"},
    )
    assert matching_res.status_code == 200
    matched_ids = {supplier["organisation_id"] for supplier in matching_res.json()}
    assert supplier_org_id not in matched_ids

    contractor_approval_res = await client.post(
        f"/api/v1/suppliers/{supplier_org_id}/approve",
        headers={"Authorization": f"Bearer {contractor_token}"},
    )
    assert contractor_approval_res.status_code == 403

    approval_res = await client.post(
        f"/api/v1/suppliers/{supplier_org_id}/approve",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert approval_res.status_code == 200
    assert approval_res.json()["status"] == "approved"

    approved_profile_res = await client.get(
        "/api/v1/suppliers/profile",
        headers={"Authorization": f"Bearer {supplier_token}"},
    )
    assert approved_profile_res.status_code == 200
    assert approved_profile_res.json()["status"] == "approved"

    matching_after_approval = await client.get(
        "/api/v1/suppliers/match?category=building-materials&region=eThekwini",
        headers={"Authorization": f"Bearer {contractor_token}"},
    )
    assert supplier_org_id in {
        supplier["organisation_id"] for supplier in matching_after_approval.json()
    }


@pytest.mark.asyncio
async def test_supplier_rejection_blocks_matching_and_quote_delivery(
    client: AsyncClient, seeded_entities: dict, pending_supplier: dict, db_session
):
    operator_token = seeded_entities["platform_admin_token"]
    supplier_org_id = pending_supplier["organisation"].id
    supplier_token = pending_supplier["token"]
    pending_supplier["profile"].categories = ["electrical"]
    pending_supplier["profile"].service_regions = ["Gauteng"]
    await db_session.commit()

    reject_res = await client.post(
        f"/api/v1/suppliers/{supplier_org_id}/reject",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "rejected"
    assert reject_res.json()["active"] is False

    profile_res = await client.get(
        "/api/v1/suppliers/profile",
        headers={"Authorization": f"Bearer {supplier_token}"},
    )
    assert profile_res.status_code == 200
    assert profile_res.json()["status"] == "rejected"

    matching_res = await client.get(
        "/api/v1/suppliers/match?category=electrical&region=Gauteng",
        headers={"Authorization": f"Bearer {seeded_entities['contractor_token']}"},
    )
    assert supplier_org_id not in {supplier["organisation_id"] for supplier in matching_res.json()}

    update_res = await client.post(
        "/api/v1/suppliers/profile",
        headers={"Authorization": f"Bearer {supplier_token}"},
        json={"status": "approved", "active": True},
    )
    assert update_res.status_code == 422


@pytest.mark.asyncio
async def test_supplier_profile_endpoints(client: AsyncClient, seeded_entities: dict):
    supplier_token = seeded_entities["supplier1_token"]

    # 1. Get supplier profile
    get_res = await client.get(
        "/api/v1/suppliers/profile",
        headers={"Authorization": f"Bearer {supplier_token}"},
    )
    assert get_res.status_code == 200
    profile = get_res.json()
    assert "building-materials" in profile["categories"]

    # 2. Update supplier profile
    update_res = await client.post(
        "/api/v1/suppliers/profile",
        headers={"Authorization": f"Bearer {supplier_token}"},
        json={
            "categories": ["building-materials", "concrete", "earthworks"],
            "service_regions": ["KwaZulu-Natal", "Eastern Cape"],
            "preferred_contact_method": "email",
            "compliance_flags": {"bbee_level": "2", "csd_registered": True},
        },
    )
    assert update_res.status_code == 200
    updated = update_res.json()
    assert "earthworks" in updated["categories"]
    assert "Eastern Cape" in updated["service_regions"]
    assert updated["preferred_contact_method"] == "email"


@pytest.mark.asyncio
async def test_rfq_broadcast_and_frictionless_mobile_token_quoting(
    client: AsyncClient, seeded_entities: dict
):
    contractor_token = seeded_entities["contractor_token"]
    supplier1_org = seeded_entities["supplier1_org"]

    # 1. Contractor creates a BoQ
    boq_res = await client.post(
        "/api/v1/boqs",
        headers={"Authorization": f"Bearer {contractor_token}"},
        json={
            "title": "Durban Port Perimeter Retaining Wall Tender",
            "tender_reference": "TRANSNET-2026-09",
            "region": "eThekwini",
        },
    )
    assert boq_res.status_code == 201
    boq_id = boq_res.json()["id"]

    # 2. Add line item
    item_res = await client.post(
        f"/api/v1/boqs/{boq_id}/line-items",
        headers={"Authorization": f"Bearer {contractor_token}"},
        json={
            "description": "Supply and deliver 50kg bags of Portland cement CEM II 42.5N to site",
            "quantity": 600,
            "unit": "no",
            "category": "building-materials",
        },
    )
    assert item_res.status_code == 201
    item_id = item_res.json()["id"]

    # 3. Create quote request
    qr_res = await client.post(
        "/api/v1/quote-requests",
        headers={"Authorization": f"Bearer {contractor_token}"},
        json={
            "line_item_id": item_id,
            "response_deadline": "2026-12-31T17:00:00Z",
        },
    )
    assert qr_res.status_code == 201
    qr_id = qr_res.json()["id"]

    # 4. Broadcast quote request to matched suppliers
    broadcast_res = await client.post(
        f"/api/v1/quote-requests/{qr_id}/broadcast",
        headers={"Authorization": f"Bearer {contractor_token}"},
    )
    assert broadcast_res.status_code == 200

    # 5. Simulate supplier clicking mobile alert link with query access_token (NO Bearer header)
    rfq_direct_token = create_rfq_access_token(quote_request_id=qr_id, supplier_org_id=supplier1_org.id)

    # 5a. Supplier retrieves RFQ specifications
    mobile_view_res = await client.get(
        f"/api/v1/suppliers/quote-requests/{qr_id}",
        headers={"Authorization": f"Bearer {rfq_direct_token}"},
    )
    assert mobile_view_res.status_code == 200
    mobile_data = mobile_view_res.json()
    assert mobile_data["id"] == qr_id
    assert mobile_data["line_item_quantity"] == 600
    assert mobile_data["line_item_unit"] == "no"

    profile_res = await client.get(
        "/api/v1/suppliers/profile",
        headers={"Authorization": f"Bearer {rfq_direct_token}"},
    )
    inbox_res = await client.get(
        "/api/v1/suppliers/quote-requests",
        headers={"Authorization": f"Bearer {rfq_direct_token}"},
    )
    assert profile_res.status_code == 403
    assert inbox_res.status_code == 403

    # 5b. Supplier submits quote using only query access_token (NO prior login session)
    quote_submit_res = await client.post(
        f"/api/v1/quote-requests/{qr_id}/quotes",
        headers={"Authorization": f"Bearer {rfq_direct_token}"},
        json={
            "unit_price_minor": 9850,  # R98.50 per bag
            "currency": "ZAR",
            "lead_time_days": 2,
            "notes": "Includes flatbed delivery to Port of Durban site.",
        },
    )
    assert quote_submit_res.status_code == 201
    quote_data = quote_submit_res.json()
    assert quote_data["unit_price_minor"] == 9850
    assert quote_data["total_price_minor"] == 600 * 9850

    # 5c. Contractor checks quote comparison
    comp_res = await client.get(
        f"/api/v1/boqs/{boq_id}/quote-comparison",
        headers={"Authorization": f"Bearer {contractor_token}"},
    )
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert len(comp_data["line_items"]) == 1
    assert comp_data["line_items"][0]["lowest_quote"]["unit_price_minor"] == 9850


@pytest.mark.asyncio
async def test_rfq_token_security_and_tenant_isolation(
    client: AsyncClient, seeded_entities: dict
):
    supplier1_token = seeded_entities["supplier1_token"]

    # 1. Supplier cannot access contractor private BoQ list
    boq_forbidden_res = await client.get(
        "/api/v1/boqs",
        headers={"Authorization": f"Bearer {supplier1_token}"},
    )
    assert boq_forbidden_res.status_code == 403

    # 2. RFQ direct token for Request A cannot be used to submit quotes on Request B
    token_for_request_a = create_rfq_access_token(
        quote_request_id="request-aaa", supplier_org_id=seeded_entities["supplier1_org"].id
    )
    mismatch_res = await client.post(
        "/api/v1/quote-requests/request-bbb/quotes",
        headers={"Authorization": f"Bearer {token_for_request_a}"},
        json={"unit_price_minor": 5000, "currency": "ZAR"},
    )
    assert mismatch_res.status_code == 403

    query_token_res = await client.get(
        "/api/v1/suppliers/quote-requests/request-aaa"
        f"?access_token={token_for_request_a}"
    )
    assert query_token_res.status_code == 401


@pytest.mark.asyncio
async def test_direct_rfq_quote_audit_does_not_claim_a_user_account(
    client: AsyncClient,
    seeded_entities: dict,
    db_session: AsyncSession,
):
    contractor_headers = {"Authorization": f"Bearer {seeded_entities['contractor_token']}"}
    boq = await client.post(
        "/api/v1/boqs",
        headers=contractor_headers,
        json={"title": "Direct RFQ audit test", "region": "eThekwini"},
    )
    item = await client.post(
        f"/api/v1/boqs/{boq.json()['id']}/line-items",
        headers=contractor_headers,
        json={
            "description": "Portland cement 42.5N",
            "quantity": 20,
            "unit": "bag",
            "category": "building-materials",
        },
    )
    request = await client.post(
        "/api/v1/quote-requests",
        headers=contractor_headers,
        json={
            "line_item_id": item.json()["id"],
            "response_deadline": "2026-12-31T17:00:00Z",
        },
    )
    assert request.status_code == 201
    request_id = request.json()["id"]
    broadcast = await client.post(
        f"/api/v1/quote-requests/{request_id}/broadcast",
        headers=contractor_headers,
    )
    assert broadcast.status_code == 200

    direct_token = create_rfq_access_token(
        quote_request_id=request_id,
        supplier_org_id=seeded_entities["supplier1_org"].id,
    )
    submitted = await client.post(
        f"/api/v1/quote-requests/{request_id}/quotes",
        headers={"Authorization": f"Bearer {direct_token}"},
        json={"unit_price_minor": 5000, "currency": "ZAR"},
    )
    assert submitted.status_code == 201

    event = await db_session.scalar(
        select(AuditEvent).where(
            AuditEvent.entity_type == "quote",
            AuditEvent.entity_id == submitted.json()["id"],
            AuditEvent.action == "quote.submitted",
        )
    )
    assert event is not None
    assert event.actor_user_id is None
    assert event.organisation_id == seeded_entities["supplier1_org"].id
    assert event.metadata_json == {"access_method": "rfq_link"}


@pytest.mark.asyncio
async def test_broadcast_never_uses_unmatched_or_unapproved_suppliers(
    client: AsyncClient,
    seeded_entities: dict,
    pending_supplier: dict,
):
    contractor_headers = {"Authorization": f"Bearer {seeded_entities['contractor_token']}"}
    boq = await client.post(
        "/api/v1/boqs",
        headers=contractor_headers,
        json={"title": "Unmatched roofing request", "region": "eThekwini"},
    )
    item = await client.post(
        f"/api/v1/boqs/{boq.json()['id']}/line-items",
        headers=contractor_headers,
        json={
            "description": "Supply roofing sheets to site",
            "quantity": 10,
            "unit": "no",
            "category": "roofing",
        },
    )
    request = await client.post(
        "/api/v1/quote-requests",
        headers=contractor_headers,
        json={"line_item_id": item.json()["id"], "response_deadline": "2026-12-31T23:59:59Z"},
    )
    broadcast_url = f"/api/v1/quote-requests/{request.json()['id']}/broadcast"

    unmatched = await client.post(broadcast_url, headers=contractor_headers)
    assert unmatched.status_code == 422
    assert unmatched.json()["detail"]["code"] == "NO_MATCHED_SUPPLIERS"

    unapproved = await client.post(
        broadcast_url,
        headers=contractor_headers,
        json={"supplier_organisation_ids": [pending_supplier["organisation"].id]},
    )
    assert unapproved.status_code == 422
    assert unapproved.json()["detail"]["code"] == "INVALID_SUPPLIER_RECIPIENTS"
