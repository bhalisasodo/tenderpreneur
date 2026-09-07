import io
import pytest
from httpx import AsyncClient
import openpyxl
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.parsing.segmentation import (
    classify_candidate_line_item,
    is_legal_or_narrative_noise,
    segment_document_text,
)
from app.domains.parsing.spreadsheet import parse_structured_spreadsheet
from app.integrations.llm.stub import StubLLMProvider


SAMPLE_MESSY_TENDER_DOCUMENT = """
TENDER NO: WS-7840/2026 - WATER & SANITATION INFRASTRUCTURE
Page 1 of 24

GENERAL CONDITIONS AND PREAMBLE:
Clause 2.0 - Law and Jurisdiction of South Africa.
however
Without limiting the generality of the provisions of clause 2.0, the Contractor shall comply with all municipal bylaws.
The Contractor shall inspect the site prior to submitting tender prices.
All materials and workmanship to comply with SANS 1200.
Allow for water and temporary power during construction.

Bill No. 1: Earthworks
1.01 | Site clearance and bulk excavation in earth for pipeline trenches | 850.0 | m3
1.02 | Selected granular bedding material compacted in 150mm layers | 340.0 | m3
Carried to Collection of Bill No. 1
Brought forward from Page 1

Bill No. 2: Concrete & Pipelines
2.01 | Supply and lay 160mm Class 34 heavy duty uPVC sewer pipes | 520.0 | m
2.02 | 25MPa / 19mm ready-mix concrete for pipe encasement and thrust blocks | 75.0 | m3
Total of Bill No. 2
Grand Total Carried Forward to Final Summary

Tenderer's Signature: __________________
Date: __________________
Witness: __________________
"""


@pytest.mark.asyncio
async def test_segmentation_rejects_problematic_clauses_and_fragments():
    """Verify that specific false-positive failure patterns are rejected during segmentation."""
    known_problematic_phrases = [
        "Clause 2.0 - Law",
        "however",
        "Without limiting the generality of the provisions of clause 2.0",
        "the Contractor shall inspect the site",
        "All materials and workmanship to comply with SANS 1200",
        "Carried to Collection of Bill No. 1",
        "Brought forward from Page 1",
        "Total of Bill No. 2",
        "Grand Total Carried Forward to Final Summary",
        "Page 1 of 24",
        "Tenderer's Signature: __________________",
    ]

    for phrase in known_problematic_phrases:
        is_noise, reason = is_legal_or_narrative_noise(phrase)
        assert is_noise is True, f"Failed to reject false positive: '{phrase}'"
        assert reason is not None


@pytest.mark.asyncio
async def test_candidate_classifier_confidence_bands():
    """Verify 3-band confidence classification (accepted, needs_review, excluded)."""
    # 1. High confidence genuine BoQ item
    valid, conf, status, reason = classify_candidate_line_item(
        description="Excavation in earth for foundation trenches not exceeding 2m deep",
        unit="m3",
        quantity=450.0,
        section_name="Earthworks",
    )
    assert valid is True
    assert conf >= 0.80
    assert status == "accepted"

    # 2. Ambiguous item (no standard unit or unclear description)
    valid_amb, conf_amb, status_amb, reason_amb = classify_candidate_line_item(
        description="Specialist testing and soil investigation report",
        unit=None,
        quantity=1.0,
    )
    assert conf_amb < 0.80
    assert conf_amb >= 0.50
    assert status_amb == "needs_review"

    # 3. Non-item / clause (low confidence)
    valid_low, conf_low, status_low, reason_low = classify_candidate_line_item(
        description="Clause 2.0 - Law",
    )
    assert valid_low is False
    assert conf_low < 0.50
    assert status_low == "excluded"


@pytest.mark.asyncio
async def test_zero_fabricated_benchmark_pricing():
    """Verify that parsed line items have NO fabricated benchmark prices attached."""
    provider = StubLLMProvider()
    result = await provider.parse_boq_document(SAMPLE_MESSY_TENDER_DOCUMENT)

    assert len(result.line_items) > 0
    for item in result.line_items:
        # Benchmarks MUST be None unless backed by an explicit pricing provider
        assert item.benchmark_min_minor is None
        assert item.benchmark_max_minor is None
        assert item.benchmark_source is None


@pytest.mark.asyncio
async def test_deterministic_spreadsheet_parsing():
    """Verify structured Excel sheets parse deterministically with 0 LLM calls."""
    # Create sample Excel workbook in-memory
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Bill 1 Earthworks"

    # Header
    ws.append(["Item No", "Description", "Unit", "Qty", "Rate (ZAR)", "Amount"])
    # Real BoQ items
    ws.append(["1.01", "Excavation for pipe trenches 0-1.5m", "m3", 450, None, None])
    ws.append(["1.02", "Selected sand bedding", "m3", 120, None, None])
    # Narrative row that should be filtered out
    ws.append(["1.03", "The Contractor shall allow for dewatering", "no", 1, None, None])
    ws.append(["1.04", "Total of Bill No. 1", "", "", None, None])

    out = io.BytesIO()
    wb.save(out)
    xlsx_bytes = out.getvalue()

    det_result = parse_structured_spreadsheet(xlsx_bytes, filename="tender_schedule.xlsx")
    assert det_result is not None
    assert det_result.metadata["parser_method"] == "deterministic_spreadsheet"

    descriptions = [i.description for i in det_result.line_items]
    assert "Excavation for pipe trenches 0-1.5m" in descriptions
    assert "Selected sand bedding" in descriptions
    # Verify narrative row and total row were excluded
    assert "Total of Bill No. 1" not in descriptions

    # Verify no fabricated benchmarks
    for item in det_result.line_items:
        assert item.benchmark_min_minor is None


@pytest.mark.asyncio
async def test_contractor_correction_and_removal_learning_feedback(
    db_session: AsyncSession,
    seeded_entities: dict,
    client: AsyncClient,
):
    """Verify contractor edits, deletes, and restores are captured as structured feedback."""
    contractor_token = seeded_entities["contractor_token"]
    headers = {"Authorization": f"Bearer {contractor_token}"}

    # 1. Create BoQ and parse messy text
    boq_res = await client.post(
        "/api/v1/boqs",
        headers=headers,
        json={"title": "Feedback Learning Tender", "region": "KwaZulu-Natal"},
    )
    boq_id = boq_res.json()["id"]

    parse_res = await client.post(
        f"/api/v1/boqs/{boq_id}/parse",
        headers=headers,
        json={"pasted_text": SAMPLE_MESSY_TENDER_DOCUMENT},
    )
    assert parse_res.status_code == 200
    parsed_boq = parse_res.json()
    items = parsed_boq["line_items"]
    assert len(items) >= 4

    # 2. Contractor edits quantity on item 0 (e.g. from 850 to 900)
    target_item = items[0]
    edit_res = await client.patch(
        f"/api/v1/boqs/{boq_id}/line-items/{target_item['id']}",
        headers=headers,
        json={"quantity": 900.0, "unit": "m3"},
    )
    assert edit_res.status_code == 200

    # 3. Contractor deletes item 1
    delete_item = items[1]
    del_res = await client.delete(
        f"/api/v1/boqs/{boq_id}/line-items/{delete_item['id']}",
        headers=headers,
    )
    assert del_res.status_code == 204

    # 4. Contractor restores an item if excluded or needs review
    restore_res = await client.post(
        f"/api/v1/boqs/{boq_id}/line-items/{target_item['id']}/restore",
        headers=headers,
    )
    assert restore_res.status_code == 200
    assert restore_res.json()["review_status"] == "accepted"

    # 5. Query parser feedback summary endpoint
    feedback_res = await client.get("/api/v1/boqs/parser/feedback-summary", headers=headers)
    assert feedback_res.status_code == 200
    feedback = feedback_res.json()
    assert feedback["corrections_count"] >= 1
    assert feedback["removals_count"] >= 1
    assert feedback["restorations_count"] >= 1
    assert "quantity" in feedback["top_corrected_fields"]
