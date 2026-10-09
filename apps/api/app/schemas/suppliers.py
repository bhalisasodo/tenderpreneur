from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

SupplierProfileStatus = Literal["pending", "approved", "rejected", "suspended"]


class SupplierProfileBase(BaseModel):
    categories: List[str] = Field(default_factory=list)
    service_regions: List[str] = Field(default_factory=list)
    compliance_flags: Dict[str, Any] = Field(default_factory=dict)
    preferred_contact_method: str = Field(default="whatsapp")
    status: SupplierProfileStatus = Field(default="pending")
    active: bool = False


class SupplierProfileCreate(SupplierProfileBase):
    pass


class SupplierProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    categories: Optional[List[str]] = None
    service_regions: Optional[List[str]] = None
    compliance_flags: Optional[Dict[str, Any]] = None
    preferred_contact_method: Optional[str] = None
    active: Optional[bool] = None


class SupplierProfileResponse(SupplierProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organisation_id: str
    created_at: datetime
    updated_at: datetime


class SupplierMatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organisation_id: str
    legal_name: str
    trading_name: Optional[str] = None
    email: str
    phone: Optional[str] = None
    categories: List[str]
    service_regions: List[str]
    preferred_contact_method: str
    match_reasons: List[str]


class SupplierApprovalResponse(SupplierProfileResponse):
    pass


class SupplierReviewResponse(BaseModel):
    id: str
    organisation_id: str
    legal_name: str
    trading_name: Optional[str] = None
    email: str
    phone: Optional[str] = None
    region: str
    categories: List[str]
    service_regions: List[str]
    approval_status: str
    status: str
    active: bool


class SupplierApprovalRequest(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=500)
