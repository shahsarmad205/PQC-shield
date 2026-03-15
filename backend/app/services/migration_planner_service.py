"""
MigrationPlannerService — generates a prioritized, phased migration roadmap from CBOM
using the Groq API (OpenAI-compatible). Caches plans in migration_plans table when available.
"""
import json
import re
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from groq import Groq
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.cbom import Asset, CryptoFinding, Organization
from app.models.cbom.asset import AssetType, Lifecycle
from app.models.migration_plan_stored import MigrationPlanStored
from app.schemas.migration_plan import MigrationPhase, MigrationPlan

GROQ_MODEL = "llama-3.3-70b-versatile"

# Priority buckets: critical 80-100, high 60-79, medium 30-59, low 0-29
BUCKETS = [
    ("critical", 80, 100),
    ("high", 60, 79),
    ("medium", 30, 59),
    ("low", 0, 29),
]


def _bucket(priority_score: int | None) -> str:
    if priority_score is None:
        return "low"
    for name, lo, hi in BUCKETS:
        if lo <= (priority_score or 0) <= hi:
            return name
    return "low"


def _asset_summary(assets: list[Asset], findings_by_asset: dict[UUID, list[CryptoFinding]]) -> dict:
    by_type: dict[str, int] = {}
    by_quantum: dict[str, int] = {}
    for a in assets:
        by_type[a.asset_type.value] = by_type.get(a.asset_type.value, 0) + 1
        for f in findings_by_asset.get(a.id, []):
            by_quantum[f.quantum_status.value] = by_quantum.get(f.quantum_status.value, 0) + 1
    return {"by_asset_type": by_type, "by_quantum_status": by_quantum}


def _build_system_prompt() -> str:
    return (
        "You are a post-quantum migration expert. Generate a prioritized, phased migration roadmap "
        "based on the organization's Cryptographic Bill of Materials (CBOM). "
        "Output a single JSON object only (no markdown, no code fence) with this shape: "
        '{"summary": "...", "executive_summary": "2-3 sentences for leadership", "quick_wins": ["action 1", "..."], '
        '"recommended_algorithms": ["ML-KEM-768", "ML-DSA-65", "..."], '
        '"phases": [{"phase_number": 1, "title": "...", "description": "...", "asset_ids": ["uuid", ...], '
        '"estimated_effort_days": N, "compliance_impact": ["NIST SP 800-208", ...]}, ...]}. '
        "Rules: Phase 1 = external/expiring keys (quick wins). Phase 2 = internal APIs/databases. "
        "Phase 3 = source code. Phase 4 = network. Include 3–5 phases. "
        "recommended_algorithms: suggest PQC algorithms e.g. ML-KEM-768, ML-DSA-65. "
        "quick_wins: list 2–5 immediate actions. asset_ids: use UUIDs from the input only."
    )


def _build_prompt(
    org_name: str,
    asset_summary: dict,
    top_assets: list[tuple[Asset, list[CryptoFinding]]],
    compliance_frameworks: list[str],
) -> str:
    lines = [
        "## Organization",
        f"Name: {org_name}",
        "",
        "## Asset summary",
        json.dumps(asset_summary, indent=2),
        "",
        "## Top 20 critical/high assets (with findings)",
        "Each asset has: id, asset_type, display_name, priority_score, priority_rationale, attributes (JSON). Findings list: algorithm, usage, quantum_status, key_expires_at.",
    ]
    for i, (asset, findings) in enumerate(top_assets[:20], 1):
        attrs = getattr(asset, "attributes", None) or {}
        expiring = [f for f in findings if getattr(f, "key_expires_at", None)]
        lines.append(f"\n### Asset {i}: {asset.display_name or asset.source_identifier} (id={asset.id})")
        lines.append(f"  type={asset.asset_type.value} priority_score={asset.priority_score} rationale={asset.priority_rationale or 'N/A'}")
        lines.append(f"  attributes: {json.dumps(attrs)}")
        lines.append("  findings:")
        for f in findings:
            lines.append(f"    - {f.algorithm} ({f.usage.value}) quantum={f.quantum_status.value} key_expires_at={getattr(f, 'key_expires_at', None)}")
        if expiring:
            lines.append(f"  (has {len(expiring)} finding(s) with key expiry)")

    lines.extend([
        "",
        "## Compliance frameworks the org must meet",
        json.dumps(compliance_frameworks),
        "",
        "Output only the JSON object as described in the system prompt.",
    ])
    return "\n".join(lines)


def _parse_plan_from_response(text: str, generated_at: datetime) -> MigrationPlan:
    """Parse JSON from response (Groq returns pure JSON; fallback to regex strip if needed)."""
    text = text.strip()
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as e:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            raise HTTPException(500, f"AI returned invalid JSON: {e}") from e
        try:
            raw = json.loads(m.group(0))
        except json.JSONDecodeError as e2:
            raise HTTPException(500, f"AI returned invalid JSON: {e2}") from e2
    phases = [
        MigrationPhase(
            phase_number=p["phase_number"],
            title=p["title"],
            description=p["description"],
            asset_ids=[str(x) for x in p.get("asset_ids", [])],
            estimated_effort_days=int(p.get("estimated_effort_days", 0)),
            compliance_impact=list(p.get("compliance_impact", [])),
        )
        for p in raw.get("phases", [])
    ]
    return MigrationPlan(
        summary=raw.get("summary", ""),
        phases=phases,
        generated_at=generated_at.isoformat(),
        executive_summary=raw.get("executive_summary"),
        quick_wins=list(raw.get("quick_wins", [])),
        recommended_algorithms=list(raw.get("recommended_algorithms", [])),
    )


class MigrationPlannerService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._client = Groq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None

    async def generate_plan(self, org_id: UUID, scope_id: UUID | None = None) -> MigrationPlan:
        """
        Generate a prioritized, phased migration roadmap from the org's CBOM.
        Queries active assets with findings, groups by priority, calls Groq, returns plan.
        """
        if not self._client or not settings.GROQ_API_KEY:
            raise RuntimeError(
                "Groq API key not configured. Set GROQ_API_KEY in backend/.env "
                "(or export GROQ_API_KEY) and restart the server."
            )

        org_result = await self._session.execute(select(Organization).where(Organization.id == org_id))
        org = org_result.scalar_one_or_none()
        if not org:
            raise ValueError("Organization not found")

        settings_dict = getattr(org, "settings", None) or {}
        compliance_frameworks = (
            settings_dict.get("compliance_frameworks")
            if isinstance(settings_dict, dict)
            else None
        ) or ["NIST SP 800-208", "NSA CNSA 2.0"]

        # 1. Query active assets with findings, ordered by priority_score desc
        q = (
            select(Asset)
            .where(Asset.organization_id == org_id, Asset.lifecycle == Lifecycle.active)
        )
        if scope_id is not None:
            q = q.where(Asset.scope_id == scope_id)
        q = q.order_by(Asset.priority_score.desc().nulls_last())
        result = await self._session.execute(q)
        assets = list(result.scalars().all())

        if not assets:
            return MigrationPlan(
                summary="No active assets in CBOM. Run discovery scans to populate assets, then regenerate.",
                phases=[],
                generated_at=datetime.now(timezone.utc).isoformat(),
            )

        asset_ids = [a.id for a in assets]
        find_result = await self._session.execute(
            select(CryptoFinding).where(CryptoFinding.asset_id.in_(asset_ids))
        )
        findings = list(find_result.scalars().all())
        findings_by_asset: dict[UUID, list[CryptoFinding]] = {}
        for f in findings:
            findings_by_asset.setdefault(f.asset_id, []).append(f)

        # 2. Group into buckets; take top 20 critical/high
        critical_high = [
            a for a in assets
            if _bucket(a.priority_score) in ("critical", "high")
        ][:20]
        if not critical_high:
            critical_high = assets[:20]

        top_assets = [(a, findings_by_asset.get(a.id, [])) for a in critical_high]
        asset_summary = _asset_summary(assets, findings_by_asset)

        # 3–4. Build prompts and call Groq
        system_prompt = _build_system_prompt()
        user_prompt = _build_prompt(
            getattr(org, "name", "Organization"),
            asset_summary,
            top_assets,
            compliance_frameworks,
        )
        generated_at = datetime.now(timezone.utc)
        response = self._client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )
        result_text = response.choices[0].message.content if response.choices else ""

        # 5. Parse and validate
        plan = _parse_plan_from_response(result_text, generated_at)

        if assets and len(plan.phases) < 3:
            raise ValueError("AI did not return 3–5 phases")

        # 6. Cache in DB (optional; table may be legacy)
        try:
            stored = MigrationPlanStored(
                organization_id=org_id,
                scope_id=scope_id,
                plan_json=plan.model_dump(mode="json"),
                generated_at=generated_at,
                model_used=GROQ_MODEL,
                prompt_version="1",
            )
            self._session.add(stored)
            await self._session.flush()
        except Exception:
            pass  # ignore if table not present or different schema

        return plan
