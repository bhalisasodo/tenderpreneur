from typing import List, Optional, Protocol
from pydantic import BaseModel, Field


class ParsedLineItemDTO(BaseModel):
    source_row_reference: Optional[str] = Field(None, description="Row or item identifier from source, e.g. 'A.1', '1.02'")
    section_name: Optional[str] = Field(None, description="Section or Bill name, e.g. 'Bill No. 2 - Earthworks'")
    description: str = Field(..., description="Detailed description of materials or work")
    unit: str = Field(default="no", description="Unit of measurement, e.g. 'm2', 'm3', 'kg', 'no', 'sum', 'm', 'item'")
    quantity: float = Field(default=1.0, description="Quantity")
    category: str = Field(default="general-building", description="Standard material or trade category")
    benchmark_min_minor: Optional[int] = Field(None, description="Estimated lower benchmark in minor cents")
    benchmark_max_minor: Optional[int] = Field(None, description="Estimated upper benchmark in minor cents")
    benchmark_source: Optional[str] = Field(None, description="Benchmark reference label")
    parsing_confidence: float = Field(default=0.90, ge=0.0, le=1.0, description="Confidence score")
    review_status: str = Field(default="accepted", description="Review status: 'accepted', 'needs_review', 'excluded'")
    exclusion_reason: Optional[str] = Field(None, description="Reason if excluded or flagged for review")


class ParseResultDTO(BaseModel):
    title_hint: Optional[str] = None
    tender_reference_hint: Optional[str] = None
    sections_detected: List[str] = []
    line_items: List[ParsedLineItemDTO] = []
    excluded_candidates: List[ParsedLineItemDTO] = []
    metadata: dict = {}


class LLMProvider(Protocol):
    async def parse_boq_document(
        self,
        extracted_text: str,
        filename: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> ParseResultDTO:
        """Parses extracted document text into structured line items with strict validation."""
        ...

    async def parse_boq_document_bytes(
        self,
        document_bytes: bytes,
        mime_type: str,
        filename: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> ParseResultDTO:
        """Parses raw document bytes (PDF, Excel) directly into structured line items."""
        ...

