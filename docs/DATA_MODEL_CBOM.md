# CBOM Data Model — Design

This document defines the data model for the **Cryptographic Bill of Materials (CBOM)**. It represents every cryptographic asset discovered across an organization’s infrastructure and tracks vulnerability status, migration priority, and remediation history.

---

## Design principles

1. **Asset-centric** — We model *assets* (a certificate, an API endpoint, a code location, etc.) and attach *crypto findings* (algorithms in use) to them. Remediation is tracked per asset so “replaced this cert” updates one place.
2. **Living CBOM** — Discovery runs produce a stream of findings. We link assets to the last run that saw them and support “stale” or “removed” so the CBOM reflects current state while preserving history.
3. **Multi-tenant and scoped** — Organizations can have multiple scopes (environments, apps, regions). Assets and runs are scoped so reporting and priority can be per-scope or org-wide.
4. **Type-safe asset attributes** — Each asset type has a clear set of attributes (cert fields, API path, file:line, etc.) so scanners and UI can rely on a consistent shape.

---

## Entity relationship overview

```
Organization
    │
    ├── Scope (optional: env, app, region)
    │
    ├── DiscoveryRun (each scan)
    │       │
    │       └── discovers/updates ──► Asset (one per logical “thing”)
    │                                     │
    │                                     ├── CryptoFinding (1..n per asset: algorithm + usage)
    │                                     │
    │                                     └── RemediationEvent (0..n: history of fixes)
    │
    └── (Migration plans and Compliance reports reference CBOM by querying Assets/Findings)
```

- **Organization** — Tenant (enterprise or government org).
- **Scope** — Optional subdivision: environment (prod/staging), application, or region. Assets and runs belong to an org and optionally to a scope.
- **DiscoveryRun** — One scan or discovery job. Used to know “when we last saw this asset” and to attach run-level metadata (scanner version, errors).
- **Asset** — One logical cryptographic “thing”: a certificate, an API endpoint, a code location, a database config, or a network protocol endpoint. Type-specific attributes live in `asset_type` + `attributes` (or typed columns).
- **CryptoFinding** — One row = “this asset uses this algorithm for this purpose.” An asset can have multiple findings (e.g. TLS endpoint: RSA-2048 KEX + AES-256-GCM encryption).
- **RemediationEvent** — One record = one remediation action on an asset (or optionally on a finding). Tracks status (planned / in progress / completed / deferred) and before/after state.

---

## Core entities

### 1. Organization

| Field           | Type     | Description |
|-----------------|----------|-------------|
| `id`            | UUID     | PK. |
| `name`          | string   | Display name. |
| `created_at`    | timestamp| |
| `updated_at`    | timestamp| |
| `settings`      | JSON     | Optional: defaults for priority rules, retention, etc. |

---

### 2. Scope (optional)

| Field           | Type     | Description |
|-----------------|----------|-------------|
| `id`            | UUID     | PK. |
| `organization_id` | UUID   | FK → Organization. |
| `name`          | string   | e.g. "Production", "US-East", "Payment Service". |
| `scope_type`    | enum     | `environment` \| `application` \| `region` \| `custom`. |
| `created_at`    | timestamp| |
| `updated_at`    | timestamp| |

Use this to filter “prod only” or “this app only” for dashboards and migration plans.

---

### 3. DiscoveryRun

| Field           | Type     | Description |
|-----------------|----------|-------------|
| `id`            | UUID     | PK. |
| `organization_id` | UUID   | FK → Organization. |
| `scope_id`      | UUID?    | FK → Scope; null = org-wide. |
| `started_at`    | timestamp| |
| `finished_at`   | timestamp?| Null if still running. |
| `status`        | enum     | `running` \| `completed` \| `failed` \| `partial`. |
| `source`        | string   | Scanner or source: e.g. `network_scanner`, `cert_scanner`, `api_scanner`, `code_scanner`, `manual`. |
| `summary`       | JSON     | Optional: counts by asset_type, by quantum_status, error summary. |
| `created_at`    | timestamp| |

Enables “last scan at” and “which run last saw this asset.”

---

### 4. Asset

The central entity: one row per discovered cryptographic *thing*.

| Field               | Type     | Description |
|---------------------|----------|-------------|
| `id`                | UUID     | PK. |
| `organization_id`   | UUID     | FK → Organization. |
| `scope_id`          | UUID?    | FK → Scope; null = org-wide. |
| `asset_type`        | enum     | `certificate` \| `api_endpoint` \| `source_code` \| `database` \| `network_protocol`. |
| `source_identifier` | string   | **Deterministic id from the world** (cert thumbprint, host+path, file:line, etc.). Used for deduplication. |
| `display_name`      | string?  | Human-readable label (e.g. "api.example.com", "LoginService.cs"). |
| `attributes`        | JSON     | Type-specific attributes (see below). |
| `first_seen_run_id` | UUID?    | FK → DiscoveryRun. |
| `last_seen_run_id`  | UUID?    | FK → DiscoveryRun. |
| `last_seen_at`      | timestamp?| When this asset was last observed. |
| `lifecycle`         | enum     | `active` \| `stale` \| `removed`. `stale` = not seen in last run; `removed` = explicitly or implicitly retired. |
| `migration_priority`| enum?    | `critical` \| `high` \| `medium` \| `low` \| `none`. Computed or manual. |
| `priority_score`    | int?     | Optional 0–100 for ordering. |
| `priority_rationale`| string?  | Why this priority (e.g. "Public-facing TLS", "Handles PII"). |
| `created_at`        | timestamp| |
| `updated_at`        | timestamp| |

**Unique constraint:** `(organization_id, scope_id, asset_type, source_identifier)` so the same logical asset is not duplicated when scans repeat.

**Asset type–specific attributes (in `attributes` JSON):**

| asset_type        | Suggested attributes (key names) |
|-------------------|-----------------------------------|
| `certificate`     | `subject`, `issuer`, `serial`, `thumbprint`, `not_before`, `not_after`, `key_algorithm`, `key_size_or_oid`, `store_location`, `chain_position` |
| `api_endpoint`    | `host`, `base_url`, `method`, `path`, `tls_version`, `auth_scheme`, `protocol` (e.g. REST, gRPC) |
| `source_code`     | `repo`, `repo_url`, `branch`, `file_path`, `line_start`, `line_end`, `symbol_or_pattern`, `language`, `context_snippet` |
| `database`        | `engine`, `instance_id`, `database_name`, `encryption_scope` (e.g. TDE, column, connection), `connection_protocol` |
| `network_protocol`| `protocol` (e.g. SSH, IPsec, TLS), `role` (client/server), `host_or_endpoint`, `port` |

You can later add typed columns or a separate table per asset type if query performance or schema clarity demands it; starting with JSON keeps the model flexible as scanners evolve.

---

### 5. CryptoFinding

One row = one algorithm (and usage) on one asset. An asset can have many findings (e.g. one TLS connection: key exchange + bulk cipher + signature).

| Field             | Type     | Description |
|-------------------|----------|-------------|
| `id`              | UUID     | PK. |
| `asset_id`        | UUID     | FK → Asset. |
| `algorithm`       | string   | e.g. `RSA-2048`, `ECDH-P256`, `AES-256-GCM`, `ML-KEM-768`, `ML-DSA-65`, `SHA-256`. |
| `usage`           | enum     | `key_exchange` \| `signing` \| `encryption` \| `hashing` \| `unknown`. |
| `quantum_status`  | enum     | `vulnerable` \| `hybrid` \| `quantum_safe`. |
| `key_created_at`  | timestamp?| When key/cert was created (if known). |
| `key_expires_at`  | timestamp?| Expiry (certs, key rotation). |
| `metadata`        | JSON     | Optional: cipher_suite name, OID, library version, etc. |
| `risk_score`      | int?     | Optional 0–100 for this finding. |
| `cve_refs`        | string[]?| Related CVEs if applicable. |
| `created_at`      | timestamp| |
| `updated_at`      | timestamp| |

**Vulnerability status** is represented by:
- `quantum_status` — whether the algorithm is quantum-vulnerable, hybrid, or PQC.
- Optional `risk_score` and `cve_refs` for classical vulnerabilities or misconfigurations.

You can add a separate `Vulnerability` table later (e.g. CVE + severity + affected finding) if you need a full vulnerability DB; for CBOM, `quantum_status` + optional refs on the finding is enough to drive dashboards and priority.

---

### 6. RemediationEvent

History of what was done (or planned) to fix an asset.

| Field           | Type     | Description |
|-----------------|----------|-------------|
| `id`            | UUID     | PK. |
| `asset_id`      | UUID     | FK → Asset. |
| `action`        | enum     | e.g. `cert_replaced` \| `tls_upgraded` \| `algorithm_rotated` \| `code_updated` \| `deferred` \| `false_positive`. |
| `status`        | enum     | `planned` \| `in_progress` \| `completed` \| `deferred` \| `cancelled`. |
| `performed_at`  | timestamp?| When the fix was applied (null if planned only). |
| `performed_by`  | string?  | User id or "scanner" / "system". |
| `notes`         | string?  | Free text. |
| `before_state`  | JSON?    | Snapshot of asset/findings before (e.g. algorithm list). |
| `after_state`   | JSON?    | Snapshot after (for audit). |
| `created_at`    | timestamp| |

Linking to `asset_id` (not finding_id) keeps remediation simple: “we fixed this cert” closes all findings on that cert. If you need finding-level remediation (e.g. “we only upgraded KEX, not the signature”), you can add optional `finding_id` later.

---

## Derived / computed concepts

- **Vulnerability status (asset-level)** — E.g. “vulnerable” if any finding on that asset has `quantum_status = vulnerable`; “hybrid” if mix; “quantum_safe” if all PQC. Can be stored on Asset as `aggregate_quantum_status` and refreshed on finding change, or computed in queries.
- **Migration priority** — Stored on Asset (`migration_priority`, `priority_score`, `priority_rationale`). Can be computed from: exposure (public vs internal), data classification, algorithm strength, key expiry, and compliance scope. Recompute after each scan or when running the migration planner.
- **Remediation history** — Query `RemediationEvent` by `asset_id` ordered by `created_at` (or `performed_at`). “Remediation status” for an asset can be: latest event’s `status`, or “not started” if no events.

---

## Indexing and query patterns

- **Dashboard / CBOM list:** Filter by `organization_id`, optional `scope_id`, `lifecycle = active`, optional `asset_type`, `migration_priority`. Order by `priority_score` desc, `last_seen_at` desc.
- **Drill into asset:** By `asset_id` load Asset + all CryptoFindings + latest RemediationEvents.
- **Compliance / reports:** Aggregate by `quantum_status`, `asset_type`, and scope; join to framework control mappings (separate compliance model).
- **Migration planner:** Query high-priority assets and their findings; pass to AI or rules engine.
- **Deduplication on ingest:** Upsert Asset by `(organization_id, scope_id, asset_type, source_identifier)`; insert/update CryptoFindings for that asset; set `last_seen_run_id`, `last_seen_at`, `lifecycle = active`. Mark assets not seen in this run as `stale` (or `removed` after N runs).

---

## Summary

| Entity            | Purpose |
|-------------------|--------|
| **Organization**  | Tenant. |
| **Scope**         | Optional env/app/region. |
| **DiscoveryRun**  | One scan; supports “living CBOM” and last-seen. |
| **Asset**         | One certificate, API, code location, DB, or network endpoint; type + attributes + priority. |
| **CryptoFinding** | One algorithm/usage on one asset; quantum status and key dates. |
| **RemediationEvent** | Per-asset remediation history and status. |

This model supports certificates, API endpoints, code signatures, database encryption, and network protocols; tracks vulnerability (quantum and optional CVE); stores migration priority and rationale on the asset; and keeps full remediation history per asset. When you’re ready to implement, this can be translated into SQL migrations (e.g. Alembic) and Pydantic schemas in the backend.
