from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


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
