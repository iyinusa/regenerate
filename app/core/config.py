"""
Core configuration module for reGen API.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application settings
    app_env: Literal["dev", "test", "prod"] = "dev"
    debug: bool = False
    app_name: str = "reGen API"
    app_version: str = "0.1.0"
    enable_docs_in_production: bool = Field(
        default=False,
        description="Enable Swagger docs in production (use with caution)"
    )
    base_url: str = Field(
        default="http://localhost:8000", 
        description="Base URL for the application"
    )
    api: str = Field(
        default="/api/v1/",
        description="API prefix for the application"
    )

    # Database settings
    database_url: str = Field(
        default="",
        description="MySQL database connection URL"
    )

    # JWT settings
    jwt_secret: str = Field(default="change-me-in-production", description="JWT secret key")
    jwt_alg: str = Field(default="HS256", description="JWT algorithm")
    access_token_expires_min: int = Field(
        default=15, description="Access token expiration in minutes"
    )
    refresh_token_expires_days: int = Field(
        default=30, description="Refresh token expiration in days"
    )
    game_session_token_expires_min: int = Field(
        default=120, description="Game session token expiration in minutes (for active gameplay)"
    )

    # CORS settings
    cors_origins: str = Field(
        default="http://localhost:3000",
        description="Comma-separated list of allowed CORS origins"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # AI Provider settings
    ai_provider_api_key: str = Field(default="", description="AI provider API key")
    ai_provider_base_url: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta",
        description="AI provider base URL"
    )
    
    # Google Custom Search API settings
    google_search_api_key: str = Field(default="", description="Google Custom Search API key")
    google_search_cx_id: str = Field(default="", description="Google Custom Search Engine ID")

    # GitHub OAuth settings
    github_client_id: str = Field(default="", description="GitHub OAuth Client ID")
    github_client_secret: str = Field(default="", description="GitHub OAuth Client Secret")
    github_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/auth/github/callback",
        description="GitHub OAuth Redirect URI"
    )
    
    # LinkedIn OAuth settings
    linkedin_client_id: str = Field(default="", description="LinkedIn OAuth Client ID")
    linkedin_client_secret: str = Field(default="", description="LinkedIn OAuth Client Secret")
    linkedin_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/auth/linkedin/callback",
        description="LinkedIn OAuth Redirect URI"
    )

    # Email settings
    email_host: str = Field(default="", description="SMTP host")
    email_port: int = Field(default=587, description="SMTP port")
    email_username: str = Field(default="", description="SMTP username")
    email_password: str = Field(default="", description="SMTP password")

    # File upload settings
    upload_max_size_mb: int = Field(
        default=10, description="Maximum file upload size in MB"
    )

    # Redis settings
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    
    # Google Cloud Storage settings
    gcs_bucket_name: str = Field(
        default="regen_videos",
        description="Google Cloud Storage bucket name for videos"
    )
    gcp_project_id: str = Field(
        default="",
        description="Google Cloud Platform project ID"
    )
    google_application_credentials: str = Field(
        default="",
        description="Path to GCP service account JSON credentials file"
    )

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env == "dev"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env == "prod"

    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.app_env == "test"


# Global settings instance
settings = Settings()
