"""CBOM API — threat clock and other CBOM endpoints."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_org
from app.models import Organization
from app.schemas.threat_clock import ThreatClockResult
from app.services.quantum_threat_clock_service import QuantumThreatClockService

router = APIRouter(prefix="/cbom", tags=["cbom"])

THREAT_CLOCK_CACHE_MAX_AGE = 3600  # 1 hour


@router.get(
    "/threat-clock",
    response_model=ThreatClockResult,
    summary="Quantum Threat Clock",
    description="Org's cryptographic debt and risk window. Cached 1 hour.",
)
async def get_threat_clock(
    response: Response,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> ThreatClockResult:
    service = QuantumThreatClockService(db)
    result = await service.compute_threat_window(org.id)
    response.headers["Cache-Control"] = f"public, max-age={THREAT_CLOCK_CACHE_MAX_AGE}"
    return result
