"""Settings loaded from .env and environment (pydantic-settings)."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env from backend root (parent of app/)
_backend_root = Path(__file__).resolve().parent.parent
_env_file = _backend_root / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_file if _env_file.exists() else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql+asyncpg://pqc:localdev@localhost:5432/pqcshield"
    SECRET_KEY: str = "dev-secret-change-in-production"
    GROQ_API_KEY: str = ""
    # Stripe (optional; leave empty to disable checkout/portal)
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_STARTER: str = ""
    STRIPE_PRICE_PRO: str = ""
    STRIPE_PRICE_ENTERPRISE: str = ""
    FRONTEND_URL: str = "http://localhost:5173"


settings = Settings()
