import os
from typing import Any, List, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, model_validator


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

    # File Storage & Ingestion Limits
    storage_type: str = "local"  # "local" or "s3"
    local_storage_path: str = "./storage"
    object_storage_endpoint: str = "http://localhost:9000"
    object_storage_bucket: str = "boqpro"
    object_storage_access_key: str = "boqpro"
    object_storage_secret_key: str = "change-me-local-only"
    max_upload_size_bytes: int = 15 * 1024 * 1024  # 15 MB

    # External Provider Integrations
    llm_provider: str = "stub"  # "stub", "openai", "gemini"
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.5-flash"
    notification_provider: str = "console"  # "console", "email", "memory", "webhook"

    # Outbound Email (SMTP)
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True
    smtp_from_email: str = "noreply@boqpro.co.za"

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
            "jwt_expire_minutes", "rate_limit_auth_per_minute", "storage_type",
            "local_storage_path", "object_storage_endpoint", "object_storage_bucket",
            "object_storage_access_key", "object_storage_secret_key", "max_upload_size_bytes",
            "llm_provider", "openai_api_key", "gemini_api_key", "gemini_model",
            "notification_provider", "smtp_host", "smtp_port", "smtp_username",
            "smtp_password", "smtp_use_tls", "smtp_from_email",
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
            if self.debug:
                raise ValueError(
                    "Production security violation: BOQPRO_DEBUG must be False in production."
                )
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="BOQPRO_",
        extra="ignore",
    )


settings = Settings()
