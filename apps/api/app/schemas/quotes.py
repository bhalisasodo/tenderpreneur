from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class QuoteSubmitRequest(BaseModel):
    unit_price_minor: int = Field(..., gt=0, description="Unit price in integer minor cents (e.g. 125000 = R1,250.00)")
    currency: str = Field(default="ZAR")
    lead_time_days: Optional[int] = None
    notes: Optional[str] = None


class QuoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    quote_request_id: str
    supplier_organisation_id: str
    supplier_name: Optional[str] = None
    unit_price_minor: int
    total_price_minor: int
    currency: str
    lead_time_days: Optional[int] = None
    notes: Optional[str] = None
    is_selected: bool
    submitted_at: datetime
    created_at: datetime


class QuoteRequestCreate(BaseModel):
    line_item_id: str
    response_deadline: datetime


class QuoteRequestBroadcastRequest(BaseModel):
    supplier_organisation_ids: Optional[List[str]] = None


class QuoteRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    line_item_id: str
    line_item_description: Optional[str] = None
    line_item_quantity: Optional[float] = None
    line_item_unit: Optional[str] = None
    line_item_category: Optional[str] = None
    boq_id: Optional[str] = None
    boq_title: Optional[str] = None
    boq_region: Optional[str] = None
    requested_by_user_id: Optional[str] = None
    response_deadline: datetime
    status: str
    created_at: datetime
    closed_at: Optional[datetime] = None
    is_expired: bool = False
    quotes: List[QuoteResponse] = []
    supplier_count: int = 0


class LineItemComparisonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    line_item_id: str
    description: str
    unit: str
    quantity: float
    category: str
    benchmark_min_minor: Optional[int] = None
    benchmark_max_minor: Optional[int] = None
    final_price_minor: Optional[int] = None
    pricing_status: str
    quote_request_id: Optional[str] = None
    response_deadline: Optional[datetime] = None
    is_deadline_passed: bool = False
    quotes: List[QuoteResponse] = []
    lowest_quote: Optional[QuoteResponse] = None
    fastest_quote: Optional[QuoteResponse] = None
    selected_quote: Optional[QuoteResponse] = None


class BoQQuoteComparisonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    boq_id: str
    title: str
    region: str
    tender_deadline: Optional[datetime] = None
    line_items: List[LineItemComparisonResponse] = []
    total_estimated_minor: int = 0
    total_priced_minor: int = 0


class QuoteSelectRequest(BaseModel):
    quote_id: str


class PriceOverrideRequest(BaseModel):
    price_minor: int = Field(..., ge=0, description="Override price in minor cents")
    currency: str = Field(default="ZAR")
    reason: str = Field(..., min_length=3)
