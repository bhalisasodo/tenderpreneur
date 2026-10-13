import asyncio
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.config import Settings
from app.core.rate_limit import InMemoryRateLimiter
from app.integrations.notifications.email import EmailNotificationProvider


def test_production_jwt_secret_enforcement():
    """Verify system strictly refuses to boot in production with default insecure secret."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            environment="production",
            debug=False,
            jwt_secret="boqpro-insecure-dev-secret-key-replace-in-production",
        )
    assert "Production security violation" in str(exc_info.value)
    assert "BOQPRO_JWT_SECRET" in str(exc_info.value)


def test_production_debug_mode_disabled():
    """Verify system strictly refuses to boot in production if debug mode is True."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            environment="production",
            debug=True,
            jwt_secret="a_super_strong_cryptographic_secret_key_of_length_greater_than_32",
            password_salt="a_super_strong_cryptographic_salt_key_of_length_greater_than_32",
            database_url="postgresql+psycopg://boqpro:secret@postgres:5432/boqpro",
            cors_origins=["https://app.boqpro.co.za"],
            app_base_url="https://app.boqpro.co.za",
            public_app_url="https://app.boqpro.co.za",
            notification_provider="email",
            smtp_host="smtp.example.co.za",
        )
    assert "Production security violation" in str(exc_info.value)
    assert "BOQPRO_DEBUG" in str(exc_info.value)


def test_production_valid_configuration_passes():
    """Verify system boots cleanly in production when compliant secrets and settings are provided."""
    valid_settings = Settings(
        app_base_url="https://app.boqpro.co.za",
        public_app_url="https://app.boqpro.co.za",
        notification_provider="email",
        smtp_host="smtp.example.co.za",
        environment="production",
        debug=False,
        jwt_secret="a_super_strong_cryptographic_secret_key_of_length_greater_than_32",
        password_salt="a_super_strong_cryptographic_salt_key_of_length_greater_than_32",
        database_url="postgresql+psycopg://boqpro:secret@postgres:5432/boqpro",
        cors_origins=["https://app.boqpro.co.za"],
    )
    assert valid_settings.environment == "production"
    assert valid_settings.debug is False
    assert valid_settings.database_url.startswith("postgresql")


def test_production_password_salt_enforcement():
    """Verify production rejects placeholder or short password salts."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            environment="production",
            debug=False,
            jwt_secret="a_super_strong_cryptographic_secret_key_of_length_greater_than_32",
            password_salt="boqpro-default-salt-change-in-production",
            database_url="postgresql+psycopg://boqpro:secret@postgres:5432/boqpro",
            cors_origins=["https://app.boqpro.co.za"],
        )
    assert "BOQPRO_PASSWORD_SALT" in str(exc_info.value)


def test_production_requires_https_cors_origins():
    """Verify production rejects unsafe or private CORS origins."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            environment="production",
            debug=False,
            jwt_secret="a_super_strong_cryptographic_secret_key_of_length_greater_than_32",
            password_salt="a_super_strong_cryptographic_salt_key_of_length_greater_than_32",
            database_url="postgresql+psycopg://boqpro:secret@postgres:5432/boqpro",
            cors_origins=["http://localhost:3000"],
        )
    assert "CORS origins" in str(exc_info.value)


def test_production_rejects_cors_origins_with_paths():
    with pytest.raises(ValidationError, match="Invalid CORS origin"):
        Settings(
            environment="production",
            debug=False,
            jwt_secret="a_super_strong_cryptographic_secret_key_of_length_greater_than_32",
            password_salt="a_super_strong_cryptographic_salt_key_of_length_greater_than_32",
            database_url="postgresql+psycopg://user:password@localhost:5432/boqpro",
            cors_origins=["https://app.boqpro.co.za/untrusted-path"],
        )


def test_cors_origins_parsing_from_string():
    """Verify CORS origins string is automatically parsed into a list."""
    s = Settings(
        cors_origins="https://app.boqpro.co.za, https://supplier.boqpro.co.za"
    )
    assert "https://app.boqpro.co.za" in s.cors_origins
    assert "https://supplier.boqpro.co.za" in s.cors_origins


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
    """An unconfigured email provider must report failure, not simulated delivery."""
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
        submission_link="https://app.boqpro.co.za/quotes/submit?token=abc",
    )
    assert success is False


@pytest.mark.asyncio
async def test_email_notification_escapes_user_supplied_html(monkeypatch: pytest.MonkeyPatch):
    sent_messages = []

    async def capture_message(function, message):
        sent_messages.append(message)
        return True

    monkeypatch.setattr(asyncio, "to_thread", capture_message)
    provider = EmailNotificationProvider(host="smtp.example.co.za")
    await provider.send_quote_request_notification(
        supplier_id="supplier-id",
        supplier_name="<img src=x onerror=alert(1)>",
        supplier_contact="supplier@example.co.za",
        channel="email",
        boq_title="<script>alert(1)</script>",
        line_item_description="<svg onload=alert(1)>",
        quantity=1,
        unit="item",
        response_deadline_iso="2026-12-31T23:59:59Z",
        submission_link="https://app.example.co.za/rfq#access_token=token",
    )

    html_body = sent_messages[0].get_body(preferencelist=("html",)).get_content()
    assert "&lt;img" in html_body
    assert "&lt;script&gt;" in html_body
    assert "&lt;svg" in html_body
    assert "<script>" not in html_body


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


def test_production_rejects_console_notifications():
    with pytest.raises(ValidationError, match="NOTIFICATION_PROVIDER"):
        Settings(
            environment="production",
            debug=False,
            jwt_secret="a_super_strong_cryptographic_secret_key_of_length_greater_than_32",
            password_salt="a_super_strong_cryptographic_salt_key_of_length_greater_than_32",
            database_url="postgresql+psycopg://boqpro:password@localhost:5432/boqpro",
            cors_origins=["https://app.boqpro.co.za"],
            app_base_url="https://app.boqpro.co.za",
            public_app_url="https://app.boqpro.co.za",
            notification_provider="console",
        )


def test_production_requires_real_smtp_configuration():
    with pytest.raises(ValidationError, match="SMTP_HOST"):
        Settings(
            environment="production",
            debug=False,
            jwt_secret="a_super_strong_cryptographic_secret_key_of_length_greater_than_32",
            password_salt="a_super_strong_cryptographic_salt_key_of_length_greater_than_32",
            database_url="postgresql+psycopg://boqpro:password@localhost:5432/boqpro",
            cors_origins=["https://app.boqpro.co.za"],
            app_base_url="https://app.boqpro.co.za",
            public_app_url="https://app.boqpro.co.za",
            notification_provider="email",
        )


def test_production_webhook_requires_authentication_token():
    with pytest.raises(ValidationError, match="NOTIFICATION_WEBHOOK_TOKEN"):
        Settings(
            environment="production",
            debug=False,
            jwt_secret="a_super_strong_cryptographic_secret_key_of_length_greater_than_32",
            password_salt="a_super_strong_cryptographic_salt_key_of_length_greater_than_32",
            database_url="postgresql+psycopg://user:password@localhost:5432/boqpro",
            cors_origins=["https://app.boqpro.co.za"],
            app_base_url="https://app.boqpro.co.za",
            public_app_url="https://app.boqpro.co.za",
            notification_provider="webhook",
            notification_webhook_url="https://notify.example.co.za/boqpro",
        )
