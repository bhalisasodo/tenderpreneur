import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.models import User

security_scheme = HTTPBearer(auto_error=False)


class AuthContext(BaseModel):
    user_id: str
    organisation_id: str
    organisation_type: str  # "contractor" or "supplier"
    role: str
    email: str
    rfq_id: Optional[str] = None
    is_rfq_direct: bool = False


def hash_password(password: str) -> str:
    """Securely hash a password using scrypt with a unique cryptographic salt."""
    salt = secrets.token_hex(16)
    key = hashlib.scrypt(password.encode("utf-8"), salt=salt.encode("utf-8"), n=16384, r=8, p=1)
    return f"{salt}:{key.hex()}"


def verify_password(plain_password: str, hashed_password: Optional[str]) -> bool:
    if not hashed_password:
        return False

    try:
        if hashed_password.startswith("pbkdf2_sha256$"):
            algorithm, iterations, encoded_salt, encoded_digest = hashed_password.split("$", 3)
            if algorithm != "pbkdf2_sha256":
                return False
            salt = base64.urlsafe_b64decode(encoded_salt.encode("ascii"))
            expected_digest = base64.urlsafe_b64decode(encoded_digest.encode("ascii"))
            actual_digest = hashlib.pbkdf2_hmac(
                "sha256", plain_password.encode("utf-8"), salt, int(iterations)
            )
            return hmac.compare_digest(actual_digest, expected_digest)

        if ":" not in hashed_password:
            return False
        salt, original_hex = hashed_password.split(":", 1)
        key = hashlib.scrypt(
            plain_password.encode("utf-8"),
            salt=salt.encode("utf-8"),
            n=16384,
            r=8,
            p=1,
        )
        return hmac.compare_digest(key.hex(), original_hex)
    except (TypeError, ValueError, UnicodeDecodeError):
        return False


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


def create_rfq_access_token(
    quote_request_id: str,
    supplier_org_id: str,
    expires_in_hours: int = 72,
) -> str:
    """Generates a cryptographically signed direct quoting token for a supplier and specific RFQ."""
    expire = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
    to_encode = {
        "sub": f"rfq_{supplier_org_id}",
        "org_id": supplier_org_id,
        "org_type": "supplier",
        "rfq_id": quote_request_id,
        "role": "sales",
        "token_type": "rfq_direct",
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
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    # 1. Try Authorization header
    token = credentials.credentials if (credentials and credentials.credentials) else None

    # 2. Fallback to query parameter (e.g. ?access_token=... for mobile RFQ links)
    if not token:
        token = request.query_params.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Missing or invalid authorization token."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Token is invalid or expired."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    is_rfq_direct = payload.get("token_type") == "rfq_direct"
    user_id = payload.get("sub")
    organisation_id = payload.get("org_id")
    organisation_type = payload.get("org_type")
    user = None
    if not is_rfq_direct:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if (
            not user
            or not user.is_active
            or user.organisation_id != organisation_id
            or not user.organisation
            or user.organisation.type != organisation_type
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_TOKEN", "message": "This account is no longer active."},
                headers={"WWW-Authenticate": "Bearer"},
            )

    return AuthContext(
        user_id=user_id,
        organisation_id=organisation_id,
        organisation_type=organisation_type,
        role=user.role if user else payload.get("role", "sales"),
        email=user.email if user else payload.get("email", ""),
        rfq_id=payload.get("rfq_id"),
        is_rfq_direct=is_rfq_direct,
    )


def require_contractor(auth: AuthContext = Depends(get_current_auth)) -> AuthContext:
    if auth.organisation_type != "contractor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Action requires contractor organisation permissions."},
        )
    return auth


def require_supplier(auth: AuthContext = Depends(get_current_auth)) -> AuthContext:
    if auth.organisation_type != "supplier" or auth.is_rfq_direct:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Action requires supplier organisation permissions."},
        )
    return auth


def require_quote_supplier(auth: AuthContext = Depends(get_current_auth)) -> AuthContext:
    if auth.organisation_type != "supplier":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Action requires supplier organisation permissions."},
        )
    return auth


def require_platform_admin(auth: AuthContext = Depends(get_current_auth)) -> AuthContext:
    if auth.role != "platform_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Action requires platform administrator permissions."},
        )
    return auth


def require_operator(auth: AuthContext = Depends(get_current_auth)) -> AuthContext:
    if auth.role not in {"platform_admin", "platform_operator"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "OPERATOR_REQUIRED", "message": "Action requires platform operator permissions."},
        )
    return auth
