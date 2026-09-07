import io
import re
from typing import Any, Dict, List, Optional, Tuple
import openpyxl
from app.domains.parsing.segmentation import (
    classify_candidate_line_item,
    clean_quantity_value,
    is_legal_or_narrative_noise,
)
from app.integrations.llm.base import ParseResultDTO, ParsedLineItemDTO
from app.integrations.llm.stub import CATEGORY_KEYWORDS, UNIT_NORMALIZATION

HEADER_SYNONYMS = {
    "ref": ["item", "item no", "item nr", "item #", "ref", "no", "code", "item_code", "section/item"],
    "description": ["description", "item description", "particulars", "specification", "work description", "details", "scope of work", "item details"],
    "unit": ["unit", "uom", "unit of measure", "measure", "item unit"],
    "quantity": [
        "qty", "quantity", "quantities", "amount of units", "est qty", "total qty",
        "estimated quantity", "estimated qty", "est. quantity", "est. qty", "est quantity",
        "tender qty", "tender quantity", "contract qty", "contract quantity", "boq qty", "boq quantity"
    ],
    "rate": ["rate", "unit rate", "unit price", "price", "tender rate"],
    "amount": ["amount", "total", "line total", "total amount", "extended price"],
}


def _infer_category(description: str) -> str:
    desc_lower = description.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in desc_lower for kw in keywords):
            return cat
    return "general-building"


def _normalize_unit(raw_unit: str) -> str:
    cleaned = str(raw_unit).strip().lower()
    return UNIT_NORMALIZATION.get(cleaned, "no")


def detect_sheet_header_columns(ws) -> Optional[Tuple[int, Dict[str, int]]]:
    """Inspects the first 25 rows of an Excel worksheet to detect structured BoQ table headers.
    Returns (header_row_idx_1_based, column_map: {'description': col_idx, 'unit': col_idx, ...})
    """
    for row_idx, row in enumerate(ws.iter_rows(values_only=True, max_row=25), start=1):
        if not row:
            continue
        
        row_str_cells = [str(c).strip().lower() for c in row if c is not None]
        if len(row_str_cells) < 2:
            continue
            
        col_map: Dict[str, int] = {}
        for col_idx, cell_value in enumerate(row):
            if cell_value is None:
                continue
            val_clean = str(cell_value).strip().lower()
            
            for field, synonyms in HEADER_SYNONYMS.items():
                if field not in col_map and any(val_clean == syn or val_clean.startswith(f"{syn} ") for syn in synonyms):
                    col_map[field] = col_idx
                    break
        
        # A valid structured BoQ header must have at least Description AND (Quantity or Unit)
        if "description" in col_map and ("quantity" in col_map or "unit" in col_map):
            return row_idx, col_map
            
    return None


def parse_structured_spreadsheet(
    document_bytes: bytes,
    filename: Optional[str] = None,
) -> Optional[ParseResultDTO]:
    """Deterministically parses structured Excel workbooks.
    If structured headers are found, extracts line items with 100% fidelity and 0 LLM hallucination.
    If unstructured / ambiguous, returns None so LLM pipeline can handle it.
    """
    try:
        wb = openpyxl.load_workbook(io.BytesIO(document_bytes), data_only=True)
    except Exception:
        return None

    all_line_items: List[ParsedLineItemDTO] = []
    all_excluded: List[ParsedLineItemDTO] = []
    sections_detected: List[str] = []
    
    title_hint = filename.replace(".xlsx", "").replace(".xls", "").replace("_", " ").title() if filename else "Tender BoQ Schedule"
    ref_hint = "TND-DET-EXCEL"

    found_structured_sheet = False

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        header_info = detect_sheet_header_columns(ws)
        if not header_info:
            continue
            
        found_structured_sheet = True
        header_row_idx, col_map = header_info
        
        section_name = f"Sheet: {sheet_name}"
        if section_name not in sections_detected:
            sections_detected.append(section_name)

        desc_col = col_map["description"]
        unit_col = col_map.get("unit")
        qty_col = col_map.get("quantity")
        ref_col = col_map.get("ref")

        row_num = 1
        for row in ws.iter_rows(values_only=True, min_row=header_row_idx + 1):
            if not row or len(row) <= desc_col:
                continue
                
            raw_desc = row[desc_col]
            if raw_desc is None:
                continue
                
            desc_str = str(raw_desc).strip()
            if not desc_str or len(desc_str) < 3:
                continue

            # Check if this row is a section header (e.g. "EARTHWORKS", "BILL NO. 2")
            if re.match(r'^(?:bill\s+no\.?\s*\d+|section\s+[a-z0-9]+|part\s+\d+)[\s:\-–]+(.+)', desc_str, re.I):
                sec_title = desc_str.strip().title()
                if sec_title not in sections_detected:
                    sections_detected.append(sec_title)
                section_name = sec_title
                continue

            # Unit
            raw_unit = str(row[unit_col]).strip() if unit_col is not None and len(row) > unit_col and row[unit_col] is not None else "no"
            unit = _normalize_unit(raw_unit)

            # Quantity
            qty = 1.0
            if qty_col is not None and len(row) > qty_col and row[qty_col] is not None:
                qty = clean_quantity_value(row[qty_col])

            # Ref
            raw_ref = str(row[ref_col]).strip() if ref_col is not None and len(row) > ref_col and row[ref_col] is not None else f"{row_num}"
            if len(raw_ref) > 20:
                raw_ref = f"{row_num}"

            # Two-stage Candidate Classification
            is_valid, conf, review_status, exclusion_reason = classify_candidate_line_item(
                description=desc_str,
                unit=unit,
                quantity=qty,
                raw_reference=raw_ref,
                section_name=section_name,
            )

            category = _infer_category(desc_str + " " + section_name)

            item_dto = ParsedLineItemDTO(
                source_row_reference=raw_ref,
                section_name=section_name,
                description=desc_str,
                unit=unit,
                quantity=qty,
                category=category,
                benchmark_min_minor=None,  # No fabricated benchmark pricing!
                benchmark_max_minor=None,
                benchmark_source=None,
                parsing_confidence=conf,
                review_status=review_status,
                exclusion_reason=exclusion_reason,
            )

            if is_valid and review_status != "excluded":
                all_line_items.append(item_dto)
            else:
                all_excluded.append(item_dto)
                
        row_num += 1

    if not found_structured_sheet or not all_line_items:
        return None

    return ParseResultDTO(
        title_hint=title_hint,
        tender_reference_hint=ref_hint,
        sections_detected=sections_detected,
        line_items=all_line_items,
        excluded_candidates=all_excluded,
        metadata={
            "parser_method": "deterministic_spreadsheet",
            "candidates_total": len(all_line_items) + len(all_excluded),
            "candidates_classified_valid": len(all_line_items),
            "candidates_excluded": len(all_excluded),
            "high_confidence_count": sum(1 for i in all_line_items if i.review_status == "accepted"),
            "needs_review_count": sum(1 for i in all_line_items if i.review_status == "needs_review"),
        },
    )


def extract_text_from_spreadsheet(document_bytes: bytes) -> str:
    """Safely extracts all text and values from an Excel workbook (.xlsx).
    Iterates across all sheets and rows to produce clean tabular text lines.
    Never falls back to raw binary or zip decoding.
    """
    try:
        wb = openpyxl.load_workbook(io.BytesIO(document_bytes), data_only=True)
        lines = []
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            lines.append(f"--- SHEET: {sheet_name} ---")
            for row in ws.iter_rows(values_only=True):
                row_vals = [str(v).strip() for v in row if v is not None and str(v).strip() != ""]
                if row_vals:
                    lines.append(" | ".join(row_vals))
        return "\n".join(lines)
    except Exception:
        return ""

