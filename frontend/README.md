# PQC Shield — Frontend

React + TypeScript + Vite app for the PQC Shield dashboard. Uses Tailwind CSS, shadcn/ui, and React Query.

## Setup

```bash
npm install
```

Optional: set the API base URL (defaults to same origin):

```bash
export VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Develop

```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). Register or log in (backend must be running).

## Build

```bash
npm run build
```

Output in `dist/`. Preview with `npm run preview`.

## Main pages

- **Dashboard** — KEM encrypt, DSA sign, usage stats
- **Compliance** — Algorithm table, PDF report
- **API Keys** — List, create (one-time secret), deactivate
- **Billing** — Plan, usage, Stripe Checkout/Portal
- **Audit** — Audit log table, filters, Export CSV
- **CBOM** — Summary, Quantum Threat Clock, asset inventory, migration planner, Run Discovery Scan

All data fetching uses React Query. Auth is JWT stored in `localStorage`; protected routes redirect to `/login` when unauthenticated.
