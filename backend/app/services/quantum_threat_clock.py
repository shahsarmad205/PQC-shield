"""
Quantum Threat Clock — answers: "Do we have enough time to migrate before quantum computers break our encryption?"
Based on Mosca's Theorem: if (time to migrate) + (shelf life of data) > (time to quantum threat), you are already at risk.
"""
import math
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cbom import Asset, CryptoFinding
from app.models.cbom.asset import AssetType, Lifecycle, MigrationPriority
from app.models.cbom.crypto_finding import QuantumStatus
from app.schemas.threat_clock import ThreatClockResult as ThreatClockResultSchema

# --- Configurable constants ---
MOSCA_THREAT_YEAR = 2030
DAYS_PER_CRITICAL_ASSET = 5
DAYS_PER_HIGH_ASSET = 3
DAYS_PER_MEDIUM_ASSET = 1
DAYS_PER_LOW_ASSET = 0.25

# Compliance deadlines (year): "at risk" if estimated completion year > deadline
COMPLIANCE_DEADLINES: dict[str, int] = {
    "CNSA 2.0": 2030,
    "FedRAMP Rev 5": 2028,
    "NIST SP 800-208": 2030,
    "EU NIS2": 2027,
}


class QuantumThreatClockService:
    """Computes org's quantum migration risk and timeline (Mosca's Theorem)."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def compute(self, org_id: UUID) -> ThreatClockResultSchema:
        """
        Compute threat clock for the organization.
        Returns ThreatClockResult (schema) with Mosca year, migration estimate, risk level, and CISO narrative.
        """
        now = datetime.now(timezone.utc)
        current_year = now.year
        mosca_threat_year = MOSCA_THREAT_YEAR
        years_until_threat = max(0, mosca_threat_year - current_year)

        # 1. Query org's active assets
        assets_result = await self._db.execute(
            select(Asset).where(
                Asset.organization_id == org_id,
                Asset.lifecycle == Lifecycle.active,
            )
        )
        assets = list(assets_result.scalars().all())
        total_asset_count = len(assets)
        asset_ids = [a.id for a in assets]

        if not asset_ids:
            return self._empty_result(mosca_threat_year, current_year, years_until_threat)

        # Assets with at least one vulnerable finding
        findings_result = await self._db.execute(
            select(CryptoFinding.asset_id).where(
                CryptoFinding.asset_id.in_(asset_ids),
                CryptoFinding.quantum_status == QuantumStatus.vulnerable,
            ).distinct()
        )
        vulnerable_asset_ids = {row[0] for row in findings_result.all()}
        vulnerable_asset_count = len(vulnerable_asset_ids)
        vulnerable_assets = [a for a in assets if a.id in vulnerable_asset_ids]

        # Count by migration_priority (for all assets, for display)
        critical_asset_count = sum(
            1 for a in assets
            if a.migration_priority == MigrationPriority.critical
        )

        # 2. Estimated migration days from vulnerable assets × day weights
        estimated_migration_days_float = 0.0
        for a in vulnerable_assets:
            prio = a.migration_priority
            if prio == MigrationPriority.critical:
                estimated_migration_days_float += DAYS_PER_CRITICAL_ASSET
            elif prio == MigrationPriority.high:
                estimated_migration_days_float += DAYS_PER_HIGH_ASSET
            elif prio == MigrationPriority.medium:
                estimated_migration_days_float += DAYS_PER_MEDIUM_ASSET
            else:
                estimated_migration_days_float += DAYS_PER_LOW_ASSET
        estimated_migration_days = max(0, int(math.ceil(estimated_migration_days_float)))
        estimated_migration_years = estimated_migration_days_float / 365.0

        # 4. is_at_risk = estimated_migration_years > years_until_threat
        is_at_risk = estimated_migration_years > years_until_threat

        # 5. harvest_exposure: high if any critical cert/api_endpoint; medium if high/vulnerable; low otherwise
        harvest_now_decrypt_later_exposure = self._harvest_exposure(vulnerable_assets)

        # 6. risk_level
        risk_level = self._risk_level(
            is_at_risk, vulnerable_asset_count, estimated_migration_years, years_until_threat,
        )

        # 7. recommended_urgency
        recommended_urgency = self._recommended_urgency(risk_level)

        # 8. compliance_deadline_risk
        estimated_completion_year = current_year + int(math.ceil(estimated_migration_years))
        compliance_deadline_risk = {
            name: "at risk" if estimated_completion_year > deadline else "on track"
            for name, deadline in COMPLIANCE_DEADLINES.items()
        }

        # 9. narrative
        narrative = self._narrative(
            total_asset_count, vulnerable_asset_count, critical_asset_count,
            estimated_migration_days, estimated_migration_years, years_until_threat,
            is_at_risk, risk_level, recommended_urgency,
        )

        # migration_velocity_needed: assets per month to finish in time
        months_until_threat = max(0.01, years_until_threat * 12)
        migration_velocity_needed = vulnerable_asset_count / months_until_threat if vulnerable_asset_count else 0.0

        return ThreatClockResultSchema(
            mosca_threat_year=mosca_threat_year,
            current_year=current_year,
            years_until_threat=years_until_threat,
            vulnerable_asset_count=vulnerable_asset_count,
            critical_asset_count=critical_asset_count,
            total_asset_count=total_asset_count,
            estimated_migration_days=estimated_migration_days,
            estimated_migration_years=round(estimated_migration_years, 2),
            is_at_risk=is_at_risk,
            risk_level=risk_level,
            harvest_now_decrypt_later_exposure=harvest_now_decrypt_later_exposure,
            recommended_urgency=recommended_urgency,
            narrative=narrative,
            migration_velocity_needed=round(migration_velocity_needed, 2),
            compliance_deadline_risk=compliance_deadline_risk,
        )

    def _empty_result(
        self,
        mosca_threat_year: int,
        current_year: int,
        years_until_threat: int,
    ) -> ThreatClockResultSchema:
        return ThreatClockResultSchema(
            mosca_threat_year=mosca_threat_year,
            current_year=current_year,
            years_until_threat=years_until_threat,
            vulnerable_asset_count=0,
            critical_asset_count=0,
            total_asset_count=0,
            estimated_migration_days=0,
            estimated_migration_years=0.0,
            is_at_risk=False,
            risk_level="low",
            harvest_now_decrypt_later_exposure="low",
            recommended_urgency="monitoring",
            narrative="No active assets in CBOM. Run discovery to assess cryptographic exposure.",
            migration_velocity_needed=0.0,
            compliance_deadline_risk={k: "on track" for k in COMPLIANCE_DEADLINES},
        )

    def _harvest_exposure(self, vulnerable_assets: list[Asset]) -> str:
        """high = certs or classified APIs with vulnerable crypto; medium = internal vulnerable; low = mostly safe."""
        if not vulnerable_assets:
            return "low"
        critical_external = [
            a for a in vulnerable_assets
            if a.migration_priority == MigrationPriority.critical
            and a.asset_type in (AssetType.certificate, AssetType.api_endpoint)
        ]
        if critical_external:
            return "high"
        if vulnerable_assets:
            return "medium"
        return "low"

    def _risk_level(
        self,
        is_at_risk: bool,
        vulnerable_asset_count: int,
        estimated_migration_years: float,
        years_until_threat: int,
    ) -> str:
        if is_at_risk and vulnerable_asset_count > 0:
            return "critical"
        if years_until_threat <= 0:
            return "critical" if vulnerable_asset_count > 0 else "low"
        threshold_80 = years_until_threat * 0.8
        threshold_50 = years_until_threat * 0.5
        if estimated_migration_years > threshold_80:
            return "high"
        if estimated_migration_years > threshold_50:
            return "medium"
        return "low"

    def _recommended_urgency(self, risk_level: str) -> str:
        if risk_level == "critical":
            return "immediate"
        if risk_level == "high":
            return "urgent"
        if risk_level == "medium":
            return "planned"
        return "monitoring"

    def _narrative(
        self,
        total_asset_count: int,
        vulnerable_asset_count: int,
        critical_asset_count: int,
        estimated_migration_days: int,
        estimated_migration_years: float,
        years_until_threat: int,
        is_at_risk: bool,
        risk_level: str,
        recommended_urgency: str,
    ) -> str:
        if vulnerable_asset_count == 0:
            return (
                f"Of {total_asset_count} assets in scope, none are currently quantum-vulnerable. "
                "Continue monitoring and maintain PQC readiness."
            )
        months = max(1, int(estimated_migration_years * 12))
        if is_at_risk:
            return (
                f"Your organization has {vulnerable_asset_count} quantum-vulnerable assets ({critical_asset_count} critical) "
                f"requiring an estimated {months} months to migrate. "
                f"With {years_until_threat} years until the estimated RSA-2048 threat window, you are at risk. "
                f"{recommended_urgency.capitalize()} action is recommended."
            )
        return (
            f"Your organization has {vulnerable_asset_count} quantum-vulnerable assets requiring an estimated "
            f"{months} months to migrate. With {years_until_threat} years until the threat window, "
            f"{recommended_urgency} migration pace is appropriate."
        )
