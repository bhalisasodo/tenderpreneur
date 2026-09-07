import io
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.config import Settings
from app.core.rate_limit import InMemoryRateLimiter, reset_auth_rate_limiter
from app.integrations.notifications.email import EmailNotificationProvider


def test_production_jwt_secret_enforcement():
    """Verify system strictly refuses to boot in production with default insecure secret."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            environment="production",
            debug=False,
            jwt_secret="tenderpreneur-insecure-dev-secret-key-replace-in-production",
        )
    assert "Production security violation" in str(exc_info.value)
    assert "TENDERPRENEUR_JWT_SECRET" in str(exc_info.value)


def test_production_debug_mode_disabled():
    """Verify system strictly refuses to boot in production if debug mode is True."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            environment="production",
            debug=True,
            jwt_secret="a_super_strong_cryptographic_secret_key_of_length_greater_than_32",
        )
    assert "Production security violation" in str(exc_info.value)
    assert "TENDERPRENEUR_DEBUG" in str(exc_info.value)


def test_production_valid_configuration_passes():
    """Verify system boots cleanly in production when compliant secrets and settings are provided."""
    valid_settings = Settings(
        environment="production",
        debug=False,
        jwt_secret="a_super_strong_cryptographic_secret_key_of_length_greater_than_32",
    )
    assert valid_settings.environment == "production"
    assert valid_settings.debug is False


def test_cors_origins_parsing_from_string():
    """Verify CORS origins string is automatically parsed into a list."""
    s = Settings(
        cors_origins="https://app.tenderpreneur.co.za, https://supplier.tenderpreneur.co.za"
    )
    assert "https://app.tenderpreneur.co.za" in s.cors_origins
    assert "https://supplier.tenderpreneur.co.za" in s.cors_origins


def test_auth_rate_limiter_exceeded():
    """Verify rate limiter blocks bursts and returns 429 with Retry-After header."""
    limiter = InMemoryRateLimiter(requests_per_minute=3)
    client_ip = "192.168.1.100"

    # 3 allowed requests
    limiter.check(client_ip)
    limiter.check(client_ip)
    limiter.check(client_ip)

    # 4th request must be blocked
    with pytest.raises(HTTPException) as exc_info:
        limiter.check(client_ip)

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail["code"] == "RATE_LIMIT_EXCEEDED"
    assert "Retry-After" in exc_info.value.headers


@pytest.mark.asyncio
async def test_email_notification_provider_dry_run():
    """Verify EmailNotificationProvider runs safely when no SMTP host is configured."""
    provider = EmailNotificationProvider(host=None)
    success = await provider.send_quote_request_notification(
        supplier_id="sup-1",
        supplier_name="KZN Bulk Aggregates",
        supplier_contact="sales@kznaggregates.co.za",
        channel="email",
        boq_title="Mogale City Bulk Pipeline",
        line_item_description="19mm concrete stone",
        quantity=50.0,
        unit="m3",
        response_deadline_iso="2026-09-10T12:00:00Z",
        submission_link="https://app.tenderpreneur.co.za/quotes/submit?token=abc",
    )
    assert success is True


@pytest.mark.asyncio
async def test_file_upload_size_and_type_validation(client, seeded_entities):
    """Verify file upload endpoint rejects files exceeding 15MB or with illegal extensions."""
    headers = {"Authorization": f"Bearer {seeded_entities['contractor_token']}"}

    # 1. Create a BoQ
    create_res = await client.post(
        "/api/v1/boqs",
        headers=headers,
        json={"title": "Size Test BoQ", "region": "Gauteng"},
    )
    assert create_res.status_code == 201
    boq_id = create_res.json()["id"]

    # 2. Test illegal file extension (.exe) -> 415
    bad_ext_res = await client.post(
        f"/api/v1/boqs/{boq_id}/documents",
        headers=headers,
        files={"file": ("malicious_file.exe", b"binary content", "application/x-msdownload")},
    )
    assert bad_ext_res.status_code == 415
    assert bad_ext_res.json()["detail"]["code"] == "UNSUPPORTED_MEDIA_TYPE"

    # 3. Test file exceeding 15MB limit -> 413
    oversized_bytes = b"0" * (16 * 1024 * 1024)  # 16 MB
    oversized_res = await client.post(
        f"/api/v1/boqs/{boq_id}/documents",
        headers=headers,
        files={"file": ("huge_schedule.xlsx", oversized_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert oversized_res.status_code == 413
    assert oversized_res.json()["detail"]["code"] == "FILE_TOO_LARGE"

