import io
import re
import csv
from typing import Any, Dict, List, Optional, Tuple
import openpyxl
from app.domains.parsing.segmentation import (
    classify_candidate_line_item,
    clean_quantity_value,
    is_legal_or_narrative_noise,
    quantity_needs_review,
)
from app.integrations.llm.base import ParseResultDTO, ParsedLineItemDTO
from app.integrations.llm.stub import CATEGORY_KEYWORDS, UNIT_NORMALIZATION


class _RowsWorksheet:
    def __init__(self, rows: List[Tuple[Any, ...]]):
        self.rows = rows

    def iter_rows(self, values_only: bool = False, max_row: Optional[int] = None, min_row: int = 1):
        end = max_row if max_row is not None else len(self.rows)
        return iter(self.rows[min_row - 1:end])


def _load_worksheets(document_bytes: bytes, filename: Optional[str] = None):
    if (filename or "").lower().endswith(".xls") and not (filename or "").lower().endswith(".xlsx"):
        import xlrd

        workbook = xlrd.open_workbook(file_contents=document_bytes)
        return [
            (
                sheet.name,
                _RowsWorksheet(
                    [tuple(value if value != "" else None for value in sheet.row_values(row_idx))
                     for row_idx in range(sheet.nrows)]
                ),
            )
            for sheet in workbook.sheets()
        ]

    workbook = openpyxl.load_workbook(io.BytesIO(document_bytes), data_only=True)
    return [(sheet_name, workbook[sheet_name]) for sheet_name in workbook.sheetnames]

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
        worksheets = _load_worksheets(document_bytes, filename)
    except Exception:
        return None

    all_line_items: List[ParsedLineItemDTO] = []
    all_excluded: List[ParsedLineItemDTO] = []
    sections_detected: List[str] = []
    
    title_hint = filename.replace(".xlsx", "").replace(".xls", "").replace("_", " ").title() if filename else "Tender BoQ Schedule"
    ref_hint = "TND-DET-EXCEL"

    found_structured_sheet = False

    for sheet_name, ws in worksheets:
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

        for row_num, row in enumerate(
            ws.iter_rows(values_only=True, min_row=header_row_idx + 1),
            start=header_row_idx + 1,
        ):
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

            is_noise, noise_reason = is_legal_or_narrative_noise(desc_str)
            if is_noise:
                excluded_item = ParsedLineItemDTO(
                    source_row_reference=f"{row_num}",
                    section_name=section_name,
                    description=desc_str,
                    unit=_normalize_unit(str(row[unit_col]).strip() if unit_col is not None and len(row) > unit_col and row[unit_col] is not None else "no"),
                    quantity=clean_quantity_value(row[qty_col] if qty_col is not None and len(row) > qty_col else None),
                    category=_infer_category(desc_str + " " + section_name),
                    benchmark_min_minor=None,
                    benchmark_max_minor=None,
                    benchmark_source=None,
                    parsing_confidence=0.15,
                    review_status="excluded",
                    exclusion_reason=noise_reason,
                )
                all_excluded.append(excluded_item)
                continue

            # Missing fields use a display placeholder but must remain visibly reviewable.
            raw_unit = str(row[unit_col]).strip() if unit_col is not None and len(row) > unit_col and row[unit_col] is not None else ""
            missing_unit = not raw_unit
            if missing_unit:
                raw_unit = "no"
            unit = _normalize_unit(raw_unit)

            # Quantity
            raw_quantity = row[qty_col] if qty_col is not None and len(row) > qty_col else None
            quantity_parse_failed = quantity_needs_review(raw_quantity)
            qty = clean_quantity_value(raw_quantity)

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
            if missing_unit or quantity_parse_failed:
                is_valid = True
                review_status = "needs_review"
                conf = min(conf, 0.55)
                missing_fields = []
                if missing_unit:
                    missing_fields.append("unit")
                if quantity_parse_failed:
                    missing_fields.append("quantity")
                exclusion_reason = f"Confirm missing or unreadable source {' and '.join(missing_fields)}."

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
                
    if not found_structured_sheet or not (all_line_items or all_excluded):
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


def parse_structured_csv(document_bytes: bytes, filename: Optional[str] = None) -> Optional[ParseResultDTO]:
    text = None
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "iso-8859-1"):
        try:
            text = document_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        return None

    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    for row in csv.reader(io.StringIO(text)):
        worksheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return parse_structured_spreadsheet(buffer.getvalue(), filename=filename)


def extract_text_from_spreadsheet(document_bytes: bytes, filename: Optional[str] = None) -> str:
    """Safely extracts all text and values from an Excel workbook (.xlsx).
    Iterates across all sheets and rows to produce clean tabular text lines.
    Never falls back to raw binary or zip decoding.
    """
    try:
        worksheets = _load_worksheets(document_bytes, filename)
        lines = []
        for sheet_name, ws in worksheets:
            lines.append(f"--- SHEET: {sheet_name} ---")
            for row in ws.iter_rows(values_only=True):
                row_vals = [str(v).strip() for v in row if v is not None and str(v).strip() != ""]
                if row_vals:
                    lines.append(" | ".join(row_vals))
        return "\n".join(lines)
    except Exception:
        return ""
