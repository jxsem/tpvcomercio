from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parent / ".env")
    DATABASE_URL: str
    TEST_DATABASE_URL: str | None = None
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]


settings = Settings()
