"""Audit log API — paginated list and CSV export for current org."""
import csv
import io
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_org
from app.models import AuditLog, Organization

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditLogItem(BaseModel):
    id: UUID
    org_id: UUID
    user_id: UUID | None
    operation: str
    algorithm: str | None
    ip_address: str | None
    latency_ms: float | None
    success: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogPage(BaseModel):
    items: list[AuditLogItem]
    total: int
    page: int
    page_size: int


def _parse_date(s: str | None) -> datetime | None:
    if not s or not s.strip():
        return None
    try:
        dt = datetime.strptime(s.strip()[:10], "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _end_of_day(s: str | None) -> datetime | None:
    if not s or not s.strip():
        return None
    try:
        dt = datetime.strptime(s.strip()[:10], "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc) + timedelta(days=1)
    except ValueError:
        return None


def _apply_filters(q, org_id: UUID, start_dt: datetime | None, end_dt: datetime | None, operation: str | None, algorithm: str | None):
    q = q.where(AuditLog.org_id == org_id)
    if start_dt is not None:
        q = q.where(AuditLog.created_at >= start_dt)
    if end_dt is not None:
        q = q.where(AuditLog.created_at < end_dt)
    if operation is not None and operation != "":
        q = q.where(AuditLog.operation == operation)
    if algorithm is not None and algorithm != "":
        q = q.where(AuditLog.algorithm == algorithm)
    return q


@router.get("", response_model=AuditLogPage)
async def list_audit(
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
    start_date: str | None = Query(None, description="From date (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="To date (YYYY-MM-DD)"),
    operation: str | None = Query(None),
    algorithm: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> AuditLogPage:
    start_dt = _parse_date(start_date)
    end_dt = _end_of_day(end_date)

    count_q = select(func.count(AuditLog.id))
    count_q = _apply_filters(count_q, org.id, start_dt, end_dt, operation, algorithm)
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    base = select(AuditLog)
    base = _apply_filters(base, org.id, start_dt, end_dt, operation, algorithm)
    q = base.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    rows = result.scalars().all()

    return AuditLogPage(
        items=[AuditLogItem.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/export")
async def export_audit_csv(
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    operation: str | None = Query(None),
    algorithm: str | None = Query(None),
):
    start_dt = _parse_date(start_date)
    end_dt = _end_of_day(end_date)

    base = select(AuditLog)
    base = _apply_filters(base, org.id, start_dt, end_dt, operation, algorithm)
    q = base.order_by(AuditLog.created_at.desc())
    result = await db.execute(q)
    rows = result.scalars().all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "org_id", "user_id", "operation", "algorithm", "ip_address", "latency_ms", "success", "created_at"])
    for r in rows:
        writer.writerow([
            str(r.id),
            str(r.org_id),
            str(r.user_id) if r.user_id else "",
            r.operation,
            r.algorithm or "",
            r.ip_address or "",
            r.latency_ms if r.latency_ms is not None else "",
            r.success,
            r.created_at.isoformat() if r.created_at else "",
        ])
    buf.seek(0)

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="audit_export.csv"'},
    )
