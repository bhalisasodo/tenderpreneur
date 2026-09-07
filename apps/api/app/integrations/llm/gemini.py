import base64
import json
import logging
import time
from typing import Any, Dict, List, Optional
import httpx
from app.core.config import settings
from app.domains.parsing.segmentation import (
    classify_candidate_line_item,
    is_legal_or_narrative_noise,
)
from app.integrations.llm.base import LLMProvider, ParseResultDTO, ParsedLineItemDTO
from app.integrations.llm.stub import UNIT_NORMALIZATION, StubLLMProvider

logger = logging.getLogger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SYSTEM_PROMPT = """You are an expert South African Quantity Surveyor (QS) and Tender BoQ Parsing AI.
Your task is to parse unstructured, tabular, or scanned tender Bills of Quantities (BoQ), Scopes of Work, or Schedule of Quantities documents into a clean list of ACTIONABLE, MEASURABLE procurement line items.

CRITICAL PRECISION & NOISE FILTERING RULES (DO NOT EXTRACT THE FOLLOWING):
1. NEGATIVE CLAUSE PATTERNS:
   - Contract / Legal Clauses: DO NOT extract clauses such as 'Clause 2.0 - Law', 'Clause 14.1 - Variations', 'Section 1: General Conditions'.
   - Narrative Transitions & Sentence Fragments: DO NOT extract standalone words or clause continuations like 'however', 'furthermore', 'notwithstanding', 'moreover'.
   - Contractor / Employer Legal Instructions: DO NOT extract legal narrative text like 'Without limiting the generality of the provisions of clause 2.0', 'The Contractor shall inspect the site prior to tendering', 'The Employer reserves the right to accept any tender'.
   - General Preambles & Specifications: DO NOT extract notes like 'All workmanship and materials to comply with SANS 1200', 'Allow for water and lighting during construction'.
2. ACCOUNTING & COLLECTION ROWS:
   - DO NOT extract accounting subtotals: 'Carried to Collection', 'Brought Forward', 'Total of Bill No. 2', 'Grand Total Carried to Final Summary'.
3. ADMINISTRATIVE & SIGNATURE ROWS:
   - DO NOT extract page numbers ('Page 1 of 12'), signature lines ('Tenderer Signature: ____'), date stamps, or empty headers.

ACTIONABLE PRICEABLE ITEMS TO EXTRACT:
Extract ONLY items representing physical materials, construction labour packages, earthworks, concrete, structural steel, roofing, plumbing, electrical, finishes, plant hire, or measurable bill items with descriptions, units, and quantities.

For each item, identify:
1. source_row_reference: The original item/row reference number (e.g., '1.01', 'A.2', '2.14', 'Item 3').
2. section_name: The Bill / Section header (e.g. 'Bill No. 1: Earthworks', 'Bill No. 2: Concrete, Formwork & Rebar', 'Bill No. 3: Masonry', 'Bill No. 4: Roofing', 'Bill No. 5: Plumbing', 'Bill No. 6: Electrical').
3. description: The clear description of the material, labour, or work.
4. unit: Normalized unit of measurement (e.g. 'm2', 'm3', 'kg', 'no', 'sum', 'm', 'ton', 'hr', 'day', 'item').
5. quantity: Numeric quantity (float). Default to 1.0 if not specified.
6. category: One of standard trade categories:
   - "building-materials" (bricks, cement, sand, stone, masonry)
   - "concrete" (ready-mix, rebar, mesh, formwork, slabs)
   - "earthworks" (excavation, trenching, backfill, site clearance)
   - "roofing" (trusses, sheeting, IBR, tiles, gutters)
   - "plumbing" (pipes, drainage, sanitaryware, taps, geysers)
   - "electrical" (cables, DB boards, conduits, lighting, sockets)
   - "finishes" (paint, tiles, ceilings, plaster, doors, windows)
   - "ppe" (safety gear, boots, vests, overalls, helmets)
   - "plant-hire" (tippers, excavators, TLB, scaffolding, generators)
   - "general-building" (miscellaneous bill items)
7. parsing_confidence: Float from 0.50 to 0.98 indicating how confident you are that this is a genuine priceable item:
   - 0.90 to 0.98: Fully specified line items with complete description, specific dimensions/grades, standard unit, and quantity.
   - 0.70 to 0.85: Legitimate items with partial ambiguity (e.g. provisional sums, missing dimensions, or non-standard units).
   - 0.50 to 0.69: Borderline or composite items that require contractor clarification before pricing.
   DO NOT return a flat or constant confidence score across all items; evaluate each item individually based on specification clarity.

Output valid JSON strictly adhering to the schema.
"""

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "title_hint": {"type": "STRING"},
        "tender_reference_hint": {"type": "STRING"},
        "sections_detected": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
        },
        "line_items": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "source_row_reference": {"type": "STRING"},
                    "section_name": {"type": "STRING"},
                    "description": {"type": "STRING"},
                    "unit": {"type": "STRING"},
                    "quantity": {"type": "NUMBER"},
                    "category": {"type": "STRING"},
                    "parsing_confidence": {"type": "NUMBER"},
                },
                "required": ["description", "unit", "quantity", "category"],
            },
        },
    },
    "required": ["line_items"],
}


class GeminiLLMProvider:
    """Production LLM Provider using Google Gemini API with multimodal PDF support and fallback to StubLLMProvider."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or getattr(settings, "gemini_model", "gemini-2.5-flash")
        self.stub_fallback = StubLLMProvider()

    def _normalize_unit(self, unit_str: str) -> str:
        cleaned = str(unit_str).strip().lower()
        return UNIT_NORMALIZATION.get(cleaned, "no")

    def _parse_candidate_response(
        self,
        candidate_text: str,
        filename: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> ParseResultDTO:
        parsed_json = json.loads(candidate_text)
        raw_items = parsed_json.get("line_items", [])
        sections_detected = parsed_json.get("sections_detected", [])

        line_items: List[ParsedLineItemDTO] = []
        excluded_candidates: List[ParsedLineItemDTO] = []

        for idx, item in enumerate(raw_items, 1):
            desc = item.get("description", "").strip()
            if not desc or len(desc) < 3:
                continue

            unit = self._normalize_unit(item.get("unit", "no"))
            try:
                qty = float(item.get("quantity", 1.0))
            except (ValueError, TypeError):
                qty = 1.0

            cat = item.get("category", "general-building").strip().lower()
            ref = item.get("source_row_reference") or f"Item-{idx}"
            sec = item.get("section_name") or "General Scope"
            if sec and sec not in sections_detected:
                sections_detected.append(sec)

            # Safety validation: Pass through deterministic candidate classifier
            is_valid, det_conf, review_status, exclusion_reason = classify_candidate_line_item(
                description=desc,
                unit=unit,
                quantity=qty,
                raw_reference=ref,
                section_name=sec,
            )

            # Combine model confidence with deterministic confidence
            raw_model_conf = float(item.get("parsing_confidence", 0.85))
            combined_conf = round((raw_model_conf * 0.45) + (det_conf * 0.55), 2)

            high_thresh = getattr(settings, "parser_high_confidence_threshold", 0.80)
            low_thresh = getattr(settings, "parser_low_confidence_threshold", 0.50)

            if not is_valid or combined_conf < low_thresh:
                review_status = "excluded"
                exclusion_reason = exclusion_reason or "Low confidence non-priceable candidate"
            elif combined_conf >= high_thresh and review_status != "needs_review":
                review_status = "accepted"
                exclusion_reason = None
            else:
                review_status = "needs_review"
                exclusion_reason = exclusion_reason or "Ambiguous candidate — verify in review"

            item_dto = ParsedLineItemDTO(
                source_row_reference=ref,
                section_name=sec,
                description=desc,
                unit=unit,
                quantity=qty,
                category=cat,
                benchmark_min_minor=None,  # No fabricated benchmark pricing!
                benchmark_max_minor=None,
                benchmark_source=None,
                parsing_confidence=combined_conf,
                review_status=review_status,
                exclusion_reason=exclusion_reason,
            )

            if is_valid and review_status != "excluded":
                line_items.append(item_dto)
            else:
                excluded_candidates.append(item_dto)

        title_hint = parsed_json.get("title_hint") or filename or "Tender BoQ Scope"
        ref_hint = parsed_json.get("tender_reference_hint") or "TND-2026-AI"

        return ParseResultDTO(
            title_hint=title_hint,
            tender_reference_hint=ref_hint,
            sections_detected=sections_detected,
            line_items=line_items,
            excluded_candidates=excluded_candidates,
            metadata={
                "parser_method": f"GeminiLLMProvider ({self.model})",
                "candidates_total": len(line_items) + len(excluded_candidates),
                "candidates_classified_valid": len(line_items),
                "candidates_excluded": len(excluded_candidates),
                "high_confidence_count": sum(1 for i in line_items if i.review_status == "accepted"),
                "needs_review_count": sum(1 for i in line_items if i.review_status == "needs_review"),
                "duration_ms": duration_ms,
            },
        )

    async def parse_boq_document(
        self,
        extracted_text: str,
        filename: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> ParseResultDTO:
        if not self.api_key:
            logger.info("No GEMINI_API_KEY configured; falling back to StubLLMProvider.")
            return await self.stub_fallback.parse_boq_document(extracted_text, filename, context)

        # Pre-extraction sanity check for garbled or corrupted text
        from app.domains.parsing.segmentation import is_text_corrupted
        is_corrupted, ratio, corrupt_reason = is_text_corrupted(extracted_text, is_line_item=False)
        if is_corrupted:
            raise ValueError(f"GARBLED_DOCUMENT_TEXT: {corrupt_reason}")

        # Preprocessing segmentation: filter obvious narrative blocks before LLM
        candidate_lines, raw_excluded = segment_document_text(extracted_text)
        filtered_text = "\n".join(candidate_lines)

        url = GEMINI_API_URL.format(model=self.model) + f"?key={self.api_key}"
        prompt_payload = {
            "contents": [
                {
                    "parts": [
                        {"text": SYSTEM_PROMPT},
                        {
                            "text": (
                                f"Document Filename: {filename or 'Unknown'}\n\n"
                                f"Document Content:\n{filtered_text}\n\n"
                                "Please extract all BoQ line items in JSON format, strictly omitting clauses, narrative, and headings."
                            )
                        },
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
                "responseSchema": RESPONSE_SCHEMA,
            },
        }

        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(url, json=prompt_payload)
                duration_ms = int((time.time() - start_time) * 1000)

                if response.status_code != 200:
                    logger.warning("Gemini API returned %s: %s. Falling back to stub.", response.status_code, response.text)
                    return await self.stub_fallback.parse_boq_document(extracted_text, filename, context)

                data = response.json()
                candidate_text = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                )

                if not candidate_text:
                    return await self.stub_fallback.parse_boq_document(extracted_text, filename, context)

                return self._parse_candidate_response(candidate_text, filename, duration_ms)

        except Exception as e:
            logger.error("Error during Gemini text parsing: %s. Falling back to stub.", e)
            return await self.stub_fallback.parse_boq_document(extracted_text, filename, context)

    async def parse_boq_document_bytes(
        self,
        document_bytes: bytes,
        mime_type: str,
        filename: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> ParseResultDTO:
        mime = (mime_type or "").lower()
        fname = (filename or "").lower()

        # Deterministic Excel/CSV parsing first
        if "excel" in mime or "sheet" in mime or fname.endswith(".xlsx") or fname.endswith(".xls"):
            from app.domains.parsing.spreadsheet import parse_structured_spreadsheet, extract_text_from_spreadsheet
            det_res = parse_structured_spreadsheet(document_bytes, filename=filename)
            if det_res:
                return det_res
            sheet_text = extract_text_from_spreadsheet(document_bytes)
            if not sheet_text or not sheet_text.strip():
                raise ValueError("EMPTY_OR_UNREADABLE_EXCEL: We could not extract any readable rows from this Excel document. Please ensure it is a valid, uncorrupted Excel (.xlsx) file.")
            return await self.parse_boq_document(sheet_text, filename=filename, context=context)

        # If it's a PDF and we have an API key, use direct multimodal PDF input
        if self.api_key and ("pdf" in mime or fname.endswith(".pdf")):
            if not document_bytes.startswith(b"%PDF"):
                raise ValueError("INVALID_PDF_HEADER: The uploaded file does not have a valid PDF header.")
            url = GEMINI_API_URL.format(model=self.model) + f"?key={self.api_key}"
            pdf_b64 = base64.b64encode(document_bytes).decode("utf-8")

            prompt_payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": SYSTEM_PROMPT},
                            {
                                "inlineData": {
                                    "mimeType": "application/pdf",
                                    "data": pdf_b64,
                                }
                            },
                            {
                                "text": f"Filename: {filename or 'Tender_BoQ.pdf'}. Parse all Bills and Schedule of Quantities table rows into JSON. Filter out clauses, legal text, and collection summaries."
                            },
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.1,
                    "responseMimeType": "application/json",
                    "responseSchema": RESPONSE_SCHEMA,
                },
            }

            start_time = time.time()
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(url, json=prompt_payload)
                    duration_ms = int((time.time() - start_time) * 1000)

                    if response.status_code == 200:
                        data = response.json()
                        candidate_text = (
                            data.get("candidates", [{}])[0]
                            .get("content", {})
                            .get("parts", [{}])[0]
                            .get("text", "")
                        )
                        if candidate_text:
                            return self._parse_candidate_response(candidate_text, filename, duration_ms)
                    else:
                        logger.warning("Gemini multimodal PDF returned %s: %s. Falling back.", response.status_code, response.text)
            except Exception as e:
                logger.error("Error during Gemini multimodal PDF parsing: %s. Falling back.", e)

        # Fallback to stub / text extraction pipeline
        return await self.stub_fallback.parse_boq_document_bytes(
            document_bytes=document_bytes,
            mime_type=mime_type,
            filename=filename,
            context=context,
        )
