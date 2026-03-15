"""
QuantumThreatClockService — computes org's cryptographic debt and risk window.
Uses configurable MOSCA year and migration days per asset priority.
"""
import math
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Asset, CryptoFinding
from app.models.asset import Lifecycle, MigrationPriority
from app.models.crypto_finding import QuantumStatus
from app.schemas.threat_clock import ThreatClockResult

# Configurable (from settings with defaults)
def _mosca_year() -> int:
    return getattr(settings, "mosca_year_estimate", 2030)

def _days_per_critical() -> int:
    return getattr(settings, "migration_days_per_critical_asset", 5)

def _days_per_high() -> int:
    return getattr(settings, "migration_days_per_high_asset", 3)

def _days_per_medium() -> int:
    return getattr(settings, "migration_days_per_medium_asset", 1)


def _priority_bucket(priority: MigrationPriority | None, priority_score: int | None) -> str:
    if priority:
        return priority.value
    if priority_score is None:
        return "low"
    if priority_score >= 80:
        return "critical"
    if priority_score >= 60:
        return "high"
    if priority_score >= 30:
        return "medium"
    return "low"


def _exposure_level(asset_types: list[str], vulnerable_count: int) -> str:
    """high if external-facing / DB heavy; medium if mixed; low if few assets."""
    if vulnerable_count == 0:
        return "low"
    high_exposure_types = {"certificate", "api_endpoint", "database"}
    count_high = sum(1 for t in asset_types if t in high_exposure_types)
    if count_high >= 3 or vulnerable_count >= 20:
        return "high"
    if count_high >= 1 or vulnerable_count >= 5:
        return "medium"
    return "low"


def _urgency(is_at_risk: bool, exposure: str) -> str:
    if is_at_risk and exposure == "high":
        return "immediate"
    if is_at_risk or exposure == "high":
        return "urgent"
    if exposure == "medium":
        return "planned"
    return "monitoring"


def _narrative(
    is_at_risk: bool,
    window_years: int,
    migration_years_needed: int,
    vulnerable_asset_count: int,
    urgency: str,
) -> str:
    if vulnerable_asset_count == 0:
        return "No quantum-vulnerable assets in scope; continue monitoring and maintain PQC readiness."
    if is_at_risk:
        return (
            f"Your migration timeline ({migration_years_needed} years) exceeds the estimated risk window ({window_years} years). "
            f"Prioritize {vulnerable_asset_count} vulnerable assets; {urgency} action recommended."
        )
    return (
        f"Current estimate: {migration_years_needed} years to migrate {vulnerable_asset_count} vulnerable assets, "
        f"with {window_years} years until RSA-2048 risk. {urgency.capitalize()} migration pace is appropriate."
    )


class QuantumThreatClockService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def compute_threat_window(self, org_id: UUID) -> ThreatClockResult:
        """
        Compute the org's cryptographic debt and risk window.
        Returns ThreatClockResult with Mosca year, migration estimate, risk flag, and CISO narrative.
        """
        now = datetime.now(timezone.utc)
        current_year = now.year
        mosca_year = _mosca_year()
        window_years = max(0, mosca_year - current_year)

        # Active assets for org
        q_assets = (
            select(Asset)
            .where(Asset.organization_id == org_id, Asset.lifecycle == Lifecycle.ACTIVE)
        )
        result = await self._session.execute(q_assets)
        assets = list(result.scalars().all())
        asset_ids = [a.id for a in assets]

        if not asset_ids:
            return ThreatClockResult(
                mosca_theorem_year=mosca_year,
                migration_completion_estimate_year=current_year,
                window_years=window_years,
                migration_years_needed=0,
                is_at_risk=False,
                vulnerable_asset_count=0,
                harvest_now_decrypt_later_exposure="low",
                recommended_urgency="monitoring",
                narrative="No active assets in CBOM. Run discovery to assess cryptographic exposure.",
            )

        # Findings: which assets have at least one vulnerable finding
        q_findings = select(CryptoFinding).where(
            CryptoFinding.asset_id.in_(asset_ids),
            CryptoFinding.quantum_status == QuantumStatus.VULNERABLE,
        )
        find_result = await self._session.execute(q_findings)
        findings = list(find_result.scalars().all())
        vulnerable_asset_ids = {f.asset_id for f in findings}
        vulnerable_asset_count = len(vulnerable_asset_ids)

        # Migration days: sum by priority for vulnerable assets only
        vulnerable_assets = [a for a in assets if a.id in vulnerable_asset_ids]
        migration_days = 0
        for a in vulnerable_assets:
            bucket = _priority_bucket(a.migration_priority, a.priority_score)
            if bucket == "critical":
                migration_days += _days_per_critical()
            elif bucket == "high":
                migration_days += _days_per_high()
            elif bucket == "medium":
                migration_days += _days_per_medium()
            else:
                migration_days += 1

        migration_years_needed = max(0, math.ceil(migration_days / 365))
        migration_completion_estimate_year = current_year + migration_years_needed

        is_at_risk = migration_years_needed > window_years
        asset_types = [a.asset_type.value for a in vulnerable_assets]
        exposure = _exposure_level(asset_types, vulnerable_asset_count)
        urgency = _urgency(is_at_risk, exposure)
        narrative = _narrative(
            is_at_risk, window_years, migration_years_needed, vulnerable_asset_count, urgency
        )

        return ThreatClockResult(
            mosca_theorem_year=mosca_year,
            migration_completion_estimate_year=migration_completion_estimate_year,
            window_years=window_years,
            migration_years_needed=migration_years_needed,
            is_at_risk=is_at_risk,
            vulnerable_asset_count=vulnerable_asset_count,
            harvest_now_decrypt_later_exposure=exposure,
            recommended_urgency=urgency,
            narrative=narrative,
        )
