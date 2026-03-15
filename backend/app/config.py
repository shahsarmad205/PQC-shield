"""Application configuration. Threat-clock and other settings."""
import os
from types import SimpleNamespace

def _int_env(key: str, default: int) -> int:
    v = os.environ.get(key)
    return int(v) if v is not None else default

# Defaults; override via env (MOSCA_YEAR_ESTIMATE, MIGRATION_DAYS_PER_*)
_settings = {
    "database_url": os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/pqc_shield"),
    "anthropic_api_key": os.environ.get("ANTHROPIC_API_KEY"),
    "redis_url": os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
    "jwt_secret": os.environ.get("JWT_SECRET", "change-me-in-production"),
    "jwt_algorithm": os.environ.get("JWT_ALGORITHM", "HS256"),
    "mosca_year_estimate": _int_env("MOSCA_YEAR_ESTIMATE", 2030),
    "migration_days_per_critical_asset": _int_env("MIGRATION_DAYS_PER_CRITICAL_ASSET", 5),
    "migration_days_per_high_asset": _int_env("MIGRATION_DAYS_PER_HIGH_ASSET", 3),
    "migration_days_per_medium_asset": _int_env("MIGRATION_DAYS_PER_MEDIUM_ASSET", 1),
}
settings = SimpleNamespace(**_settings)
