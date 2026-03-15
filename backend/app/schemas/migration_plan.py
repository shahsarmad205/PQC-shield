"""MigrationPlan schema — AI-generated phased roadmap (Pydantic)."""
from pydantic import BaseModel, Field


class MigrationPhase(BaseModel):
    phase_number: int = Field(..., ge=1, description="1-based phase index")
    title: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    asset_ids: list[str] = Field(default_factory=list, description="IDs of assets in this phase")
    estimated_effort_days: int = Field(..., ge=0, description="Estimated effort in days")
    compliance_impact: list[str] = Field(
        default_factory=list,
        description="NIST/other control IDs or names this phase addresses",
    )


class MigrationPlan(BaseModel):
    summary: str = Field(..., min_length=1)
    phases: list[MigrationPhase] = Field(..., min_length=0, max_length=5)
    generated_at: str | None = Field(None, description="ISO timestamp when generated")
    executive_summary: str | None = Field(None, description="2-3 sentence summary for leadership")
    quick_wins: list[str] = Field(default_factory=list, description="Immediate high-impact actions")
    recommended_algorithms: list[str] = Field(
        default_factory=list,
        description="PQC algorithms to adopt e.g. ML-KEM-768, ML-DSA-65",
    )
