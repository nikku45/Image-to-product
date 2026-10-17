from typing import Annotated, List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=("backend/.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core Application Settings
    app_env: str = Field(default="development", alias="APP_ENV")
    backend_host: str = Field(default="127.0.0.1", alias="BACKEND_HOST")
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")

    # External Provider Credentials
    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-3.8-flash", alias="GEMINI_MODEL")
    gemini_timeout_seconds: float = Field(
        default=120.0,
        alias="GEMINI_TIMEOUT_SECONDS",
        description="Max wait per Gemini vision request (multimodal calls often exceed 30s)",
    )

    serpapi_api_key: Optional[str] = Field(default=None, alias="SERPAPI_API_KEY")

    # Persistence
    database_url: str = Field(default="sqlite:///./data/app.db", alias="DATABASE_URL")

    # Processing Limits & Policies
    max_upload_size_mb: int = Field(default=10, alias="MAX_UPLOAD_SIZE_MB")
    max_search_queries: int = Field(default=3, alias="MAX_SEARCH_QUERIES")
    max_candidates_per_query: int = Field(default=15, alias="MAX_CANDIDATES_PER_QUERY")

    # Security & CORS
    cors_origins: Annotated[List[str], NoDecode] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        alias="CORS_ORIGINS",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("gemini_model", mode="before")
    @classmethod
    def parse_gemini_model(cls, v):
        if not v or not str(v).strip():
            return "gemini-3.8-flash"
        return str(v).strip()

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def has_gemini_credentials(self) -> bool:
        return bool(self.gemini_api_key and self.gemini_api_key.strip())

    @property
    def has_serpapi_credentials(self) -> bool:
        return bool(self.serpapi_api_key and self.serpapi_api_key.strip())


# Cached singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
