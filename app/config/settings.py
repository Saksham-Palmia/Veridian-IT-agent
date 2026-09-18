"""Application configuration — reads from .env file."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "Veridian IT Service Agent"
    app_version: str = "1.0.0"
    debug: bool = False

    # Database
    database_url: str = "sqlite:///./veridian.db"

    # Auth / JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    # Admin credentials
    admin_username: str = "admin"
    admin_password: str = "admin123"

    # LLM — optional
    gemini_api_key: str = ""

    # SMTP — optional (falls back to console log)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@veridian-corp.example"

    @property
    def llm_enabled(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def smtp_enabled(self) -> bool:
        return bool(self.smtp_host and self.smtp_user)


@lru_cache()
def get_settings() -> Settings:
    return Settings()

