import pytest
from httpx import AsyncClient
from app.core.security import create_rfq_access_token


@pytest.mark.asyncio
async def test_supplier_registration_and_login_lifecycle(client: AsyncClient):
    payload = {
        "legal_name": "Tshwane Quarry & Aggregate Supplies (Pty) Ltd",
        "trading_name": "Tshwane Aggregates",
        "contact_name": "Kagiso Mokoena",
        "email": "kagiso@tshwaneaggregates.co.za",
        "phone": "+27 82 555 8899",
        "region": "Gauteng",
        "password": "SecurePassword2026!",
        "categories": ["concrete", "earthworks"],
        "service_regions": ["Gauteng", "Mpumalanga"],
        "preferred_contact_method": "whatsapp",
        "compliance_flags": {"bbee_level": "1", "csd_number": "MAAA0998877", "csd_registered": True},
    }

    # 1. Register supplier
    response = await client.post("/api/v1/auth/register-supplier", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["organisation"]["legal_name"] == "Tshwane Quarry & Aggregate Supplies (Pty) Ltd"
    assert data["organisation"]["type"] == "supplier"
    assert data["organisation"]["region"] == "Gauteng"
    assert data["user"]["email"] == "kagiso@tshwaneaggregates.co.za"
    assert data["profile"]["categories"] == ["concrete", "earthworks"]
    assert data["profile"]["compliance_flags"]["csd_number"] == "MAAA0998877"

    # 2. Login with correct password
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "kagiso@tshwaneaggregates.co.za", "password": "SecurePassword2026!"},
    )
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()

    # 3. Login with incorrect password
    bad_login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "kagiso@tshwaneaggregates.co.za", "password": "WrongPassword!"},
    )
    assert bad_login_res.status_code == 401

    # 4. Attempt to register again with duplicate email -> should fail
    dup_res = await client.post("/api/v1/auth/register-supplier", json=payload)
    assert dup_res.status_code == 400


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
            "categories": ["building-materials", "roofing", "plumbing"],
            "service_regions": ["KwaZulu-Natal", "Eastern Cape"],
            "preferred_contact_method": "email",
            "compliance_flags": {"bbee_level": "2", "csd_registered": True},
            "active": True,
        },
    )
    assert update_res.status_code == 200
    updated = update_res.json()
    assert "roofing" in updated["categories"]
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
            "region": "KwaZulu-Natal",
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
        f"/api/v1/suppliers/quote-requests/{qr_id}?access_token={rfq_direct_token}"
    )
    assert mobile_view_res.status_code == 200
    mobile_data = mobile_view_res.json()
    assert mobile_data["id"] == qr_id
    assert mobile_data["line_item_quantity"] == 600
    assert mobile_data["line_item_unit"] == "no"

    # 5b. Supplier submits quote using only query access_token (NO prior login session)
    quote_submit_res = await client.post(
        f"/api/v1/quote-requests/{qr_id}/quotes?access_token={rfq_direct_token}",
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
        f"/api/v1/quote-requests/request-bbb/quotes?access_token={token_for_request_a}",
        json={"unit_price_minor": 5000, "currency": "ZAR"},
    )
    assert mismatch_res.status_code == 403
