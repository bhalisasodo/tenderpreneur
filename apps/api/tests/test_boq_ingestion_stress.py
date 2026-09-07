"""
Tenderpreneur BoQ Ingestion Stress Testing Suite
================================================
Exhaustive stress tests for real-world South African tender document parsing:
1. 100-Item Municipal Mega-Schedule throughput & category distribution
2. Dirty Excel workbook with merged headers, subtotals, and formatted comma strings
3. Adversarial legal specification & GCC 2015 clause noise filtering (>95% precision)
4. Degraded OCR scanning artifacts (glyph repairs: rn3 -> m3, rn2 -> m2, letter O -> 0)
5. Edge-case measurement units (ha, km, prov sum, bag, roll, pair, bay)
6. Multi-page PDF municipal tender document stress-testing via PyPDF
"""

import io
import time
import openpyxl
import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from pypdf import PdfReader


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        extracted = []
        for page_idx, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                extracted.append(f"--- PAGE {page_idx + 1} ---\n{text}")
        return "\n\n".join(extracted)
    except Exception:
        return ""
from app.domains.parsing.segmentation import (
    classify_candidate_line_item,
    clean_quantity_value,
    is_legal_or_narrative_noise,
)
from app.domains.parsing.spreadsheet import parse_structured_spreadsheet
from app.integrations.llm.stub import StubLLMProvider


# ==============================================================================
# TEST 1: 100-Item Municipal Mega-Schedule Throughput & Category Distribution
# ==============================================================================

@pytest.mark.asyncio
async def test_100_item_municipal_mega_schedule_throughput():
    """Generates a 100-item municipal tender across 8 construction trades and measures parsing performance."""
    trades = [
        ("Earthworks", "Bulk excavation in soft earth for stormwater attenuation pond", "m3", 1250.0, "earthworks"),
        ("Earthworks", "Trenching for 250mm sewer pipeline not exceeding 2.0m depth", "m3", 450.0, "earthworks"),
        ("Concrete", "Supply and place 30MPa / 19mm ready-mix concrete for pumpstation slab", "m3", 85.0, "concrete"),
        ("Concrete", "High tensile steel rebar cutting, bending and fixing in position", "ton", 14.5, "concrete"),
        ("Building-Materials", "Standard imperial face bricks in 1:4 cement mortar for substation", "no", 35000.0, "building-materials"),
        ("Building-Materials", "50kg All-purpose Portland cement bags CEM II 42.5N", "no", 500.0, "building-materials"),
        ("Roofing", "Timber roof trusses manufactured to SANS 10243 engineering standards", "m2", 280.0, "roofing"),
        ("Roofing", "0.58mm IBR Colorplus corrugated roof sheeting with insulation blanket", "m2", 320.0, "roofing"),
        ("Plumbing", "200mm Class 12 uPVC pressure water main pipeline with rubber rings", "m", 780.0, "plumbing"),
        ("Plumbing", "110mm heavy duty sewer pipe fittings, bends, junctions and gullies", "no", 45.0, "plumbing"),
        ("Electrical", "16mm2 4-core copper armoured electrical cable laid in trench", "m", 350.0, "electrical"),
        ("Electrical", "High-mast lighting 30m pole with LED luminaires and control panel", "no", 4.0, "electrical"),
        ("Finishes", "Two coats external acrylic PVA paint and primer on walls", "m2", 1200.0, "finishes"),
        ("Plant-Hire", "Hire of 20-ton tracked hydraulic excavator including operator and fuel", "day", 15.0, "plant-hire"),
        ("PPE", "Safety boots with steel toecap SABS approved for site operatives", "pair", 40.0, "ppe"),
    ]

    # Synthesize 100 lines
    lines = ["BILL OF QUANTITIES - BULK INFRASTRUCTURE CONTRACT REF: MIG-KZN-2026-99", "Item | Description | Quantity | Unit"]
    for i in range(1, 101):
        trade_spec = trades[(i - 1) % len(trades)]
        desc = f"{trade_spec[1]} (Section Ref {i:03d})"
        qty = trade_spec[3] + (i * 2.5)
        lines.append(f"{i:03d} | {desc} | {qty:.1f} | {trade_spec[2]}")

    scope_document = "\n".join(lines)

    start_time = time.time()
    provider = StubLLMProvider()
    result = await provider.parse_boq_document(scope_document, filename="Mega_Schedule_100_Items.txt")
    elapsed_time = time.time() - start_time

    # Performance benchmark: 100 items parsed in under 2.5 seconds
    assert elapsed_time < 2.5, f"Parsing 100 items took {elapsed_time:.2f}s, exceeding 2.5s threshold"

    # Integrity assertions
    assert result is not None
    assert len(result.line_items) == 100, f"Expected exactly 100 items, got {len(result.line_items)}"

    # Category diversity verification
    extracted_categories = {item.category for item in result.line_items}
    assert "earthworks" in extracted_categories
    assert "concrete" in extracted_categories
    assert "building-materials" in extracted_categories
    assert "roofing" in extracted_categories
    assert "plumbing" in extracted_categories
    assert "electrical" in extracted_categories
    assert "finishes" in extracted_categories
    assert "ppe" in extracted_categories

    # Verify confidence scores are within valid range (0.50 to 1.0)
    for item in result.line_items:
        assert 0.50 <= item.parsing_confidence <= 1.0
        assert item.quantity > 0


# ==============================================================================
# TEST 2: Dirty Excel Grid with Subtotals, Merged Headers & Comma Strings
# ==============================================================================

@pytest.mark.asyncio
async def test_dirty_excel_with_subtotals_and_commas():
    """Validates deterministic parsing of an Excel workbook containing comma-separated quantities,
    formatted Rands, interspersed subtotals, blank rows, and administrative signature notes."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Schedule of Rates"

    # Decorative header rows
    ws.append(["DEPARTMENT OF PUBLIC WORKS & INFRASTRUCTURE", "", "", "", "", ""])
    ws.append(["TENDER NO: DWP-2026/088 - CLINIC RESTORATION", "", "", "", "", ""])
    ws.append(["", "", "", "", "", ""])  # blank row

    # Table Header Row
    ws.append(["Item No", "Work Description", "UOM", "Estimated Quantity", "Tender Rate (ZAR)", "Total"])

    # Legitimate items with tricky quantity formats
    ws.append(["1.01", "Site establishment and removal of obstructions", "sum", 1.0, "", ""])
    ws.append(["1.02", "Bulk excavation in earth for storm foundations", "m3", "1,450.50", "", ""])  # String with comma thousand & dot decimal
    ws.append(["1.03", "Commercial ready-mix concrete 25MPa / 19mm stone", "m3", "12 500", "", ""])   # Space thousand separator
    ws.append(["1.04", "Solid clay stock bricks in cement mortar", "no", "25,000", "", ""])           # Comma thousand integer
    ws.append(["1.05", "High tensile deformed rebar cut and bent", "ton", "15,5", "", ""])            # Comma decimal format

    # Subtotal noise rows that MUST be excluded
    ws.append(["", "Subtotal of Bill No. 1: Earthworks & Civils", "", "", "R 185,000.00", ""])
    ws.append(["", "Carried forward to Collection of Schedule A", "", "", "", ""])
    ws.append(["", "", "", "", "", ""])

    # Section 2
    ws.append(["2.01", "Supply and lay 160mm Class 34 heavy duty uPVC pipe", "m", 320.0, "", ""])
    ws.append(["2.02", "Supply and install 0.58mm corrugated roof sheeting", "m2", "1 850,75", "", ""])

    # Summary & signature lines
    ws.append(["", "TOTAL OF SCHEDULE OF RATES CARRIED TO FORM OF OFFER", "", "", "", ""])
    ws.append(["", "Tenderer's Signature: __________________", "", "", "", ""])
    ws.append(["", "Date: 2026-09-03", "", "", "", ""])

    buffer = io.BytesIO()
    wb.save(buffer)
    excel_bytes = buffer.getvalue()

    # Parse with structured spreadsheet engine
    parsed = parse_structured_spreadsheet(excel_bytes, filename="Clinic_Schedule_Dirty.xlsx")

    assert parsed is not None
    assert len(parsed.line_items) == 7, f"Expected 7 legitimate trade items, got {len(parsed.line_items)}"

    item_map = {item.source_row_reference: item for item in parsed.line_items}

    # Verify quantities parsed accurately without truncation
    assert item_map["1.02"].quantity == 1450.5, f"Expected 1450.5, got {item_map['1.02'].quantity}"
    assert item_map["1.03"].quantity == 12500.0, f"Expected 12500.0, got {item_map['1.03'].quantity}"
    assert item_map["1.04"].quantity == 25000.0, f"Expected 25000.0, got {item_map['1.04'].quantity}"
    assert item_map["1.05"].quantity == 15.5, f"Expected 15.5, got {item_map['1.05'].quantity}"
    assert item_map["2.02"].quantity == 1850.75, f"Expected 1850.75, got {item_map['2.02'].quantity}"

    # Verify no subtotal or signature lines leaked into line items
    all_descriptions = " ".join([i.description.lower() for i in parsed.line_items])
    assert "subtotal" not in all_descriptions
    assert "carried forward" not in all_descriptions
    assert "tenderer's signature" not in all_descriptions


# ==============================================================================
# TEST 3: Adversarial Legal Specification & GCC 2015 Clause Filtering
# ==============================================================================

def test_adversarial_legal_clause_filtering_precision():
    """Tests noise filtering against 25 real-world South African contract preambles, GCC 2015 clauses,
    CIDB instructions, and SANS 1200 specifications."""
    legal_clauses = [
        "Clause 1.0 - Definitions and Interpretation under GCC 2015 3rd Edition",
        "Clause 2.1 - Law, Regulations and Jurisdiction of the Republic of South Africa",
        "Clause 4.3 - Contractor's general obligations regarding health and safety",
        "Clause 5.1 - Time for practical completion shall be twenty-four (24) calendar months",
        "Clause 6.2 - Security and Performance Guarantee in the amount of 10% of tender sum",
        "Clause 8.1 - Rates shall include all royalties, municipal fees and transport levies",
        "Clause 10.4 - Claims for delay due to adverse climatic conditions must be submitted in 7 days",
        "Clause 14.2 - Termination of contract by the Employer upon default of contractor",
        "The Contractor shall inspect the site and thoroughly acquaint themselves with all conditions",
        "The Employer reserves the right to accept any tender and not necessarily the lowest tender",
        "All materials, plant and workmanship shall comply strictly with SANS 1200 standards",
        "Allow for water, lighting, temporary sanitary facilities and security during the works",
        "Without limiting the generality of the provisions of clause 4, the Contractor must comply",
        "No claim for extra payment will be entertained on the grounds of lack of knowledge",
        "The Contractor is referred to the Occupational Health and Safety Act 85 of 1993",
        "Carried to Collection of Bill No. 1",
        "Brought Forward from Page 12",
        "Total of Section 2: Concrete, Formwork & Reinforcement",
        "Grand Total Carried Forward to Final Summary Page",
        "Page 7 of 48",
        "Tenderer's Authorised Signature: _______________________",
        "Witness Signature: _______________________",
        "however",
        "furthermore",
        "General Conditions of Contract for Construction Works (GCC 2015)",
    ]

    legitimate_trade_items = [
        ("Bulk excavation in intermediate material for pipeline bedding", "m3", 450.0),
        ("Supply and place 25MPa / 19mm ready-mix concrete in foundation footings", "m3", 65.0),
        ("High tensile steel reinforcing bars (rebar) to SANS 920", "ton", 8.2),
        ("0.58mm Zincalume IBR roof sheeting with 75mm glasswool insulation", "m2", 420.0),
        ("Supply and install 110mm Class 34 heavy duty uPVC drainage pipes", "m", 280.0),
    ]

    # Verify all 25 legal clauses are rejected as noise
    for clause in legal_clauses:
        is_noise, reason = is_legal_or_narrative_noise(clause)
        assert is_noise is True, f"Failed to filter legal clause: '{clause}'"

        # Verify classifier also rejects them
        is_valid, conf, review_status, _ = classify_candidate_line_item(clause)
        assert is_valid is False or review_status == "excluded", f"Classifier accepted legal noise: '{clause}'"

    # Verify all 5 genuine items are accepted
    for desc, unit, qty in legitimate_trade_items:
        is_noise, _ = is_legal_or_narrative_noise(desc)
        assert is_noise is False, f"Erroneously flagged legitimate item as noise: '{desc}'"

        is_valid, conf, review_status, _ = classify_candidate_line_item(desc, unit=unit, quantity=qty)
        assert is_valid is True, f"Classifier rejected legitimate item: '{desc}'"
        assert review_status != "excluded"
        assert conf >= 0.70


# ==============================================================================
# TEST 4: Degraded OCR Scanning Artifacts & Glyph Repairs
# ==============================================================================

@pytest.mark.asyncio
async def test_degraded_ocr_glyph_repairs():
    """Tests parser resilience against common OCR corruption:
    - 'rn3' -> 'm3'
    - 'rn2' -> 'm2'
    - 'rn'  -> 'm'
    - 'l.Ol' -> '1.01'
    - '12OO.O' -> 1200.0 (letter O instead of zero 0)
    - 'l4.5' -> 14.5 (letter l instead of digit 1)
    """
    ocr_raw_text = """
    SCHEDULE OF QUANTITIES - WATER RETICULATION PIPELINE
    Item | Description | Quantity | Unit
    l.Ol | Clear site and strip vegetative topsoil to 15Omm depth | 12OO.O | rn2
    2.Ol | 3OMPa ready-mix concrete for reservoir wall encasement | 85.O | rn3
    3.Ol | High tensile deformed steel rebar cut and bent to schedule | l4.5 | ton
    4.Ol | 2OOmm Class 16 uPVC bulk pressure water pipeline | 65O | rn
    5.Ol | High-visibility reflective safety vests and hard hats | 5O | no
    """

    provider = StubLLMProvider()
    result = await provider.parse_boq_document(ocr_raw_text, filename="Scanned_Tender_OCR.txt")

    assert result is not None
    assert len(result.line_items) == 5, f"Expected 5 OCR items, got {len(result.line_items)}"

    # Item 1: rn2 -> m2 and 1200.0
    item1 = result.line_items[0]
    assert item1.unit == "m2", f"Expected 'm2' from 'rn2', got '{item1.unit}'"
    assert item1.quantity == 1200.0, f"Expected 1200.0, got {item1.quantity}"

    # Item 2: rn3 -> m3 and 85.0
    item2 = result.line_items[1]
    assert item2.unit == "m3", f"Expected 'm3' from 'rn3', got '{item2.unit}'"
    assert item2.quantity == 85.0, f"Expected 85.0, got {item2.quantity}"

    # Item 3: l4.5 -> 14.5 ton
    item3 = result.line_items[2]
    assert item3.unit == "ton"
    assert item3.quantity == 14.5, f"Expected 14.5 from 'l4.5', got {item3.quantity}"

    # Item 4: rn -> m and 650.0
    item4 = result.line_items[3]
    assert item4.unit == "m", f"Expected 'm' from 'rn', got '{item4.unit}'"
    assert item4.quantity == 650.0, f"Expected 650.0, got {item4.quantity}"

    # Item 5: 5O -> 50.0
    item5 = result.line_items[4]
    assert item5.unit == "no"
    assert item5.quantity == 50.0, f"Expected 50.0 from '5O', got {item5.quantity}"


# ==============================================================================
# TEST 5: Edge-Case Measurement Units & Provisional Sums
# ==============================================================================

@pytest.mark.asyncio
async def test_edge_case_units_and_provisional_sums():
    """Validates less common South African civil construction measurement units and provisional sums."""
    unusual_units_text = """
    1.01 | Bush clearing and eradication of alien vegetation | 4.5 | ha
    1.02 | Sub-base gravelling and grading on rural access road | 12.8 | km
    1.03 | Bituminous tack coat emulsion sprayed on asphalt surface | 3500 | litre
    1.04 | Geotextile membrane filter fabric needle-punched | 25 | roll
    1.05 | SABS approved heavy-duty leather safety work gloves | 60 | pair
    1.06 | Allow the Provisional Sum for Eskom power connection grid tie-in | 1 | prov sum
    1.07 | Allow Prime Cost (PC) Sum for specialist telemetry telemetry system | 1 | sum
    1.08 | Cement CEM II 42.5N in 50kg waterproof multi-wall paper packaging | 300 | bag
    """

    provider = StubLLMProvider()
    result = await provider.parse_boq_document(unusual_units_text, filename="Unusual_Units.txt")

    assert result is not None
    assert len(result.line_items) == 8

    unit_results = {item.source_row_reference: (item.unit, item.quantity) for item in result.line_items}

    # Verify unit mappings
    assert unit_results["1.01"] == ("ha", 4.5)
    assert unit_results["1.02"] == ("km", 12.8)
    assert unit_results["1.03"] == ("l", 3500.0)
    assert unit_results["1.04"] == ("roll", 25.0)
    assert unit_results["1.05"] == ("pair", 60.0)
    assert unit_results["1.06"] == ("sum", 1.0)
    assert unit_results["1.07"] == ("sum", 1.0)
    assert unit_results["1.08"] == ("bag", 300.0)


# ==============================================================================
# TEST 6: Multi-Page Real-World PDF Municipality Tender Stress via PyPDF
# ==============================================================================

@pytest.mark.asyncio
async def test_multipage_pdf_stress_with_pypdf():
    """Builds a 5-page real PDF with ReportLab containing document headers, GCC preambles,
    and multiple bill sections, and verifies that PyPDF extraction feeds cleanly into the parser."""
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Page 1: Tender cover & GCC Preambles (pure noise)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, height - 50, "MOGALE CITY LOCAL MUNICIPALITY")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 70, "Tender Reference: MLM-ENG-2026-042")
    p.drawString(50, height - 85, "General Conditions of Contract: GCC 2015 3rd Edition")
    p.drawString(50, height - 105, "Clause 1.0 - The Contractor shall comply with all safety regulations.")
    p.drawString(50, height - 120, "Clause 2.0 - Law and Jurisdiction of South Africa.")
    p.drawString(50, height - 135, "All materials and workmanship to comply with SANS 1200.")
    p.drawString(50, height - 150, "Page 1 of 5")
    p.showPage()

    # Pages 2 to 4: Real Bills
    bill_data = [
        ("Bill No. 1: Earthworks & Site Clearance", [
            ("1.01 | Clear site and excavate foundation trench | 350 | m3"),
            ("1.02 | Compacted soil subgrade backfill | 180 | m3"),
        ]),
        ("Bill No. 2: Concrete, Formwork & Rebar", [
            ("2.01 | 30MPa ready-mix concrete in column bases | 65 | m3"),
            ("2.02 | High tensile deformed steel rebar | 8 | ton"),
        ]),
        ("Bill No. 3: Plumbing & Infrastructure", [
            ("3.01 | 160mm Class 34 heavy duty uPVC sewer pipe | 450 | m"),
            ("3.02 | Cast iron 110mm double socket gate valves | 4 | no"),
        ]),
    ]

    for page_idx, (bill_title, bill_items) in enumerate(bill_data, start=2):
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, height - 50, bill_title)
        p.drawString(50, height - 65, "Item | Description | Quantity | Unit")
        p.line(50, height - 70, width - 50, height - 70)

        y = height - 90
        p.setFont("Helvetica", 9)
        for item_str in bill_items:
            p.drawString(50, y, item_str)
            y -= 25

        p.setFont("Helvetica-Oblique", 8)
        p.drawString(50, 40, f"Page {page_idx} of 5 - Mogale City MLM-ENG-2026-042")
        p.drawString(width - 200, 40, "Carried forward to summary")
        p.showPage()

    # Page 5: Summary & Signatures (pure noise)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 50, "SUMMARY OF BILLS & FORM OF OFFER")
    p.drawString(50, height - 70, "Grand Total Carried Forward to Final Summary")
    p.drawString(50, height - 110, "Tenderer's Signature: ________________________")
    p.drawString(50, height - 130, "Date: 2026-09-03")
    p.drawString(50, 40, "Page 5 of 5")
    p.showPage()

    p.save()
    pdf_bytes = buffer.getvalue()

    # Extract text using PyPDF
    extracted_text = extract_text_from_pdf(pdf_bytes)
    assert len(extracted_text) > 200

    # Parse with StubLLMProvider
    provider = StubLLMProvider()
    result = await provider.parse_boq_document(extracted_text, filename="Mogale_Tender.pdf")

    assert result is not None
    # Verify exactly 6 legitimate items from pages 2, 3, 4 were extracted
    assert len(result.line_items) == 6, f"Expected 6 legitimate items, got {len(result.line_items)}"

    # Verify pages 1 & 5 noise was rejected
    extracted_descs = " ".join([item.description.lower() for item in result.line_items])
    assert "clause 1.0" not in extracted_descs
    assert "jurisdiction" not in extracted_descs
    assert "grand total" not in extracted_descs
    assert "signature" not in extracted_descs
