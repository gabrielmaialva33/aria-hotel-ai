"""
Configuration management for ARIA Hotel AI.

Uses pydantic-settings for environment variable management and validation.
"""

from functools import lru_cache
from typing import Any, Optional, List

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = Field(default="ARIA Hotel AI", description="Application name")
    app_env: str = Field(default="development", description="Environment (development/staging/production)")
    app_debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # API Keys
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    groq_api_key: Optional[str] = Field(default=None, description="Groq API key")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    gemini_api_key: Optional[str] = Field(default=None, description="Google Gemini API key")

    # Twilio Configuration
    twilio_account_sid: Optional[str] = Field(default=None, description="Twilio Account SID")
    twilio_auth_token: Optional[str] = Field(default=None, description="Twilio Auth Token")
    twilio_whatsapp_number: Optional[str] = Field(default=None, description="Twilio WhatsApp number")
    twilio_voice_number: Optional[str] = Field(default=None, description="Twilio voice number")
    twilio_api_key: Optional[str] = Field(default=None, description="Twilio API key")
    twilio_api_secret: Optional[str] = Field(default=None, description="Twilio API secret")

    # Database
    database_url: Optional[PostgresDsn] = Field(default=None, description="PostgreSQL connection URL")
    redis_url: RedisDsn = Field(default="redis://localhost:6379/0", description="Redis connection URL")

    # Server Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    webhook_base_url: str = Field(default="http://localhost:8000", description="Base URL for webhooks")

    # Security
    jwt_secret_key: str = Field(default="change-this-secret-key", description="JWT secret key")
    allowed_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        description="Allowed CORS origins (comma-separated)",
    )

    # Hotel Integration
    pms_api_url: Optional[str] = Field(default=None, description="PMS API URL")
    pms_api_key: Optional[str] = Field(default=None, description="PMS API key")

    # Monitoring
    sentry_dsn: Optional[str] = Field(default=None, description="Sentry DSN for error tracking")
    prometheus_port: int = Field(default=9090, description="Prometheus metrics port")

    # Feature Flags
    enable_voice_calls: bool = Field(default=True, description="Enable voice call handling")
    enable_vision_analysis: bool = Field(default=True, description="Enable image/video analysis")
    enable_proactive_messaging: bool = Field(default=True, description="Enable proactive messaging")

    # AI Model Configuration
    default_llm_model: str = Field(default="gemini-1.5-pro", description="Default LLM model")
    vision_model: str = Field(default="gemini-1.5-pro-vision", description="Vision model")
    fast_llm_model: str = Field(default="gemini-1.5-flash", description="Fast LLM for simple tasks")
    embedding_model: str = Field(default="text-embedding-3-small", description="Embedding model")

    @field_validator("app_env")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        allowed = ["development", "staging", "production", "test"]
        if v not in allowed:
            raise ValueError(f"app_env must be one of {allowed}")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return v
    

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env == "production"

    @property
    def is_test(self) -> bool:
        """Check if running in test mode."""
        return self.app_env == "test"

    def get_webhook_url(self, endpoint: str) -> str:
        """Get full webhook URL for an endpoint."""
        return f"{self.webhook_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Get allowed origins as a list."""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
