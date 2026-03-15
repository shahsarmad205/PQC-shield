"""
MeteringService — Redis-backed quota check and async audit log writes.
"""
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, Organization


class MeteringService:
    """Redis metering and async audit log writes."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def _quota_key(self, org_id: str) -> str:
        now = datetime.now(timezone.utc)
        return f"quota:{org_id}:{now.strftime('%Y-%m')}"

    async def check_and_increment(self, org: Organization) -> None:
        """
        Increment monthly ops count for the org in Redis atomically.
        If over org.monthly_quota after increment, decrement back and raise HTTP 429
        with JSON body {ops_used, quota_limit}.
        """
        key = self._quota_key(str(org.id))
        quota_limit = org.monthly_quota

        used = await self._redis.incr(key)
        if used > quota_limit:
            await self._redis.decr(key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "ops_used": used - 1,
                    "quota_limit": quota_limit,
                },
            )

    async def write_audit(
        self,
        org: Organization,
        operation: str,
        algorithm: str | None,
        latency_ms: float | None,
        success: bool,
        db: AsyncSession,
        *,
        user_id: uuid.UUID | None = None,
        ip_address: str | None = None,
    ) -> None:
        """Write an audit log row for the org. Does not commit; caller's session commits."""
        entry = AuditLog(
            org_id=org.id,
            user_id=user_id,
            operation=operation,
            algorithm=algorithm,
            ip_address=ip_address,
            latency_ms=latency_ms,
            success=success,
        )
        db.add(entry)
        await db.flush()
