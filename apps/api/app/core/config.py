from typing import List, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, model_validator


class Settings(BaseSettings):
    app_name: str = "Tenderpreneur API"
    app_version: str = "0.1.0"
    environment: str = "development"  # "development", "staging", "production"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: str = "sqlite+aiosqlite:///./tenderpreneur.db"

    # Security / Auth
    jwt_secret: str = "tenderpreneur-insecure-dev-secret-key-replace-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days
    rate_limit_auth_per_minute: int = 20

    # File Storage & Ingestion Limits
    storage_type: str = "local"  # "local" or "s3"
    local_storage_path: str = "./storage"
    object_storage_endpoint: str = "http://localhost:9000"
    object_storage_bucket: str = "tenderpreneur"
    object_storage_access_key: str = "tenderpreneur"
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
    smtp_from_email: str = "noreply@tenderpreneur.co.za"

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
                    "Production security violation: TENDERPRENEUR_JWT_SECRET must be set to a cryptographically secure key of at least 32 characters in production."
                )
            if self.debug:
                raise ValueError(
                    "Production security violation: TENDERPRENEUR_DEBUG must be False in production."
                )
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="TENDERPRENEUR_",
        extra="ignore",
    )


settings = Settings()
