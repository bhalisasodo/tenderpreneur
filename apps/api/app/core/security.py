from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

security_scheme = HTTPBearer(auto_error=False)


class AuthContext(BaseModel):
    user_id: str
    organisation_id: str
    organisation_type: str  # "contractor" or "supplier"
    role: str
    email: str


def create_access_token(
    user_id: str,
    organisation_id: str,
    organisation_type: str,
    email: str,
    role: str = "admin",
    expires_delta: Optional[timedelta] = None,
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)

    to_encode = {
        "sub": user_id,
        "org_id": organisation_id,
        "org_type": organisation_type,
        "email": email,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except jwt.PyJWTError:
        return None


async def get_current_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    if not credentials or not credentials.credentials:
        # If in dev mode, provide fallback for default contractor if needed or raise 401
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Missing or invalid authorization token."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Token is invalid or expired."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthContext(
        user_id=payload["sub"],
        organisation_id=payload["org_id"],
        organisation_type=payload["org_type"],
        role=payload.get("role", "admin"),
        email=payload.get("email", ""),
    )


def require_contractor(auth: AuthContext = Depends(get_current_auth)) -> AuthContext:
    if auth.organisation_type != "contractor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Action requires contractor organisation permissions."},
        )
    return auth


def require_supplier(auth: AuthContext = Depends(get_current_auth)) -> AuthContext:
    if auth.organisation_type != "supplier":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Action requires supplier organisation permissions."},
        )
    return auth
