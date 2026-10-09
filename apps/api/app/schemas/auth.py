from datetime import datetime
from typing import Optional
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


class SupplierRegistrationRequest(BaseModel):
    legal_name: str = Field(min_length=2, max_length=255)
    trading_name: Optional[str] = Field(default=None, max_length=255)
    contact_name: str = Field(min_length=2, max_length=255)
    email: str
    phone: str = Field(min_length=7, max_length=50)
    password: str = Field(min_length=12, max_length=128)
    categories: list[str] = Field(min_length=1)
    service_regions: list[str] = Field(default_factory=lambda: ["Durban", "KwaZulu-Natal"])
    preferred_contact_method: str = Field(default="email")

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("A valid email address is required.")
        return normalized


class SupplierRegistrationResponse(BaseModel):
    organisation_id: str
    user_id: str
    status: str
    message: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    organisation: OrganisationResponse
