import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_generate_and_download_exports(client: AsyncClient, seeded_entities: dict):
    contractor_token = seeded_entities["contractor_token"]
    headers = {"Authorization": f"Bearer {contractor_token}"}

    # 1. Create BoQ with line items
    boq_res = await client.post(
        "/api/v1/boqs",
        json={"title": "Hospital Wing Tender", "tender_reference": "DOH-2026-01", "region": "KwaZulu-Natal"},
        headers=headers,
    )
    boq_id = boq_res.json()["id"]

    item_res = await client.post(
        f"/api/v1/boqs/{boq_id}/line-items",
        json={"description": "Plumbing fixtures", "quantity": 10.0, "unit": "no", "category": "plumbing"},
        headers=headers,
    )
    item_id = item_res.json()["id"]

    # Price the item
    await client.post(
        f"/api/v1/boqs/{boq_id}/line-items/{item_id}/price-override",
        json={"price_minor": 25000, "reason": "Standard rate guide"},
        headers=headers,
    )

    # 2. Generate Excel export
    excel_res = await client.post(
        f"/api/v1/boqs/{boq_id}/exports",
        json={"format": "xlsx"},
        headers=headers,
    )
    assert excel_res.status_code == 200
    excel_data = excel_res.json()
    assert excel_data["format"] == "xlsx"
    assert "download_url" in excel_data

    # Download Excel
    dl_excel = await client.get(excel_data["download_url"], headers=headers)
    assert dl_excel.status_code == 200
    assert len(dl_excel.content) > 0

    # 3. Generate PDF export
    pdf_res = await client.post(
        f"/api/v1/boqs/{boq_id}/exports",
        json={"format": "pdf"},
        headers=headers,
    )
    assert pdf_res.status_code == 200
    pdf_data = pdf_res.json()
    assert pdf_data["format"] == "pdf"

    # Download PDF
    dl_pdf = await client.get(pdf_data["download_url"], headers=headers)
    assert dl_pdf.status_code == 200
    assert len(dl_pdf.content) > 0
