import io
from datetime import datetime, timedelta, timezone
import openpyxl
import pytest
from httpx import AsyncClient
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import BoQ, LineItem, AuditEvent, generate_uuid
from app.domains.parsing.segmentation import is_text_corrupted, classify_candidate_line_item
from app.integrations.llm.stub import StubLLMProvider


def generate_scanned_image_like_pdf() -> bytes:
    """Generates a PDF without a text layer (simulating a scanned image document)."""
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    # Draw a line and rectangle without any drawString text
    p.rect(50, 50, width - 100, height - 100, stroke=1, fill=0)
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer.getvalue()


def generate_valid_tender_excel() -> bytes:
    """Generates an in-memory .xlsx tender BoQ document with clean data."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Bill of Quantities"

    ws.append(["Item", "Description", "Quantity", "Unit", "Rate", "Amount"])
    ws.append(["1.01", "Excavation in soft earth for foundation trenches", 350.0, "m3", "", ""])
    ws.append(["1.02", "Ready-mix 25MPa concrete in column footings to SANS 1200G", 110.0, "m3", "", ""])
    ws.append(["1.03", "Standard clay stock bricks in 1:4 cement mortar", 25000.0, "no", "", ""])

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_scanned_pdf_rejected_with_actionable_error(
    client: AsyncClient,
    seeded_entities: dict,
    db_session: AsyncSession,
):
    """Test 1: Uploading a scanned PDF with no text layer raises HTTP 422 with clear user guidance and logs audit event."""
    token = seeded_entities["contractor_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a BoQ
    create_res = await client.post(
        "/api/v1/boqs",
        json={"title": "Scanned Document Test Tender", "region": "KwaZulu-Natal"},
        headers=headers,
    )
    assert create_res.status_code == 201
    boq_id = create_res.json()["id"]

    # 2. Upload image-only / scanned PDF
    scanned_pdf_bytes = generate_scanned_image_like_pdf()
    upload_res = await client.post(
        f"/api/v1/boqs/{boq_id}/parse-file",
        files={"file": ("scanned_tender_plan.pdf", scanned_pdf_bytes, "application/pdf")},
        headers=headers,
    )

    # 3. Assert 422 with actionable scanned-document guidance
    assert upload_res.status_code == 422
    err_body = upload_res.json()
    assert err_body["error"]["code"] == "SCANNED_PDF_NO_TEXT_LAYER"
    assert "scanned document or image-only PDF" in err_body["error"]["message"]
    assert "searchable digital text layer" in err_body["error"]["message"]

    # 4. Verify audit event was logged via endpoint
    audit_res = await client.get(f"/api/v1/boqs/{boq_id}/audit", headers=headers)
    assert audit_res.status_code == 200
    events = audit_res.json()
    corrupt_events = [e for e in events if e["action"] == "boq.parse_failed_corrupted_text"]
    assert len(corrupt_events) >= 1
    assert corrupt_events[0]["metadata_json"]["error_code"] == "SCANNED_PDF_NO_TEXT_LAYER"


@pytest.mark.asyncio
async def test_binary_zip_disguised_file_rejected(
    client: AsyncClient,
    seeded_entities: dict,
    db_session: AsyncSession,
):
    """Test 2: Uploading binary zip archive content disguised as text/csv raises HTTP 422 and rejects byte-soup."""
    token = seeded_entities["contractor_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create BoQ
    create_res = await client.post(
        "/api/v1/boqs",
        json={"title": "Binary Zip Ingestion Test", "region": "Gauteng"},
        headers=headers,
    )
    boq_id = create_res.json()["id"]

    # 2. Craft binary content (PKZIP header followed by random binary bytes)
    corrupted_binary_bytes = b"PK\x03\x04\x14\x00\x00\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" + (b"\x00\xff\xfe\x01\x02\x03" * 50)
    upload_res = await client.post(
        f"/api/v1/boqs/{boq_id}/parse-file",
        files={"file": ("corrupted_schedule.csv", corrupted_binary_bytes, "text/csv")},
        headers=headers,
    )

    # 3. Assert 422 error
    assert upload_res.status_code == 422
    err_body = upload_res.json()
    assert err_body["error"]["code"] in ("BINARY_FILE", "GARBLED_DOCUMENT_TEXT")


@pytest.mark.asyncio
async def test_garbled_pasted_text_rejected(
    client: AsyncClient,
    seeded_entities: dict,
):
    """Test 3: Pasted text full of replacement characters and null bytes is rejected at the front door."""
    token = seeded_entities["contractor_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_res = await client.post(
        "/api/v1/boqs",
        json={"title": "Pasted Garbled Text Test", "region": "Western Cape"},
        headers=headers,
    )
    boq_id = create_res.json()["id"]

    # Text containing Unicode replacement characters and binary noise
    garbled_text = (
        "Item | Description | Quantity | Unit\n"
        "1.1 | \ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd | 100 | no\n"
        "1.2 | \ufffd\x00\ufffd\x00\ufffd\x00\ufffd\x00 | 50 | m\n"
    )

    parse_res = await client.post(
        f"/api/v1/boqs/{boq_id}/parse",
        json={"pasted_text": garbled_text},
        headers=headers,
    )
    assert parse_res.status_code == 422
    assert parse_res.json()["error"]["code"] == "GARBLED_DOCUMENT_TEXT"


@pytest.mark.asyncio
async def test_confidence_scores_vary_meaningfully():
    """Test 4: Parsing confidence is calibrated per-item and varies across technical clarity, not a static uniform score."""
    # Item 1: Highly specific technical item with SANS standard and strength rating
    is_valid1, conf1, classification1, reason1 = classify_candidate_line_item(
        raw_text="Supply and cast 30MPa / 19mm ready-mix concrete to SANS 1200G in reinforced ground floor columns",
        category="concrete",
        unit="m3",
        quantity=140.0,
    )

    # Item 2: Standard moderate description
    is_valid2, conf2, classification2, reason2 = classify_candidate_line_item(
        raw_text="Standard stock bricks",
        category="building-materials",
        unit="no",
        quantity=2500.0,
    )

    # Item 3: Ambiguous / short / unquantified item
    is_valid3, conf3, classification3, reason3 = classify_candidate_line_item(
        raw_text="Misc repair",
        category="general-building",
        unit="no",
        quantity=1.0,
    )

    # All should be valid items (or review), but confidence should be distinctly varied
    assert conf1 > conf2, f"Expected conf1 ({conf1}) > conf2 ({conf2})"
    assert conf2 > conf3, f"Expected conf2 ({conf2}) > conf3 ({conf3})"
    # Spread should be at least 0.15 between high and low
    assert (conf1 - conf3) >= 0.15, f"Confidence spread ({conf1} - {conf3} = {conf1 - conf3:.2f}) is too narrow!"
    # Ensure they are not uniform static numbers like 0.95
    assert len({conf1, conf2, conf3}) == 3, "Confidence scores collapsed to uniform values!"


@pytest.mark.asyncio
async def test_pre_broadcast_safety_gate_blocks_corrupted_line_items(
    client: AsyncClient,
    seeded_entities: dict,
):
    """Test 5: Pre-broadcast safety gate blocks quote request creation and broadcast for corrupted items."""
    token = seeded_entities["contractor_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create BoQ
    create_res = await client.post(
        "/api/v1/boqs",
        json={"title": "Safety Gate Broadcast Test", "region": "KwaZulu-Natal"},
        headers=headers,
    )
    boq_id = create_res.json()["id"]

    # 2. Add line item with Unicode replacement characters
    corrupt_item_res = await client.post(
        f"/api/v1/boqs/{boq_id}/line-items",
        json={
            "description": "50mm PVC pipe with \ufffd\ufffd\ufffd garbled fitting couplings",
            "unit": "m",
            "quantity": 200.0,
            "category": "plumbing",
        },
        headers=headers,
    )
    assert corrupt_item_res.status_code == 201
    corrupt_item_id = corrupt_item_res.json()["id"]

    # 3. Add clean line item
    clean_item_res = await client.post(
        f"/api/v1/boqs/{boq_id}/line-items",
        json={
            "description": "110mm Class 34 PVC underground sewer pipe",
            "unit": "m",
            "quantity": 150.0,
            "category": "plumbing",
        },
        headers=headers,
    )
    assert clean_item_res.status_code == 201
    clean_item_id = clean_item_res.json()["id"]

    # 4. Attempt to create Quote Request for corrupted item -> Should be BLOCKED with 422
    deadline = (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat()
    qr_blocked_res = await client.post(
        "/api/v1/quote-requests",
        json={"line_item_id": corrupt_item_id, "response_deadline": deadline},
        headers=headers,
    )
    assert qr_blocked_res.status_code == 422
    assert qr_blocked_res.json()["error"]["code"] == "CORRUPTED_LINE_ITEM"
    assert "garbled or corrupted text" in qr_blocked_res.json()["error"]["message"]

    # 5. Clean item Quote Request succeeds
    qr_clean_res = await client.post(
        "/api/v1/quote-requests",
        json={"line_item_id": clean_item_id, "response_deadline": deadline},
        headers=headers,
    )
    assert qr_clean_res.status_code == 201


@pytest.mark.asyncio
async def test_validate_broadcast_endpoint(
    client: AsyncClient,
    seeded_entities: dict,
):
    """Test 6: POST /api/v1/boqs/{boq_id}/validate-broadcast reports corrupt items before dispatch."""
    token = seeded_entities["contractor_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_res = await client.post(
        "/api/v1/boqs",
        json={"title": "Validation Endpoint Test", "region": "Gauteng"},
        headers=headers,
    )
    boq_id = create_res.json()["id"]

    # Item A: Clean
    item_a_res = await client.post(
        f"/api/v1/boqs/{boq_id}/line-items",
        json={
            "description": "50kg Portland Cement bags",
            "unit": "no",
            "quantity": 100.0,
            "category": "building-materials",
        },
        headers=headers,
    )
    id_a = item_a_res.json()["id"]

    # Item B: Corrupted with CID artifact
    item_b_res = await client.post(
        f"/api/v1/boqs/{boq_id}/line-items",
        json={
            "description": "Structural timber (cid:124) trusses (cid:89) spanning 6m",
            "unit": "no",
            "quantity": 12.0,
            "category": "roofing",
        },
        headers=headers,
    )
    id_b = item_b_res.json()["id"]

    # Validate both items -> Should return safe: False
    validate_both = await client.post(
        f"/api/v1/boqs/{boq_id}/validate-broadcast",
        json={"line_item_ids": [id_a, id_b]},
        headers=headers,
    )
    assert validate_both.status_code == 200
    res_both = validate_both.json()
    assert res_both["safe"] is False
    assert len(res_both["corrupted_items"]) == 1
    assert res_both["corrupted_items"][0]["line_item_id"] == id_b
    assert "PDF font CID characters" in res_both["corrupted_items"][0]["reason"]

    # Validate only clean item -> Should return safe: True
    validate_clean = await client.post(
        f"/api/v1/boqs/{boq_id}/validate-broadcast",
        json={"line_item_ids": [id_a]},
        headers=headers,
    )
    assert validate_clean.status_code == 200
    res_clean = validate_clean.json()
    assert res_clean["safe"] is True
    assert len(res_clean["corrupted_items"]) == 0


@pytest.mark.asyncio
async def test_valid_excel_extracts_clean_text():
    """Test 7: Valid Excel file parsing extracts clean line items without zip byte soup."""
    xlsx_bytes = generate_valid_tender_excel()
    provider = StubLLMProvider()

    result = await provider.parse_boq_document_bytes(
        document_bytes=xlsx_bytes,
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="Clean_BoQ.xlsx",
    )

    assert result is not None
    assert len(result.line_items) == 3
    for item in result.line_items:
        is_corrupt, score, reason = is_text_corrupted(item.description, is_line_item=True)
        assert not is_corrupt, f"Item description '{item.description}' was incorrectly flagged as corrupt ({reason})"
        assert "\ufffd" not in item.description
        assert "\x00" not in item.description
