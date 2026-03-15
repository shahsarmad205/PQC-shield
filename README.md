# PQC Shield

B2B SaaS that exposes **NIST-standardized post-quantum cryptography** (ML-KEM, ML-DSA, SLH-DSA via liboqs) as a REST API, for enterprise and government security teams.

## Stack

- **Backend:** FastAPI, async SQLAlchemy (asyncpg), Alembic, JWT + API key auth, Stripe billing
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui, React Query

## Getting started

### Backend

1. From repo root:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` (or create `.env`) and set at least:
   - `DATABASE_URL` — e.g. `postgresql+asyncpg://user:pass@localhost:5432/pqcshield`
   - `SECRET_KEY` — for JWT signing

3. Create the database and run migrations:
   ```bash
   createdb pqcshield   # or your DB name
   python -m alembic upgrade head
   ```

4. Run the API:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

API: `http://127.0.0.1:8000`  
Docs: `http://127.0.0.1:8000/docs`

### Frontend

1. From repo root:
   ```bash
   cd frontend
   npm install
   ```

2. Set `VITE_API_BASE_URL` (optional; defaults to same origin). For local dev with backend on 8000:
   ```bash
   export VITE_API_BASE_URL=http://127.0.0.1:8000
   npm run dev
   ```

3. Open `http://localhost:5173`. Register or log in to use the dashboard.

## Features

- **Dashboard** — KEM encrypt (keygen/encapsulate) and DSA sign panels; usage stats
- **API Keys** — Create/list/deactivate API keys; one-time display of secret with copy
- **Billing** — Plan and usage (Starter/Pro/Enterprise); Stripe Checkout and Customer Portal
- **Audit** — Paginated audit log with date range and operation filter; Export CSV; TanStack Table
- **CBOM** — Cryptographic Bill of Materials: summary cards, Quantum Threat Clock, asset inventory table, AI migration planner; Run Discovery Scan with sample payloads (RSA cert, ECDH API, ML-KEM API)
- **Compliance** — Algorithm reference table and PDF report export

## API overview

- `POST /api/v1/auth/register` — Create org + user
- `POST /api/v1/auth/login` — JWT
- `GET /api/v1/auth/me` — Current user + org
- `GET|POST|DELETE /api/v1/keys` — API key list, create, deactivate
- `GET /api/v1/billing` — Plan and usage
- `POST /api/v1/billing/create-checkout-session` — Stripe Checkout
- `POST /api/v1/billing/create-portal-session` — Stripe Customer Portal
- `GET /api/v1/audit` — Paginated audit log
- `GET /api/v1/audit/export` — CSV export
- `GET /api/v1/cbom/summary` — CBOM summary counts
- `GET /api/v1/cbom/threat-clock` — Quantum Threat Clock
- `GET /api/v1/cbom/assets` — Asset inventory
- `POST /api/v1/cbom/runs` — Start discovery run
- `POST /api/v1/cbom/runs/{id}/ingest` — Ingest payloads
- `POST /api/v1/cbom/runs/{id}/finish` — Finish run
- `POST /api/v1/cbom/migration-plan` — AI migration plan
- `GET /api/v1/crypto/*` — KEM/DSA crypto endpoints

All authenticated endpoints accept either `Authorization: Bearer <JWT>` or `X-API-Key: <key>` (where key is the full `pqcs_...` secret).

## Testing

See [backend/tests/README.md](backend/tests/README.md) for running pytest, PQC tests, and database connectivity.

## License

Proprietary.
