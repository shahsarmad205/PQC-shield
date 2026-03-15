"""CBOM API v1 endpoints: runs, ingest, finish, assets, summary, remediation. All require auth (get_current_org)."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_org
from app.models.cbom import Asset, CryptoFinding, DiscoveryRun, Organization, RemediationEvent
from app.models.cbom.asset import AssetType, Lifecycle, MigrationPriority
from app.models.cbom.crypto_finding import QuantumStatus
from app.models.cbom.remediation_event import RemediationAction, RemediationStatus
from app.schemas.cbom import (
    AssetDetailRead,
    AssetListResponse,
    AssetRead,
    CBOMSummary,
    CryptoFindingRead,
    DiscoveryRunRead,
    IngestResultRead,
    RemediationEventRead,
)
from app.schemas.migration_plan import MigrationPlan
from app.schemas.threat_clock import ThreatClockResult
from app.services.cbom_ingest import CBOMIngestService
from app.services.migration_planner_service import MigrationPlannerService
from app.services.quantum_threat_clock import QuantumThreatClockService

router = APIRouter()


# --- Request bodies ---

class StartRunBody(BaseModel):
    scope_id: UUID | None = None
    source: str

class IngestBody(BaseModel):
    payloads: list[dict]

class RemediationBody(BaseModel):
    asset_id: UUID
    action: RemediationAction | str
    status: RemediationStatus | str
    notes: str | None = None


class MigrationPlanBody(BaseModel):
    pass  # org from JWT


def _asset_to_read(asset: Asset, findings: list, latest_remediation=None):
    """Build AssetRead from ORM asset, list of CryptoFinding ORMs, optional RemediationEvent."""
    findings_read = [CryptoFindingRead.model_validate(f) for f in findings]
    rem_read = RemediationEventRead.model_validate(latest_remediation) if latest_remediation else None
    return AssetRead(
        id=asset.id,
        organization_id=asset.organization_id,
        scope_id=asset.scope_id,
        asset_type=asset.asset_type.value if hasattr(asset.asset_type, "value") else asset.asset_type,
        source_identifier=asset.source_identifier,
        display_name=asset.display_name,
        attributes=asset.attributes or {},
        lifecycle=asset.lifecycle.value if hasattr(asset.lifecycle, "value") else asset.lifecycle,
        migration_priority=asset.migration_priority.value if asset.migration_priority and hasattr(asset.migration_priority, "value") else asset.migration_priority,
        priority_score=asset.priority_score,
        priority_rationale=asset.priority_rationale,
        first_seen_run_id=asset.first_seen_run_id,
        last_seen_run_id=asset.last_seen_run_id,
        last_seen_at=asset.last_seen_at,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
        findings=findings_read,
        latest_remediation=rem_read,
    )


# --- Runs ---

@router.post("/runs", response_model=DiscoveryRunRead)
async def start_run(
    body: StartRunBody,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
):
    """Create a discovery run via CBOMIngestService.start_run()."""
    svc = CBOMIngestService(db)
    run = await svc.start_run(org.id, body.scope_id, body.source)
    return DiscoveryRunRead.model_validate(run)


@router.post("/runs/{run_id}/ingest", response_model=IngestResultRead)
async def ingest_run(
    run_id: UUID,
    body: IngestBody,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
):
    """Batch ingest payloads for a run."""
    run_check = await db.execute(select(DiscoveryRun).where(DiscoveryRun.id == run_id, DiscoveryRun.organization_id == org.id))
    if not run_check.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Run not found")
    svc = CBOMIngestService(db)
    result = await svc.batch_ingest(run_id, body.payloads)
    return IngestResultRead(
        assets_created=result.assets_created,
        assets_updated=result.assets_updated,
        findings_created=result.findings_created,
        findings_updated=result.findings_updated,
        errors=result.errors,
    )


@router.post("/runs/{run_id}/finish", response_model=DiscoveryRunRead)
async def finish_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
):
    """Mark run as completed and update run summary."""
    run_check = await db.execute(select(DiscoveryRun).where(DiscoveryRun.id == run_id, DiscoveryRun.organization_id == org.id))
    if not run_check.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Run not found")
    svc = CBOMIngestService(db)
    run = await svc.finish_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return DiscoveryRunRead.model_validate(run)


# --- Assets ---

@router.get("/assets", response_model=AssetListResponse)
async def list_assets(
    asset_type: AssetType | None = Query(None),
    quantum_status: str | None = Query(None, description="Filter by aggregate finding status"),
    migration_priority: MigrationPriority | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
):
    """Paginated assets with findings. Order: priority_score desc, last_seen_at desc."""
    offset = (page - 1) * page_size
    q = select(Asset).where(Asset.organization_id == org.id)
    if asset_type is not None:
        q = q.where(Asset.asset_type == asset_type)
    if migration_priority is not None:
        q = q.where(Asset.migration_priority == migration_priority)
    if quantum_status is not None:
        subq = select(CryptoFinding.asset_id).where(
            CryptoFinding.quantum_status == getattr(QuantumStatus, quantum_status, QuantumStatus.hybrid)
        ).distinct()
        q = q.where(Asset.id.in_(subq))
    count_q = select(func.count(Asset.id)).where(Asset.organization_id == org.id)
    if asset_type is not None:
        count_q = count_q.where(Asset.asset_type == asset_type)
    if migration_priority is not None:
        count_q = count_q.where(Asset.migration_priority == migration_priority)
    if quantum_status is not None:
        count_q = count_q.where(Asset.id.in_(subq))
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0
    q = q.order_by(Asset.priority_score.desc().nulls_last(), Asset.last_seen_at.desc().nulls_last()).offset(offset).limit(page_size)
    assets_result = await db.execute(q)
    assets = list(assets_result.scalars().all())
    if not assets:
        return AssetListResponse(items=[], total=total, page=page, page_size=page_size)
    asset_ids = [a.id for a in assets]
    findings_result = await db.execute(select(CryptoFinding).where(CryptoFinding.asset_id.in_(asset_ids)))
    all_findings = findings_result.scalars().all()
    findings_by_asset: dict[UUID, list] = {}
    for f in all_findings:
        findings_by_asset.setdefault(f.asset_id, []).append(f)
    rem_result = await db.execute(
        select(RemediationEvent).where(RemediationEvent.asset_id.in_(asset_ids)).order_by(RemediationEvent.created_at.desc())
    )
    rem_list = rem_result.scalars().all()
    latest_rem_by_asset: dict[UUID, RemediationEvent] = {}
    for r in rem_list:
        if r.asset_id not in latest_rem_by_asset:
            latest_rem_by_asset[r.asset_id] = r
    items = [_asset_to_read(a, findings_by_asset.get(a.id, []), latest_rem_by_asset.get(a.id)) for a in assets]
    return AssetListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/assets/{asset_id}", response_model=AssetDetailRead)
async def get_asset(
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
):
    """Full asset with all findings and all remediation events."""
    r = await db.execute(select(Asset).where(Asset.id == asset_id, Asset.organization_id == org.id))
    asset = r.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    findings_result = await db.execute(select(CryptoFinding).where(CryptoFinding.asset_id == asset_id))
    findings = list(findings_result.scalars().all())
    rem_result = await db.execute(
        select(RemediationEvent).where(RemediationEvent.asset_id == asset_id).order_by(RemediationEvent.created_at.desc())
    )
    rem_events = list(rem_result.scalars().all())
    latest_rem = rem_events[0] if rem_events else None
    base = _asset_to_read(asset, findings, latest_rem)
    remediation_reads = [RemediationEventRead.model_validate(e) for e in rem_events]
    return AssetDetailRead(**base.model_dump(), remediation_events=remediation_reads)


# --- Summary ---

@router.get("/summary", response_model=CBOMSummary)
async def get_summary(
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
):
    """Org-level CBOM summary: counts by type, quantum_status, priority; critical_count; last_scan_at; stale_asset_count."""
    count_q = select(func.count(Asset.id)).where(Asset.organization_id == org.id)
    total_result = await db.execute(count_q)
    total_assets = total_result.scalar() or 0
    by_asset_type = {}
    by_migration_priority = {}
    by_quantum_status = {"vulnerable": 0, "hybrid": 0, "quantum_safe": 0}
    critical_count = 0
    assets_result = await db.execute(select(Asset).where(Asset.organization_id == org.id))
    assets = list(assets_result.scalars().all())
    for a in assets:
        by_asset_type[a.asset_type.value] = by_asset_type.get(a.asset_type.value, 0) + 1
        if a.migration_priority:
            mp = a.migration_priority.value
            by_migration_priority[mp] = by_migration_priority.get(mp, 0) + 1
        if a.migration_priority == MigrationPriority.critical:
            critical_count += 1
    for a in assets:
        f_result = await db.execute(select(CryptoFinding).where(CryptoFinding.asset_id == a.id))
        for f in f_result.scalars().all():
            by_quantum_status[f.quantum_status.value] = by_quantum_status.get(f.quantum_status.value, 0) + 1
    stale_result = await db.execute(
        select(func.count(Asset.id)).where(Asset.organization_id == org.id, Asset.lifecycle == Lifecycle.stale)
    )
    stale_asset_count = stale_result.scalar() or 0
    last_scan_result = await db.execute(
        select(func.max(DiscoveryRun.finished_at)).where(
            DiscoveryRun.organization_id == org.id,
            DiscoveryRun.finished_at.isnot(None),
        )
    )
    last_scan_at = last_scan_result.scalar()
    return CBOMSummary(
        total_assets=total_assets,
        by_asset_type=by_asset_type,
        by_quantum_status=by_quantum_status,
        by_migration_priority=by_migration_priority,
        critical_count=critical_count,
        last_scan_at=last_scan_at,
        stale_asset_count=stale_asset_count,
    )


# --- Remediation ---

@router.post("/remediation", response_model=RemediationEventRead)
async def create_remediation(
    body: RemediationBody,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
):
    """Create a remediation event for an asset."""
    r = await db.execute(select(Asset).where(Asset.id == body.asset_id, Asset.organization_id == org.id))
    if not r.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Asset not found")
    action_enum = body.action if isinstance(body.action, RemediationAction) else getattr(RemediationAction, str(body.action), RemediationAction.deferred)
    status_enum = body.status if isinstance(body.status, RemediationStatus) else getattr(RemediationStatus, str(body.status), RemediationStatus.planned)
    event = RemediationEvent(
        asset_id=body.asset_id,
        action=action_enum,
        status=status_enum,
        notes=body.notes,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return RemediationEventRead.model_validate(event)


# --- Quantum Threat Clock ---

@router.get("/threat-clock", response_model=ThreatClockResult)
async def get_threat_clock(
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> ThreatClockResult:
    """Quantum Threat Clock: migration timeline vs Mosca threat year; CISO narrative and compliance deadlines."""
    service = QuantumThreatClockService(db)
    return await service.compute(org.id)


@router.post("/migration-plan", response_model=MigrationPlan)
async def post_migration_plan(
    body: MigrationPlanBody,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> MigrationPlan:
    """Generate a prioritized, phased PQC migration roadmap for the organization using Groq (LLaMA)."""
    service = MigrationPlannerService(db)
    try:
        return await service.generate_plan(org.id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except RuntimeError as e:
        raise HTTPException(503, str(e))