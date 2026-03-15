"""Quantum Threat Clock — cryptographic debt and risk window (Mosca's Theorem)."""
from pydantic import BaseModel, Field


class ThreatClockResult(BaseModel):
    """Result of Quantum Threat Clock compute — CISO-facing risk and migration view."""

    mosca_threat_year: int = Field(..., description="Estimated year RSA-2048 becomes breakable")
    current_year: int = Field(..., description="Current calendar year")
    years_until_threat: int = Field(..., description="mosca_threat_year - current_year")

    vulnerable_asset_count: int = Field(..., ge=0)
    critical_asset_count: int = Field(..., ge=0)
    total_asset_count: int = Field(..., ge=0)

    estimated_migration_days: int = Field(..., ge=0)
    estimated_migration_years: float = Field(..., ge=0)

    is_at_risk: bool = Field(..., description="True if migration_years > years_until_threat")
    risk_level: str = Field(..., description="critical | high | medium | low")

    harvest_now_decrypt_later_exposure: str = Field(
        ...,
        description="high | medium | low — exposure to harvest-now-decrypt-later",
    )
    recommended_urgency: str = Field(
        ...,
        description="immediate | urgent | planned | monitoring",
    )
    narrative: str = Field(..., description="2-3 sentence plain English for CISO")
    migration_velocity_needed: float = Field(
        ...,
        ge=0,
        description="Assets per month needed to finish before threat year",
    )
    compliance_deadline_risk: dict = Field(
        default_factory=dict,
        description="e.g. {'CNSA 2.0': 'at risk', 'FedRAMP': 'on track'}",
    )
