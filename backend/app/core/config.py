from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SECRET = "dev-insecure-secret-change-me-0123456789abcdef"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    database_url: str = "postgresql://apex:apex@localhost:5432/apex"
    # Direct (non-pooled) URL for Alembic; falls back to database_url.
    database_url_direct: str | None = None
    secret_key: str = DEV_SECRET
    allow_registration: bool = True
    session_days: int = 30
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-opus-5-5"
    render: bool = False  # Render sets RENDER=true on its hosts

    @model_validator(mode="after")
    def _prod_secret(self) -> "Settings":
        if self.render and (self.secret_key == DEV_SECRET or len(self.secret_key) < 32):
            raise ValueError("SECRET_KEY must be set to a random value of 32+ characters in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
