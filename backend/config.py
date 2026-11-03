from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parent / ".env")
    DATABASE_URL: str
    TEST_DATABASE_URL: str | None = None
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
    # Sin valor por defecto a propósito: un secreto por defecto acabaría en producción.
    # Generar uno con: python -c "import secrets; print(secrets.token_urlsafe(48))"
    JWT_SECRET: str = Field(min_length=32)
    # Vida corta: un JWT no se puede revocar antes de que caduque.
    JWT_EXPIRE_MINUTES: int = Field(default=60, ge=1, le=1440)


settings = Settings()
