import re
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    password: str = Field(min_length=1)


class RegistrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organisation_type: Literal["contractor", "supplier"]
    legal_name: str = Field(min_length=2, max_length=255)
    trading_name: Optional[str] = Field(default=None, max_length=255)
    email: str = Field(max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)
    region: str = Field(min_length=2, max_length=100)
    name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=12, max_length=128)
    supplier_categories: List[
        Literal[
            "building-materials",
            "concrete",
            "earthworks",
            "roofing",
            "plumbing",
            "electrical",
            "ppe",
            "finishes",
        ]
    ] = Field(default_factory=list, max_length=20)
    supplier_service_regions: List[str] = Field(default_factory=list, max_length=20)
    preferred_contact_method: Literal["email", "whatsapp", "sms"] = "email"

    @field_validator("email")
    @classmethod
    def normalize_and_validate_email(cls, value: str) -> str:
        email = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ValueError("Enter a valid email address.")
        return email

    @field_validator("legal_name", "trading_name", "phone", "region", "name", mode="before")
    @classmethod
    def strip_optional_whitespace(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value.strip() if isinstance(value, str) else value

    @field_validator("supplier_service_regions")
    @classmethod
    def normalize_service_regions(cls, regions: List[str]) -> List[str]:
        normalized = [region.strip() for region in regions]
        if any(not region or len(region) > 100 for region in normalized):
            raise ValueError("Service regions must be between 1 and 100 characters.")
        return list(dict.fromkeys(normalized))


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    organisation: OrganisationResponse
    supplier_approval_status: Optional[str] = None
