"""
CBOM Ingest Service — start runs, upsert assets/findings, recompute priority, finish runs, batch ingest.
"""
import re
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cbom import (
    Asset,
    CryptoFinding,
    DiscoveryRun,
    Organization,
    Scope,
)
from app.models.cbom.asset import AssetType, Lifecycle, MigrationPriority
from app.models.cbom.crypto_finding import FindingUsage, QuantumStatus
from app.models.cbom.discovery_run import DiscoveryRunStatus
from app.schemas.cbom import AssetCreate, CryptoFindingCreate

# --- Algorithm classification (quantum status from algorithm name) ---
QUANTUM_VULNERABLE = frozenset({
    "RSA-1024", "RSA-2048", "RSA-4096",
    "ECDSA-P256", "ECDSA-P384",
    "ECDH-P256", "DH-2048", "DSA-2048",
})
QUANTUM_SAFE = frozenset({
    "ML-KEM-512", "ML-KEM-768", "ML-KEM-1024",
    "ML-DSA-44", "ML-DSA-65", "ML-DSA-87",
    "SPHINCS+-SHA2-128f-simple", "SPHINCS+-SHA2-256s-simple",
})


def _quantum_status_for_algorithm(algorithm: str) -> str:
    """Classify algorithm as vulnerable, hybrid, or quantum_safe."""
    alg = (algorithm or "").strip()
    if alg in QUANTUM_VULNERABLE:
        return "vulnerable"
    if alg in QUANTUM_SAFE:
        return "quantum_safe"
    return "hybrid"


# --- Internal: check if host looks internal/private ---
def _is_internal_host(host: str | None) -> bool:
    if not host:
        return True
    h = host.strip().lower()
    if h in ("localhost", "127.0.0.1", "::1"):
        return True
    # IPv4 private ranges: 10.x, 172.16-31.x, 192.168.x
    if re.match(r"^10\.", h) or re.match(r"^192\.168\.", h):
        return True
    if re.match(r"^172\.(1[6-9]|2\d|3[01])\.", h):
        return True
    return False


def _parse_not_after_within_years(attrs: dict | None, years: int) -> bool:
    """True if attributes.not_after exists and is within `years` from now."""
    if not attrs or "not_after" not in attrs:
        return False
    raw = attrs["not_after"]
    if raw is None:
        return False
    try:
        s = str(raw).strip()[:30]
        if not s:
            return False
        not_after: datetime | None = None
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                not_after = datetime.strptime(s[:19], fmt)
                break
            except ValueError:
                continue
        if not_after is None:
            return False
        if not_after.tzinfo is None:
            not_after = not_after.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return (not_after - now).total_seconds() <= years * 365.25 * 24 * 3600
    except Exception:
        return False


class IngestResult:
    """Result of batch_ingest."""
    def __init__(self) -> None:
        self.assets_created: int = 0
        self.assets_updated: int = 0
        self.findings_created: int = 0
        self.findings_updated: int = 0
        self.errors: list[str] = []


class CBOMIngestService:
    """CBOM discovery run and asset/finding ingest with priority recomputation."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    # --- Method 1: start_run ---
    async def start_run(self, org_id: UUID, scope_id: UUID | None, source: str) -> DiscoveryRun:
        """Create DiscoveryRun with status=running, started_at=now."""
        run = DiscoveryRun(
            organization_id=org_id,
            scope_id=scope_id,
            started_at=self._now(),
            status=DiscoveryRunStatus.running,
            source=source,
        )
        self._db.add(run)
        await self._db.flush()
        await self._db.refresh(run)
        return run

    # --- Method 2: upsert_asset (select then update or insert via ORM) ---
    async def upsert_asset(self, run_id: UUID, asset_data: AssetCreate) -> Asset:
        """Upsert by (organization_id, scope_id, asset_type, source_identifier). Uses ORM so session has org/asset."""
        at = asset_data.asset_type
        if isinstance(at, str) and hasattr(AssetType, at):
            at = getattr(AssetType, at)
        out = await self._db.execute(
            select(Asset).where(
                Asset.organization_id == asset_data.organization_id,
                Asset.scope_id == asset_data.scope_id,
                Asset.asset_type == at,
                Asset.source_identifier == asset_data.source_identifier,
            ).limit(1)
        )
        existing = out.scalar_one_or_none()
        if existing:
            existing.last_seen_run_id = run_id
            existing.last_seen_at = self._now()
            existing.display_name = asset_data.display_name
            existing.attributes = asset_data.attributes or {}
            existing.lifecycle = Lifecycle.active
            await self._db.flush()
            return existing
        asset = Asset(
            organization_id=asset_data.organization_id,
            scope_id=asset_data.scope_id,
            asset_type=at,
            source_identifier=asset_data.source_identifier,
            display_name=asset_data.display_name,
            attributes=asset_data.attributes or {},
            first_seen_run_id=run_id,
            last_seen_run_id=run_id,
            last_seen_at=self._now(),
            lifecycle=Lifecycle.active,
            migration_priority=asset_data.migration_priority,
            priority_score=asset_data.priority_score,
            priority_rationale=asset_data.priority_rationale,
        )
        self._db.add(asset)
        await self._db.flush()
        return asset

    # --- Method 3: upsert_finding (by asset_id, algorithm, usage) ---
    async def upsert_finding(self, asset_id: UUID, finding_data: CryptoFindingCreate, *, recompute_priority: bool = True, flush_after: bool = True) -> CryptoFinding:
        """Upsert by (asset_id, algorithm, usage). If flush_after=False, only add/update, do not flush (caller flushes once)."""
        quantum_status = finding_data.quantum_status or _quantum_status_for_algorithm(finding_data.algorithm)
        usage_val = finding_data.usage if isinstance(finding_data.usage, str) else finding_data.usage.value

        usage_enum = getattr(FindingUsage, usage_val, FindingUsage.unknown) if isinstance(usage_val, str) else usage_val
        existing = await self._db.execute(
            select(CryptoFinding).where(
                CryptoFinding.asset_id == asset_id,
                CryptoFinding.algorithm == finding_data.algorithm,
                CryptoFinding.usage == usage_enum,
            ).limit(1)
        )
        one = existing.scalar_one_or_none()
        if one:
            one.quantum_status = getattr(QuantumStatus, quantum_status, QuantumStatus.hybrid)
            one.key_created_at = finding_data.key_created_at
            one.key_expires_at = finding_data.key_expires_at
            one.finding_metadata = finding_data.finding_metadata
            one.risk_score = finding_data.risk_score
            one.cve_refs = finding_data.cve_refs
            if flush_after:
                await self._db.flush()
            if recompute_priority:
                await self._recompute_asset_status(asset_id)
            return one

        finding = CryptoFinding(
            asset_id=asset_id,
            algorithm=finding_data.algorithm,
            usage=usage_enum,
            quantum_status=getattr(QuantumStatus, quantum_status, QuantumStatus.hybrid),
            key_created_at=finding_data.key_created_at,
            key_expires_at=finding_data.key_expires_at,
            finding_metadata=finding_data.finding_metadata,
            risk_score=finding_data.risk_score,
            cve_refs=finding_data.cve_refs,
        )
        self._db.add(finding)
        if flush_after:
            await self._db.flush()
        if recompute_priority:
            await self._recompute_asset_status(asset_id)
        return finding

    # --- Method 4: _recompute_asset_status ---
    async def _recompute_asset_status(self, asset_id: UUID) -> None:
        """Load findings for asset, set priority via _compute_priority, write back with explicit UPDATE."""
        asset_result = await self._db.execute(select(Asset).where(Asset.id == asset_id))
        asset = asset_result.scalar_one_or_none()
        if not asset:
            return
        findings_result = await self._db.execute(
            select(CryptoFinding).where(CryptoFinding.asset_id == asset_id)
        )
        findings = list(findings_result.scalars().all())
        priority, score, rationale = _compute_priority(asset, findings)
        priority_enum = getattr(MigrationPriority, priority, None) if priority in ("critical", "high", "medium", "low", "none") else None
        # Explicit UPDATE so priority is persisted; no flush needed (execute runs the statement).
        await self._db.execute(
            update(Asset).where(Asset.id == asset_id).values(
                migration_priority=priority_enum,
                priority_score=score,
                priority_rationale=rationale,
            )
        )

    # --- Method 5: _compute_priority (module-level for reuse) ---
    # Implemented as standalone function below.

    # --- Method 6: finish_run ---
    async def finish_run(self, run_id: UUID) -> DiscoveryRun:
        """Set status=completed, finished_at=now; mark unseen assets stale; update run summary."""
        run_result = await self._db.execute(select(DiscoveryRun).where(DiscoveryRun.id == run_id))
        run = run_result.scalar_one_or_none()
        if not run:
            raise ValueError(f"DiscoveryRun {run_id} not found")
        run.status = DiscoveryRunStatus.completed
        run.finished_at = self._now()
        await self._db.flush()

        # Recompute priority for all assets in this run's org/scope (findings are now complete).
        assets_result = await self._db.execute(
            select(Asset.id).where(
                Asset.organization_id == run.organization_id,
                Asset.scope_id == run.scope_id,
            )
        )
        for asset_id in assets_result.scalars().all():
            await self._recompute_asset_status(asset_id)

        # Mark assets in same org/scope with last_seen_run_id != run_id and lifecycle=active → stale
        await self._db.execute(
            update(Asset).where(
                Asset.organization_id == run.organization_id,
                Asset.scope_id == run.scope_id,
                Asset.lifecycle == Lifecycle.active,
                Asset.last_seen_run_id != run_id,
            ).values(lifecycle=Lifecycle.stale)
        )

        # Summary: count assets by type, by quantum_status (from findings), count findings
        assets_result = await self._db.execute(
            select(Asset).where(
                Asset.organization_id == run.organization_id,
                Asset.scope_id == run.scope_id,
            )
        )
        assets = list(assets_result.scalars().all())
        by_asset_type: dict[str, int] = {}
        by_quantum_status: dict[str, int] = {"vulnerable": 0, "hybrid": 0, "quantum_safe": 0}
        findings_total = 0
        for a in assets:
            by_asset_type[a.asset_type.value] = by_asset_type.get(a.asset_type.value, 0) + 1
            find_result = await self._db.execute(select(CryptoFinding).where(CryptoFinding.asset_id == a.id))
            for f in find_result.scalars().all():
                findings_total += 1
                by_quantum_status[f.quantum_status.value] = by_quantum_status.get(f.quantum_status.value, 0) + 1
        run.summary = {
            "assets_by_type": by_asset_type,
            "findings_by_quantum_status": by_quantum_status,
            "findings_total": findings_total,
            "assets_count": len(assets),
        }
        await self._db.flush()
        await self._db.refresh(run)
        return run

    # --- Method 7: batch_ingest ---
    async def batch_ingest(self, run_id: UUID, payloads: list[dict]) -> IngestResult:
        """Normalize payloads by type, upsert_asset + upsert_finding(s); processed sequentially (shared session).
        Note: With multiple payloads in one request, SQLAlchemy may raise \"Session is already flushing\";
        workaround: send one payload per POST request, then call finish_run to recompute priorities."""
        result = IngestResult()
        run_result = await self._db.execute(select(DiscoveryRun).where(DiscoveryRun.id == run_id))
        run = run_result.scalar_one_or_none()
        if not run:
            result.errors.append(f"Run {run_id} not found")
            return result
        org_id = run.organization_id
        scope_id = run.scope_id
        # Load org (and scope if any) into session so FK checks don't trigger a nested flush.
        await self._db.execute(select(Organization).where(Organization.id == org_id))
        if scope_id:
            await self._db.execute(select(Scope).where(Scope.id == scope_id))

        # Disable autoflush so we only flush once at the end (avoids "Session is already flushing").
        autoflush = self._db.autoflush
        self._db.autoflush = False
        try:

            async def process_one(payload: dict) -> tuple[int, int, int, int, list[str]]:
                created_a, updated_a, created_f, updated_f = 0, 0, 0, 0
                errs: list[str] = []
                try:
                    normalized = _normalize_payload(payload, org_id, scope_id)
                    if not normalized:
                        errs.append(f"Skip invalid payload: {payload!r}")
                        return (0, 0, 0, 0, errs)
                    asset_data, findings_data = normalized
                    at = asset_data.asset_type
                    if isinstance(at, str) and hasattr(AssetType, at):
                        at = getattr(AssetType, at)
                    existed = await self._db.execute(
                        select(Asset.id).where(
                            Asset.organization_id == asset_data.organization_id,
                            Asset.scope_id == asset_data.scope_id,
                            Asset.asset_type == at,
                            Asset.source_identifier == asset_data.source_identifier,
                        ).limit(1)
                    )
                    had_asset = existed.scalar_one_or_none() is not None
                    asset = await self.upsert_asset(run_id, asset_data)
                    if had_asset:
                        updated_a += 1
                    else:
                        created_a += 1
                    for fd in findings_data:
                        try:
                            usage_val = fd.usage if isinstance(fd.usage, str) else getattr(fd.usage, "value", fd.usage)
                            usage_enum = getattr(FindingUsage, usage_val, FindingUsage.unknown) if isinstance(usage_val, str) else usage_val
                            existing_before = await self._db.execute(
                                select(CryptoFinding.id).where(
                                    CryptoFinding.asset_id == asset.id,
                                    CryptoFinding.algorithm == fd.algorithm,
                                    CryptoFinding.usage == usage_enum,
                                ).limit(1)
                            )
                            had_f = existing_before.scalar_one_or_none() is not None
                            await self.upsert_finding(asset.id, fd, recompute_priority=False, flush_after=False)
                            if had_f:
                                updated_f += 1
                            else:
                                created_f += 1
                        except Exception as e:
                            errs.append(f"Finding upsert failed: {e!s}")
                except Exception as e:
                    errs.append(f"Payload failed: {e!s}")
                return (created_a, updated_a, created_f, updated_f, errs)

            for payload in payloads:
                try:
                    c_a, u_a, c_f, u_f, errs = await process_one(payload)
                    result.assets_created += c_a
                    result.assets_updated += u_a
                    result.findings_created += c_f
                    result.findings_updated += u_f
                    result.errors.extend(errs)
                except Exception as e:
                    result.errors.append(str(e))
        finally:
            self._db.autoflush = autoflush
        await self._db.flush()
        return result


def _compute_priority(asset: Asset, findings: list[CryptoFinding]) -> tuple[str, int, str]:
    """Return (MigrationPriority value, score, rationale). First match wins. Uses enum for asset_type."""
    # Debug: ensure asset_type is populated for priority rules
    assert asset.asset_type is not None, "asset.asset_type must be set for priority computation"
    statuses = [f.quantum_status.value for f in findings]
    attrs = asset.attributes or {}
    asset_type_enum = asset.asset_type if isinstance(asset.asset_type, AssetType) else getattr(AssetType, str(asset.asset_type), None)

    # certificate + vulnerable + not_after within 2 years → critical, 95
    if asset_type_enum == AssetType.certificate and "vulnerable" in statuses:
        if _parse_not_after_within_years(attrs, 2):
            return ("critical", 95, "Expiring quantum-vulnerable certificate")

    # api_endpoint + vulnerable + host not internal → critical, 90
    if asset_type_enum == AssetType.api_endpoint and "vulnerable" in statuses:
        host = attrs.get("host") or attrs.get("base_url") or ""
        if not _is_internal_host(str(host)):
            return ("critical", 90, "Public-facing quantum-vulnerable API")

    # any + vulnerable → high, 70
    if "vulnerable" in statuses:
        return ("high", 70, "Quantum-vulnerable algorithm in use")

    # any + hybrid → medium, 40
    if "hybrid" in statuses:
        return ("medium", 40, "Hybrid transition in progress")

    # quantum_safe only
    return ("low", 10, "Quantum safe")


def _normalize_payload(payload: dict, org_id: UUID, scope_id: UUID | None) -> tuple[AssetCreate, list[CryptoFindingCreate]] | None:
    """Normalize payload to (AssetCreate, list[CryptoFindingCreate]). Return None if invalid."""
    try:
        kind = (payload.get("type") or payload.get("asset_type") or "api_endpoint").lower()
        source_id = payload.get("source_identifier") or payload.get("thumbprint") or payload.get("host") or payload.get("file_path") or payload.get("id") or ""
        if not source_id:
            source_id = str(payload.get("id", "")) or None
        if not source_id:
            return None
        display_name = payload.get("display_name") or payload.get("subject") or payload.get("host") or payload.get("base_url") or payload.get("file_path") or source_id
        attributes = payload.get("attributes") or {}
        if not attributes and kind == "certificate":
            attributes = {k: payload.get(k) for k in ("subject", "issuer", "serial", "thumbprint", "not_before", "not_after", "key_algorithm", "key_size_or_oid", "store_location", "chain_position") if payload.get(k) is not None}
        if not attributes and kind == "api_endpoint":
            attributes = {k: payload.get(k) for k in ("host", "base_url", "method", "path", "tls_version", "auth_scheme", "protocol") if payload.get(k) is not None}
        if not attributes and kind == "source_code":
            attributes = {k: payload.get(k) for k in ("repo", "repo_url", "branch", "file_path", "line_start", "line_end", "symbol_or_pattern", "language", "context_snippet") if payload.get(k) is not None}
        if not attributes and kind == "network_protocol":
            attributes = {k: payload.get(k) for k in ("protocol", "role", "host_or_endpoint", "port") if payload.get(k) is not None}

        asset_create = AssetCreate(
            organization_id=org_id,
            scope_id=scope_id,
            asset_type=kind,
            source_identifier=str(source_id)[:1024],
            display_name=str(display_name)[:512] if display_name else None,
            attributes=attributes,
            lifecycle="active",
        )
        findings_data: list[CryptoFindingCreate] = []
        raw_findings = payload.get("findings") or payload.get("algorithms") or []
        if isinstance(raw_findings, dict):
            raw_findings = [{"algorithm": k, "usage": v} if isinstance(v, str) else {"algorithm": k, **v} for k, v in raw_findings.items()]
        for f in raw_findings:
            if isinstance(f, str):
                findings_data.append(CryptoFindingCreate(asset_id=UUID(int=0), algorithm=f, usage="unknown", quantum_status=_quantum_status_for_algorithm(f)))
            else:
                alg = f.get("algorithm") or f.get("alg") or ""
                usage = f.get("usage") or f.get("purpose") or "unknown"
                findings_data.append(CryptoFindingCreate(
                    asset_id=UUID(int=0),
                    algorithm=alg[:128],
                    usage=usage,
                    quantum_status=f.get("quantum_status") or _quantum_status_for_algorithm(alg),
                    key_created_at=f.get("key_created_at"),
                    key_expires_at=f.get("key_expires_at"),
                    finding_metadata=f.get("metadata") or f.get("finding_metadata"),
                    risk_score=f.get("risk_score"),
                    cve_refs=f.get("cve_refs"),
                ))
        if not findings_data and payload.get("algorithm"):
            findings_data.append(CryptoFindingCreate(
                asset_id=UUID(int=0),
                algorithm=str(payload["algorithm"])[:128],
                usage=payload.get("usage") or "unknown",
                quantum_status=payload.get("quantum_status") or _quantum_status_for_algorithm(str(payload["algorithm"])),
            ))
        return (asset_create, findings_data)
    except Exception:
        return None
