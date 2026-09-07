import io
import pytest
from httpx import AsyncClient
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import BoQ, generate_uuid
from app.integrations.llm.stub import StubLLMProvider
from app.integrations.llm.gemini import GeminiLLMProvider


def generate_sample_multipage_tender_pdf() -> bytes:
    """Generates an in-memory 3-page South African municipal tender BoQ PDF schedule."""
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # --- PAGE 1: Tender Header & Bill 1: Earthworks ---
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, height - 50, "eThekwini Municipality - Water & Sanitation Directorate")
    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, height - 70, "Tender Ref: WS-7840/2026 - Bulk Pipeline Infrastructure Upgrade")
    p.setFont("Helvetica", 9)
    p.drawString(50, height - 85, "Bill of Quantities Schedule of Prices (Page 1 of 3)")

    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, height - 120, "Bill No. 1: Earthworks & Site Clearance")
    p.line(50, height - 125, width - 50, height - 125)

    p.setFont("Helvetica-Bold", 9)
    p.drawString(50, height - 145, "Item | Description | Qty | Unit")
    p.setFont("Helvetica", 9)
    p.drawString(50, height - 165, "1.01 | Clear and strip site of vegetation and topsoil | 1200 | m2")
    p.drawString(50, height - 185, "1.02 | Excavation in soft earth for pipe trenches not exceeding 2.5m | 650 | m3")
    p.drawString(50, height - 205, "1.03 | Selected granular bedding and backfilling compacted to 93% Mod AASHTO | 420 | m3")
    p.showPage()

    # --- PAGE 2: Bill No. 2: Concrete, Formwork & Reinforcement ---
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 50, "Bill No. 2: Concrete, Formwork & Reinforcement")
    p.line(50, height - 55, width - 50, height - 55)

    p.setFont("Helvetica-Bold", 9)
    p.drawString(50, height - 75, "Item | Description | Qty | Unit")
    p.setFont("Helvetica", 9)
    p.drawString(50, height - 95, "2.01 | Mass concrete 15MPa for pipe anchor blocks and thrust cradles | 85 | m3")
    p.drawString(50, height - 115, "2.02 | Reinforced 30MPa / 19mm concrete in valve inspection chambers | 140 | m3")
    p.drawString(50, height - 135, "2.03 | High tensile deformed steel reinforcement bars (rebar) | 12 | ton")
    p.drawString(50, height - 155, "2.04 | Rough vertical formwork to sides of chamber foundation walls | 190 | m2")
    p.showPage()

    # --- PAGE 3: Bill No. 3: Pipework, Drainage & Fencing ---
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 50, "Bill No. 3: Pipework, Drainage & Security Fencing")
    p.line(50, height - 55, width - 50, height - 55)

    p.setFont("Helvetica-Bold", 9)
    p.drawString(50, height - 75, "Item | Description | Qty | Unit")
    p.setFont("Helvetica", 9)
    p.drawString(50, height - 95, "3.01 | 300mm Class 16 uPVC bulk pressure water pipeline with rubber rings | 850 | m")
    p.drawString(50, height - 115, "3.02 | Standard double flange cast iron gate valves 300mm | 6 | no")
    p.drawString(50, height - 135, "3.03 | 2.1m high galvanised anti-climb security mesh perimeter fence | 320 | m")
    p.drawString(50, height - 155, "3.04 | Personal Protective Equipment (PPE) site kits for civils team | 30 | no")
    p.showPage()

    p.save()
    buffer.seek(0)
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_multipage_pdf_stub_parsing():
    """Verify StubLLMProvider extracts line items and sections across all 3 pages of a PDF."""
    pdf_bytes = generate_sample_multipage_tender_pdf()
    provider = StubLLMProvider()

    result = await provider.parse_boq_document_bytes(
        document_bytes=pdf_bytes,
        mime_type="application/pdf",
        filename="eThekwini_WS_7840.pdf",
    )

    assert result is not None
    assert len(result.line_items) >= 9
    assert any("Earthworks" in sec for sec in result.sections_detected)
    assert any("Concrete" in sec for sec in result.sections_detected)
    assert any(item.category == "earthworks" for item in result.line_items)
    assert any(item.category == "concrete" for item in result.line_items)
    assert any(item.category == "plumbing" for item in result.line_items)


@pytest.mark.asyncio
async def test_multipage_pdf_gemini_fallback():
    """Verify GeminiLLMProvider falls back cleanly on multi-page PDF bytes when offline."""
    pdf_bytes = generate_sample_multipage_tender_pdf()
    provider = GeminiLLMProvider(api_key=None)

    result = await provider.parse_boq_document_bytes(
        document_bytes=pdf_bytes,
        mime_type="application/pdf",
        filename="eThekwini_WS_7840.pdf",
    )

    assert result is not None
    assert len(result.line_items) >= 9
    assert result.title_hint is not None


@pytest.mark.asyncio
async def test_multipage_pdf_api_upload_and_parse(
    db_session: AsyncSession,
    seeded_entities: dict,
    client: AsyncClient,
):
    """End-to-end API test: upload multi-page PDF document to BoQ and trigger parse."""
    contractor_org = seeded_entities["contractor_org"]
    contractor_token = seeded_entities["contractor_token"]
    headers = {"Authorization": f"Bearer {contractor_token}"}

    # 1. Create empty BoQ
    create_res = await client.post(
        "/api/v1/boqs",
        headers=headers,
        json={
            "title": "eThekwini Bulk Water Upgrade",
            "tender_reference": "WS-7840/2026",
            "region": "KwaZulu-Natal",
        },
    )
    assert create_res.status_code == 201
    boq_id = create_res.json()["id"]

    # 2. Upload PDF file
    pdf_bytes = generate_sample_multipage_tender_pdf()
    files = {"file": ("eThekwini_WS_7840.pdf", pdf_bytes, "application/pdf")}
    upload_res = await client.post(
        f"/api/v1/boqs/{boq_id}/documents",
        headers=headers,
        files=files,
    )
    assert upload_res.status_code == 200

    # 3. Parse BoQ document
    parse_res = await client.post(
        f"/api/v1/boqs/{boq_id}/parse",
        headers=headers,
        json={},
    )
    assert parse_res.status_code == 200
    boq_data = parse_res.json()
    assert boq_data["status"] == "parsed"
    assert len(boq_data["line_items"]) >= 9
