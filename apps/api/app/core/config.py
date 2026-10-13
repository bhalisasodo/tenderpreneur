import os
from typing import Any, List, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, model_validator
from urllib.parse import urlparse


class Settings(BaseSettings):
    app_name: str = "BoQPro API"
    app_version: str = "0.1.0"
    environment: str = "development"  # "development", "staging", "production"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: str = "sqlite+aiosqlite:///./boqpro.db"

    # Security / Auth
    jwt_secret: str = "boqpro-insecure-dev-secret-key-replace-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days
    rate_limit_auth_per_minute: int = 20
    password_salt: str = "boqpro-default-salt-change-in-production"
    app_base_url: str = "http://localhost:3000"

    # File Storage & Ingestion Limits
    storage_type: str = "local"  # "local" or "s3"
    local_storage_path: str = "./storage"
    object_storage_endpoint: str = "http://localhost:9000"
    object_storage_bucket: str = "boqpro"
    object_storage_access_key: str = "boqpro"
    object_storage_secret_key: str = "change-me-local-only"
    max_upload_size_bytes: int = 15 * 1024 * 1024  # 15 MB

    # External Provider Integrations
    llm_provider: str = "stub"  # "stub" or "gemini"
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.5-flash"
    notification_provider: str = "console"  # "console", "email", "smtp", "webhook"
    notification_webhook_url: Optional[str] = None
    notification_webhook_token: Optional[str] = None

    # Outbound Email (SMTP)
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True
    smtp_from_email: str = "noreply@boqpro.co.za"
    public_app_url: str = "http://localhost:3000"

    # BoQ Parser Configuration
    parser_high_confidence_threshold: float = 0.80
    parser_low_confidence_threshold: float = 0.50

    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"]
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @model_validator(mode="before")
    @classmethod
    def fallback_legacy_env_vars(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        # Support fallback from legacy TENDERPRENEUR_* env vars if BOQPRO_* was not provided
        field_keys = [
            "environment", "debug", "database_url", "jwt_secret", "jwt_algorithm",
            "jwt_expire_minutes", "rate_limit_auth_per_minute",
            "password_salt", "app_base_url",
            "storage_type",
            "local_storage_path", "object_storage_endpoint", "object_storage_bucket",
            "object_storage_access_key", "object_storage_secret_key", "max_upload_size_bytes",
            "llm_provider", "openai_api_key", "gemini_api_key", "gemini_model",
            "notification_provider", "smtp_host", "smtp_port", "smtp_username",
            "smtp_password", "smtp_use_tls", "smtp_from_email",
            "notification_webhook_url", "notification_webhook_token",
            "public_app_url",
            "parser_high_confidence_threshold", "parser_low_confidence_threshold",
            "cors_origins",
        ]
        for key in field_keys:
            if key not in data or data[key] is None:
                boqpro_val = os.environ.get(f"BOQPRO_{key.upper()}")
                tp_val = os.environ.get(f"TENDERPRENEUR_{key.upper()}")
                if boqpro_val is not None:
                    data[key] = boqpro_val
                elif tp_val is not None:
                    data[key] = tp_val
        return data

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, origins: List[str]) -> List[str]:
        normalized = []
        for origin in origins:
            value = origin.strip()
            parsed = urlparse(value)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.path not in {"", "/"}
                or parsed.params
                or parsed.query
                or parsed.fragment
                or "*" in parsed.netloc
            ):
                raise ValueError(f"Invalid CORS origin: {origin!r}")
            normalized.append(f"{parsed.scheme}://{parsed.netloc}".rstrip("/"))
        return normalized

    @field_validator("notification_provider")
    @classmethod
    def validate_notification_provider(cls, provider: str) -> str:
        normalized = provider.strip().lower()
        if normalized not in {"console", "email", "smtp", "webhook"}:
            raise ValueError("BOQPRO_NOTIFICATION_PROVIDER must be console, email, smtp, or webhook.")
        return normalized

    @field_validator("llm_provider")
    @classmethod
    def validate_llm_provider(cls, provider: str) -> str:
        normalized = provider.strip().lower()
        if normalized not in {"stub", "gemini"}:
            raise ValueError("BOQPRO_LLM_PROVIDER must be stub or gemini.")
        return normalized

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.environment.lower() in ("production", "prod"):
            if (
                not self.jwt_secret
                or "insecure" in self.jwt_secret
                or "replace-in-production" in self.jwt_secret
                or len(self.jwt_secret) < 32
            ):
                raise ValueError(
                    "Production security violation: BOQPRO_JWT_SECRET must be set to a cryptographically secure key of at least 32 characters in production."
                )
            if (
                not self.password_salt
                or "insecure" in self.password_salt
                or "replace-in-production" in self.password_salt
                or "default-salt" in self.password_salt
                or len(self.password_salt) < 32
            ):
                raise ValueError(
                    "Production security violation: BOQPRO_PASSWORD_SALT must be set to a cryptographically secure value of at least 32 characters in production."
                )
            if self.debug:
                raise ValueError(
                    "Production security violation: BOQPRO_DEBUG must be False in production."
                )
            if self.database_url.startswith("sqlite"):
                raise ValueError(
                    "Production security violation: BOQPRO_DATABASE_URL must use PostgreSQL in production."
                )
            if not self.cors_origins or any(
                urlparse(origin).scheme != "https" for origin in self.cors_origins
            ):
                raise ValueError(
                    "Production security violation: CORS origins must be configured with HTTPS endpoints only."
                )
            for setting_name, value in (
                ("BOQPRO_APP_BASE_URL", self.app_base_url),
                ("BOQPRO_PUBLIC_APP_URL", self.public_app_url),
            ):
                parsed_url = urlparse(value)
                if (
                    parsed_url.scheme != "https"
                    or not parsed_url.netloc
                    or parsed_url.username
                    or parsed_url.password
                    or parsed_url.query
                    or parsed_url.fragment
                ):
                    raise ValueError(
                        f"Production security violation: {setting_name} must be an HTTPS base URL without credentials, query parameters, or fragments."
                    )

            notification_provider = self.notification_provider.lower()
            if notification_provider in {"email", "smtp"}:
                if not self.smtp_host:
                    raise ValueError(
                        "Production security violation: BOQPRO_SMTP_HOST is required when email notifications are enabled."
                    )
                if not self.smtp_use_tls:
                    raise ValueError(
                        "Production security violation: BOQPRO_SMTP_USE_TLS must be enabled for email notifications."
                    )
            elif notification_provider == "webhook":
                webhook_url = urlparse(self.notification_webhook_url or "")
                if (
                    webhook_url.scheme != "https"
                    or not webhook_url.netloc
                    or webhook_url.username
                    or webhook_url.password
                    or webhook_url.fragment
                ):
                    raise ValueError(
                        "Production security violation: BOQPRO_NOTIFICATION_WEBHOOK_URL must be an HTTPS URL without embedded credentials or fragments."
                    )
                if not self.notification_webhook_token:
                    raise ValueError(
                        "Production security violation: BOQPRO_NOTIFICATION_WEBHOOK_TOKEN is required when webhook notifications are enabled."
                    )
            else:
                raise ValueError(
                    "Production security violation: BOQPRO_NOTIFICATION_PROVIDER must be email, smtp, or webhook."
                )
            if self.llm_provider == "gemini" and not self.gemini_api_key:
                raise ValueError(
                    "Production security violation: BOQPRO_GEMINI_API_KEY is required when Gemini parsing is enabled."
                )
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="BOQPRO_",
        extra="ignore",
    )


settings = Settings()
