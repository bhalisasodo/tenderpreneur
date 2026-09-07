import io
import openpyxl
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import BoQ, generate_uuid
from app.integrations.llm.stub import StubLLMProvider


def generate_sample_tender_excel() -> bytes:
    """Generates an in-memory .xlsx tender BoQ document."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Bill of Quantities"

    ws.append(["Item", "Description", "Quantity", "Unit", "Rate", "Amount"])
    ws.append(["1.01", "Excavation in earth for foundation trenches", 350.0, "m3", "", ""])
    ws.append(["1.02", "Supply and place 25MPa ready-mix concrete in footings", 110.0, "m3", "", ""])
    ws.append(["1.03", "Standard clay stock bricks in cement mortar", 25000.0, "no", "", ""])
    ws.append(["1.04", "50kg All-Purpose Portland Cement CEM II bags", 400.0, "no", "", ""])
    ws.append(["1.05", "Treated timber roof trusses designed to engineer specs", 260.0, "m2", "", ""])
    ws.append(["1.06", "0.5mm IBR Chromadek corrugated roof sheeting", 300.0, "m2", "", ""])
    ws.append(["1.07", "Personal Protective Equipment (PPE) sets: hardhats, boots", 25.0, "no", "", ""])

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_excel_stub_parsing():
    """Verify StubLLMProvider extracts line items from Excel binary bytes."""
    xlsx_bytes = generate_sample_tender_excel()
    provider = StubLLMProvider()

    result = await provider.parse_boq_document_bytes(
        document_bytes=xlsx_bytes,
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="Tender_Schedule.xlsx",
    )

    assert result is not None
    assert len(result.line_items) >= 7
    assert any(item.category == "earthworks" for item in result.line_items)
    assert any(item.category == "concrete" for item in result.line_items)
    assert any(item.category == "building-materials" for item in result.line_items)


@pytest.mark.asyncio
async def test_excel_api_upload_and_parse(
    db_session: AsyncSession,
    seeded_entities: dict,
    client: AsyncClient,
):
    """Verify full API flow: upload .xlsx file and parse into line items."""
    contractor_org = seeded_entities["contractor_org"]
    contractor_token = seeded_entities["contractor_token"]
    headers = {"Authorization": f"Bearer {contractor_token}"}

    create_res = await client.post(
        "/api/v1/boqs",
        headers=headers,
        json={
            "title": "Excel Ingestion Tender",
            "tender_reference": "XLSX-2026-001",
            "region": "KwaZulu-Natal",
        },
    )
    assert create_res.status_code == 201
    boq_id = create_res.json()["id"]

    xlsx_bytes = generate_sample_tender_excel()
    files = {
        "file": (
            "Tender_Schedule.xlsx",
            xlsx_bytes,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }
    upload_res = await client.post(
        f"/api/v1/boqs/{boq_id}/documents",
        headers=headers,
        files=files,
    )
    assert upload_res.status_code == 200

    parse_res = await client.post(
        f"/api/v1/boqs/{boq_id}/parse",
        headers=headers,
        json={},
    )
    assert parse_res.status_code == 200
    boq_data = parse_res.json()
    assert boq_data["status"] == "parsed"
    assert len(boq_data["line_items"]) >= 7


@pytest.mark.asyncio
async def test_messy_excel_parsing_with_dots_and_punctuation():
    """Verify parser does not crash on Excel files with dots or punctuation in quantity columns."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Schedule"
    ws.append(["Bill No. 1: Earthworks"])
    ws.append(["1.01", "Site Clearance and Topsoil", "...", "m2"])
    ws.append(["1.02", "Bulk Excavation in Trench", ".", "m3"])
    ws.append(["1.03", "Reinforced 25MPa Concrete Footings", "150.5", "m3"])

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    provider = StubLLMProvider()
    result = await provider.parse_boq_document_bytes(
        document_bytes=buffer.getvalue(),
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="Messy_BoQ.xlsx",
    )

    assert result is not None
    assert len(result.line_items) >= 3
    # Check that item 1.02 got defaulted safely to quantity 1.0 instead of crashing
    assert all(isinstance(item.quantity, float) for item in result.line_items)

