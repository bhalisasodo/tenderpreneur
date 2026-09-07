import re
from typing import List, Optional
from app.domains.parsing.segmentation import (
    classify_candidate_line_item,
    clean_quantity_value,
    is_legal_or_narrative_noise,
    is_text_corrupted,
    segment_document_text,
)
from app.integrations.llm.base import LLMProvider, ParseResultDTO, ParsedLineItemDTO


CATEGORY_KEYWORDS = {
    "building-materials": ["cement", "brick", "block", "mortar", "plaster", "aggregate", "sand", "stone", "masonry"],
    "concrete": ["concrete", "ready-mix", "reinforcement", "rebar", "mesh", "formwork", "slab"],
    "earthworks": ["excavation", "trench", "backfill", "earthwork", "clearing", "grading", "soil", "compaction"],
    "roofing": ["truss", "sheeting", "corrugated", "tiles", "fascia", "gutters", "waterproofing", "insulation", "ibr"],
    "plumbing": ["pipe", "pvc", "copper", "drainage", "tap", "valve", "sanitary", "geyser", "basin", "toilet"],
    "electrical": ["cable", "conduit", "wire", "lighting", "luminaire", "distribution board", "db", "socket", "switch"],
    "finishes": ["paint", "primer", "tile", "screed", "ceiling", "drywall", "door", "window", "glazing"],
    "ppe": ["safety", "boots", "gloves", "helmet", "overalls", "hi-vis", "vest", "harness", "goggles", "hardhat"],
    "plant-hire": ["tipper", "excavator", "grader", "roller", "crane", "scaffolding", "generator", "tlb"],
}

UNIT_NORMALIZATION = {
    "m2": "m2", "sqm": "m2", "m²": "m2", "rn2": "m2",
    "m3": "m3", "cum": "m3", "m³": "m3", "rn3": "m3",
    "m": "m", "lm": "m", "metres": "m", "meter": "m", "meters": "m", "rn": "m",
    "kg": "kg", "ton": "ton", "t": "ton", "tonne": "ton", "tonnes": "ton",
    "no": "no", "nr": "no", "ea": "no", "each": "no", "item": "no", "units": "no",
    "sum": "sum", "prov sum": "sum", "prov. sum": "sum", "ps": "sum", "ls": "sum", "lump sum": "sum",
    "hr": "hr", "hrs": "hr", "hour": "hr", "hours": "hr", "day": "day", "days": "day", "week": "week", "month": "month",
    "ha": "ha", "km": "km", "l": "l", "litre": "l", "litres": "l",
    "pair": "pair", "set": "set", "sets": "set", "roll": "roll", "rolls": "roll", "bag": "bag", "bags": "bag",
}


class StubLLMProvider:
    """Intelligent heuristic and rule-based parser with segmentation and candidate classification."""

    def _infer_category(self, description: str) -> str:
        desc_lower = description.lower()
        for cat, keywords in CATEGORY_KEYWORDS.items():
            if any(kw in desc_lower for kw in keywords):
                return cat
        return "general-building"

    def _infer_unit(self, raw_unit: str) -> str:
        cleaned = raw_unit.strip().lower()
        return UNIT_NORMALIZATION.get(cleaned, "no")

    async def parse_boq_document(
        self,
        extracted_text: str,
        filename: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> ParseResultDTO:
        # Pre-extraction sanity check for garbled or corrupted text
        is_corrupted, ratio, corrupt_reason = is_text_corrupted(extracted_text, is_line_item=False)
        if is_corrupted:
            raise ValueError(f"GARBLED_DOCUMENT_TEXT: {corrupt_reason}")

        # Preprocessing: segment document text into candidates vs noise
        candidate_lines, raw_excluded = segment_document_text(extracted_text)

        line_items: List[ParsedLineItemDTO] = []
        excluded_candidates: List[ParsedLineItemDTO] = []

        title_hint = "Tender Scope of Work"
        ref_hint = "TND-2026-AUTO"

        for line in candidate_lines[:10]:
            if "tender" in line.lower() or "boq" in line.lower() or "bill" in line.lower():
                title_hint = line
            ref_match = re.search(r'([A-Z]{2,4}[-/\s]?[0-9]{3,8}[-/\w]*)', line)
            if ref_match and len(ref_match.group(1)) >= 4:
                ref_hint = ref_match.group(1).replace(" ", "-")

        current_section = "General Building Scope"
        sections_detected = []

        row_num = 1
        for line in candidate_lines:
            # Check for section or bill headers
            sec_match = re.search(r'^(bill\s+no\.?\s*\d+|section\s+[a-z0-9]+|part\s+\d+)[\s:\-–]+(.+)', line, re.I)
            if sec_match:
                current_section = f"{sec_match.group(1).title()}: {sec_match.group(2).strip()}"
                if current_section not in sections_detected:
                    sections_detected.append(current_section)
                continue
            elif re.match(r'^(earthworks|concrete|masonry|brickwork|roofing|plumbing|electrical|finishes|external works)', line, re.I):
                current_section = line.strip().title()
                if current_section not in sections_detected:
                    sections_detected.append(current_section)
                continue

            # Skip table column headers
            if re.match(r'^(item|no|description|qty|quantity|unit|rate|amount|bill)[\s|\t,;]', line, re.I):
                continue
            if len(line) < 4:
                continue

            # Tabular/delimited lines
            parts = re.split(r'[\t|,;]', line)
            if len(parts) >= 3:
                desc = parts[0].strip() if len(parts[0].strip()) > 5 else parts[1].strip()
                qty_raw = parts[-2].strip() if len(parts) >= 4 else parts[-1].strip()
                unit_raw = parts[-1].strip() if len(parts) >= 4 else "no"

                qty = clean_quantity_value(qty_raw)
                unit = self._infer_unit(unit_raw)
                ref = parts[0].strip() if (len(parts) >= 4 and len(parts[0].strip()) <= 12) else f"Row-{row_num}"

                is_valid, conf, review_status, reason = classify_candidate_line_item(
                    description=desc,
                    unit=unit,
                    quantity=qty,
                    raw_reference=ref,
                    section_name=current_section,
                )

                cat = self._infer_category(desc + " " + current_section)

                item_dto = ParsedLineItemDTO(
                    source_row_reference=ref,
                    section_name=current_section,
                    description=desc,
                    unit=unit,
                    quantity=qty,
                    category=cat,
                    benchmark_min_minor=None,
                    benchmark_max_minor=None,
                    benchmark_source=None,
                    parsing_confidence=conf,
                    review_status=review_status,
                    exclusion_reason=reason,
                )

                if is_valid and review_status != "excluded":
                    line_items.append(item_dto)
                else:
                    excluded_candidates.append(item_dto)
                row_num += 1

            else:
                # Regex heuristic for free text line items
                match = re.search(r'^(?:([\dA-Za-z.]+)\s+)?(.+?)\s+([R$]?\d+(?:[.,]\d+)?)\s*([a-zA-Z0-9²³\/]+)?$', line)
                if match:
                    ref = match.group(1) or f"Row-{row_num}"
                    desc = match.group(2).strip()
                    qty = clean_quantity_value(match.group(3))
                    unit = self._infer_unit(match.group(4) or "no")

                    is_valid, conf, review_status, reason = classify_candidate_line_item(
                        description=desc,
                        unit=unit,
                        quantity=qty,
                        raw_reference=ref,
                        section_name=current_section,
                    )

                    cat = self._infer_category(desc + " " + current_section)

                    item_dto = ParsedLineItemDTO(
                        source_row_reference=ref,
                        section_name=current_section,
                        description=desc,
                        unit=unit,
                        quantity=qty,
                        category=cat,
                        benchmark_min_minor=None,
                        benchmark_max_minor=None,
                        benchmark_source=None,
                        parsing_confidence=conf,
                        review_status=review_status,
                        exclusion_reason=reason,
                    )

                    if is_valid and review_status != "excluded":
                        line_items.append(item_dto)
                    else:
                        excluded_candidates.append(item_dto)
                    row_num += 1

        return ParseResultDTO(
            title_hint=title_hint,
            tender_reference_hint=ref_hint,
            sections_detected=sections_detected,
            line_items=line_items,
            excluded_candidates=excluded_candidates,
            metadata={
                "parser_method": "rule_based_stub",
                "candidates_total": len(line_items) + len(excluded_candidates),
                "candidates_classified_valid": len(line_items),
                "candidates_excluded": len(excluded_candidates),
                "high_confidence_count": sum(1 for i in line_items if i.review_status == "accepted"),
                "needs_review_count": sum(1 for i in line_items if i.review_status == "needs_review"),
            },
        )

    async def parse_boq_document_bytes(
        self,
        document_bytes: bytes,
        mime_type: str,
        filename: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> ParseResultDTO:
        import io
        mime = (mime_type or "").lower()
        fname = (filename or "").lower()

        # Deterministic Excel/CSV parsing first
        if "excel" in mime or "sheet" in mime or fname.endswith(".xlsx") or fname.endswith(".xls"):
            from app.domains.parsing.spreadsheet import parse_structured_spreadsheet, extract_text_from_spreadsheet
            det_res = parse_structured_spreadsheet(document_bytes, filename=filename)
            if det_res:
                return det_res

            # If not structured table, safely extract all cell text using openpyxl
            extracted_text = extract_text_from_spreadsheet(document_bytes)
            if not extracted_text or not extracted_text.strip():
                raise ValueError("EMPTY_OR_UNREADABLE_EXCEL: We could not extract any readable rows from this Excel document. Please ensure it is a valid, uncorrupted Excel (.xlsx) file.")
            return await self.parse_boq_document(extracted_text, filename=filename, context=context)

        # PDF documents
        if "pdf" in mime or fname.endswith(".pdf"):
            if not document_bytes.startswith(b"%PDF"):
                raise ValueError("INVALID_PDF_HEADER: The uploaded file does not have a valid PDF header.")

            try:
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(document_bytes))
                num_pages = len(reader.pages)
                if num_pages == 0:
                    raise ValueError("EMPTY_PDF: Uploaded PDF has 0 pages.")

                extracted = []
                for page_idx, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text:
                        extracted.append(f"--- PAGE {page_idx + 1} ---\n{text}")
                extracted_text = "\n\n".join(extracted)

                if not extracted_text or len(extracted_text.strip()) < 20:
                    raise ValueError(
                        "SCANNED_PDF_NO_TEXT_LAYER: We couldn't read any text from this PDF document. "
                        "It appears to be a scanned document or image-only PDF without a searchable digital text layer. "
                        "Try re-exporting it as a text-based PDF, or upload an Excel version if you have one."
                    )

            except ValueError:
                raise
            except Exception as e:
                raise ValueError(f"PDF_READ_ERROR: Failed to read PDF pages: {e}")

            return await self.parse_boq_document(extracted_text, filename=filename, context=context)

        # CSV and plain text files
        # Prevent binary zip/office/executable files from being decoded as text
        if document_bytes.startswith(b"PK\x03\x04") or b"\x00" in document_bytes[:1024]:
            raise ValueError(
                "BINARY_FILE_UPLOADED_AS_TEXT: Uploaded file contains binary data and cannot be read as plain text. "
                "Please upload a standard Excel (.xlsx) or text-based PDF document."
            )

        extracted_text = ""
        for encoding in ("utf-8-sig", "utf-8", "cp1252", "iso-8859-1"):
            try:
                extracted_text = document_bytes.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if not extracted_text or not extracted_text.strip():
            raise ValueError("TEXT_DECODING_FAILED: Could not decode document text with valid encoding.")

        return await self.parse_boq_document(extracted_text, filename=filename, context=context)

