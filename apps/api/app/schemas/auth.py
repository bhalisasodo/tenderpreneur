from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.suppliers import SupplierProfileResponse


class OrganisationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str
    legal_name: str
    trading_name: Optional[str] = None
    email: str
    phone: Optional[str] = None
    region: str
    created_at: datetime


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organisation_id: str
    email: str
    name: str
    role: str
    created_at: datetime
    organisation: Optional[OrganisationResponse] = None


class LoginRequest(BaseModel):
    email: str
    password: Optional[str] = "password"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    organisation: OrganisationResponse


class SupplierRegisterRequest(BaseModel):
    legal_name: str = Field(..., min_length=2, max_length=255)
    trading_name: Optional[str] = Field(None, max_length=255)
    email: str = Field(..., min_length=5, max_length=255)
    phone: str = Field(..., min_length=7, max_length=50)
    region: str = Field(default="KwaZulu-Natal", max_length=100)
    contact_name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    categories: List[str] = Field(default_factory=lambda: ["building-materials"])
    service_regions: List[str] = Field(default_factory=lambda: ["KwaZulu-Natal"])
    preferred_contact_method: str = Field(default="whatsapp")
    compliance_flags: Optional[Dict[str, Any]] = Field(default_factory=dict)


class SupplierRegisterResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    organisation: OrganisationResponse
    profile: Optional[SupplierProfileResponse] = None
