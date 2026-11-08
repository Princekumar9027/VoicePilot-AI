from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    environment: str = "development"
    database_url: str = "sqlite:///./voicepilot.db"
    jwt_secret: str = "dev-only-secret-change-before-production-0123456789"
    jwt_refresh_secret: str = "dev-only-refresh-secret-change-before-production"
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    max_failed_logins: int = 5
    lockout_minutes: int = 15

    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    google_client_id: str = ""
    google_client_secret: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""

    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"
    max_upload_mb: int = 10
    seed_admin_password: str = ""


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.environment == "production" and settings.jwt_secret.startswith("dev-only"):
        raise RuntimeError("JWT_SECRET must be set in production")
    return settings
