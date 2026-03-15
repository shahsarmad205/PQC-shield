"""Pydantic v2 schemas for CBOM entities: Base, Create, Read; attribute types; CBOMSummary."""
from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, computed_field
from pydantic import BaseModel, Field

# --- Enums (string literals for API/serialization) ---
ScopeType = str  # "environment" | "application" | "region" | "custom"
DiscoveryRunStatus = str  # "running" | "completed" | "failed" | "partial"
AssetType = str  # "certificate" | "api_endpoint" | "source_code" | "database" | "network_protocol"
Lifecycle = str  # "active" | "stale" | "removed"
MigrationPriority = str  # "critical" | "high" | "medium" | "low" | "none"
FindingUsage = str  # "key_exchange" | "signing" | "encryption" | "hashing" | "unknown"
QuantumStatus = str  # "vulnerable" | "hybrid" | "quantum_safe"
RemediationAction = str
RemediationStatus = str


# --- Asset attributes (map to JSON `attributes` column) ---

class AssetAttributesCertificate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="allow")
    subject: str | None = None
    issuer: str | None = None
    serial: str | None = None
    thumbprint: str | None = None
    not_before: str | None = None
    not_after: str | None = None
    key_algorithm: str | None = None
    key_size_or_oid: str | None = None
    store_location: str | None = None
    chain_position: str | None = None


class AssetAttributesApiEndpoint(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="allow")
    host: str | None = None
    base_url: str | None = None
    method: str | None = None
    path: str | None = None
    tls_version: str | None = None
    auth_scheme: str | None = None
    protocol: str | None = None


class AssetAttributesSourceCode(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="allow")
    repo: str | None = None
    repo_url: str | None = None
    branch: str | None = None
    file_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    symbol_or_pattern: str | None = None
    language: str | None = None
    context_snippet: str | None = None


class AssetAttributesDatabase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="allow")
    engine: str | None = None
    instance_id: str | None = None
    database_name: str | None = None
    encryption_scope: str | None = None
    connection_protocol: str | None = None


class AssetAttributesNetworkProtocol(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="allow")
    protocol: str | None = None
    role: str | None = None
    host_or_endpoint: str | None = None
    port: int | None = None


# --- Organization ---

class OrganizationBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str = Field(..., max_length=255)


class OrganizationCreate(OrganizationBase):
    settings: dict | None = None


class OrganizationRead(OrganizationBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    settings: dict | None = None


# --- Scope ---

class ScopeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    organization_id: UUID
    name: str = Field(..., max_length=255)
    scope_type: ScopeType


class ScopeCreate(ScopeBase):
    pass


class ScopeRead(ScopeBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


# --- DiscoveryRun ---

class DiscoveryRunBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    organization_id: UUID
    scope_id: UUID | None = None
    status: DiscoveryRunStatus
    source: str = Field(..., max_length=128)
    summary: dict | None = None


class DiscoveryRunCreate(DiscoveryRunBase):
    started_at: datetime | None = None
    finished_at: datetime | None = None


class DiscoveryRunRead(DiscoveryRunBase):
    id: UUID
    started_at: datetime
    finished_at: datetime | None = None
    created_at: datetime


# --- RemediationEvent (before CryptoFinding and Asset for nesting) ---

class RemediationEventBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    asset_id: UUID
    action: RemediationAction
    status: RemediationStatus
    performed_at: datetime | None = None
    performed_by: str | None = None
    notes: str | None = None
    before_state: dict | None = None
    after_state: dict | None = None


class RemediationEventCreate(RemediationEventBase):
    pass


class RemediationEventRead(RemediationEventBase):
    id: UUID
    created_at: datetime


# --- CryptoFinding (has computed quantum_risk_label) ---

class CryptoFindingBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    asset_id: UUID
    algorithm: str = Field(..., max_length=128)
    usage: FindingUsage
    quantum_status: QuantumStatus
    key_created_at: datetime | None = None
    key_expires_at: datetime | None = None
    finding_metadata: dict | None = None
    risk_score: int | None = None
    cve_refs: list[str] | None = None


class CryptoFindingCreate(CryptoFindingBase):
    pass


class CryptoFindingRead(CryptoFindingBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def quantum_risk_label(self) -> str:
        if self.quantum_status == "vulnerable":
            return "Harvest Now, Decrypt Later risk"
        if self.quantum_status == "hybrid":
            return "Transition in progress"
        return "Quantum safe"


# --- Asset (has nested findings, latest_remediation, computed aggregate_quantum_status) ---

def _worst_quantum_status(statuses: list[str]) -> str:
    """vulnerable beats hybrid beats quantum_safe."""
    if not statuses:
        return "quantum_safe"
    if "vulnerable" in statuses:
        return "vulnerable"
    if "hybrid" in statuses:
        return "hybrid"
    return "quantum_safe"


class AssetBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    organization_id: UUID
    scope_id: UUID | None = None
    asset_type: AssetType
    source_identifier: str = Field(..., max_length=1024)
    display_name: str | None = None
    attributes: dict = Field(default_factory=dict)
    lifecycle: Lifecycle
    migration_priority: MigrationPriority | None = None
    priority_score: int | None = None
    priority_rationale: str | None = None


class AssetCreate(AssetBase):
    first_seen_run_id: UUID | None = None
    last_seen_run_id: UUID | None = None
    last_seen_at: datetime | None = None


class AssetRead(AssetBase):
    id: UUID
    first_seen_run_id: UUID | None = None
    last_seen_run_id: UUID | None = None
    last_seen_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    findings: list[CryptoFindingRead] = Field(default_factory=list)
    latest_remediation: RemediationEventRead | None = None

    @computed_field
    @property
    def aggregate_quantum_status(self) -> str:
        return _worst_quantum_status([f.quantum_status for f in self.findings])


# --- CBOMSummary (org-level dashboard rollup) ---

class CBOMSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    total_assets: int = Field(..., ge=0)
    by_asset_type: dict[str, int] = Field(default_factory=dict)
    by_quantum_status: dict[str, int] = Field(default_factory=dict)
    by_migration_priority: dict[str, int] = Field(default_factory=dict)
    critical_count: int = Field(..., ge=0)
    last_scan_at: datetime | None = None
    stale_asset_count: int = Field(..., ge=0)


# --- IngestResult (batch_ingest response) ---

class IngestResultRead(BaseModel):
    assets_created: int = 0
    assets_updated: int = 0
    findings_created: int = 0
    findings_updated: int = 0
    errors: list[str] = Field(default_factory=list)


# --- Paginated assets list ---

class AssetListResponse(BaseModel):
    items: list["AssetRead"] = Field(default_factory=list)
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1)


# --- Asset detail (single asset with full remediation history) ---

class AssetDetailRead(AssetRead):
    """Asset with all remediation events (for GET /assets/{id})."""
    remediation_events: list[RemediationEventRead] = Field(default_factory=list)
