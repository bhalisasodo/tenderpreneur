from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_organisation_id: str
    original_filename: str
    mime_type: str
    size_bytes: int
    created_at: datetime


class LineItemBase(BaseModel):
    source_row_reference: Optional[str] = None
    description: str
    unit: str = "no"
    quantity: float = 1.0
    category: str = "general-building"
    benchmark_min_minor: Optional[int] = None
    benchmark_max_minor: Optional[int] = None
    benchmark_source: Optional[str] = None
    benchmark_currency: str = "ZAR"
    review_status: str = "accepted"
    exclusion_reason: Optional[str] = None


class LineItemCreate(LineItemBase):
    pass


class LineItemUpdate(BaseModel):
    description: Optional[str] = None
    unit: Optional[str] = None
    quantity: Optional[float] = None
    category: Optional[str] = None
    benchmark_min_minor: Optional[int] = None
    benchmark_max_minor: Optional[int] = None
    benchmark_source: Optional[str] = None
    final_price_minor: Optional[int] = None
    pricing_status: Optional[str] = None
    review_status: Optional[str] = None
    exclusion_reason: Optional[str] = None


class LineItemResponse(LineItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    boq_id: str
    final_price_minor: Optional[int] = None
    pricing_status: str
    parsing_confidence: Optional[float] = None
    review_status: str = "accepted"
    exclusion_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class BoQCreate(BaseModel):
    title: str = Field(..., json_schema_extra={"example": "School Renovation BoQ"})
    tender_reference: Optional[str] = Field(None, json_schema_extra={"example": "DOE-KZN-2026-088"})
    tender_deadline: Optional[datetime] = None
    region: str = Field(default="KwaZulu-Natal", json_schema_extra={"example": "KwaZulu-Natal"})


class BoQUpdate(BaseModel):
    title: Optional[str] = None
    tender_reference: Optional[str] = None
    tender_deadline: Optional[datetime] = None
    region: Optional[str] = None
    status: Optional[str] = None


class BoQResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    contractor_organisation_id: str
    title: str
    tender_reference: Optional[str] = None
    tender_deadline: Optional[datetime] = None
    region: str
    source_document_id: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    source_document: Optional[DocumentResponse] = None
    line_items: List[LineItemResponse] = []


class BoQSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    contractor_organisation_id: str
    title: str
    tender_reference: Optional[str] = None
    tender_deadline: Optional[datetime] = None
    region: str
    status: str
    line_item_count: int = 0
    total_priced_minor: int = 0
    created_at: datetime
    updated_at: datetime


class ParseRequest(BaseModel):
    pasted_text: Optional[str] = None
