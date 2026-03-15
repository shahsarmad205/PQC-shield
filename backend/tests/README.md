# Running tests

## What you need installed

1. **Python 3.12+** (or 3.11+).

2. **Backend dependencies** (from repo root):
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
   This installs pytest, pytest-asyncio, and the app dependencies.

3. **Optional: liboqs-python and liboqs shared library**  
   The PQC tests (KEM and sign/verify round-trips) need `liboqs-python` **and** a working **shared** liboqs (`liboqs.dylib` on macOS, `liboqs.so` on Linux).  
   - Pip: `pip install liboqs-python` (or use `requirements.txt`).  
   - **macOS / Homebrew:** Homebrew’s `brew install liboqs` only provides a **static** library (`liboqs.a`). The Python bindings need a **shared** library. Either:
     - **Option A:** Build liboqs with shared libs and set the install path. You need **CMake** and a C compiler (e.g. Xcode CLI or `brew install cmake` on macOS):
       ```bash
       cd backend
       bash scripts/build_liboqs_shared.sh
       export OQS_INSTALL_PATH="$PWD/local"   # when in backend; script prints the path
       pytest -v
       ```
       (Run with `bash` so you don’t need `chmod +x`. From repo root, build then use `export OQS_INSTALL_PATH="$PWD/backend/local"` before pytest.)
     - **Option B:** If you have a directory that already contains `lib/liboqs.dylib`, set:
       ```bash
       export OQS_INSTALL_PATH=/path/to/that/dir
       ```
   - Without a loadable liboqs: PQC round-trip tests are **skipped**; the algorithm-set tests still run.

You do **not** need a running database, Redis, or API keys to run the current tests (audit write is mocked).

---

## How to run tests

From the **backend** directory:

```bash
cd backend
pytest
```

Or with more output:

```bash
pytest -v
```

Run only the PQC service tests:

```bash
pytest tests/test_pqc_service.py -v
```

Run a single test by name:

```bash
pytest tests/test_pqc_service.py::test_kem_algorithms_defined -v
```

---

## Testing the database scaffold

You do **not** need a database to run the current test suite (PQC and algorithm tests). To verify the **database layer** (after `app/core/database.py` is in place):

1. **Engine import (no DB required)**  
   Confirms the app sees `DATABASE_URL` and builds the async engine:
   ```bash
   cd backend
   python -c "from app.core.database import engine; print(engine)"
   ```
   You should see: `Engine(...)`.

2. **Connectivity (DB required)**  
   Start PostgreSQL (e.g. `brew services start postgresql@14` or `pg_ctl start`). Create the DB and user from `.env` if needed (e.g. `createdb pqcshield`, and user `pqc` with password `localdev`). Then:
   ```bash
   cd backend
   export $(grep -v '^#' .env | xargs)   # load .env
   python scripts/check_db.py
   ```
   Expected: `OK: database connection succeeded (SELECT 1 => 1)`.

3. **Full test suite**  
   Ensures the new core module didn’t break anything (still no DB needed for current tests):
   ```bash
   pytest -v
   ```

4. **Migrations (Alembic)**  
   If the `alembic` command is not found, run it via Python from the backend directory:
   ```bash
   cd backend
   python scripts/run_alembic.py revision --autogenerate -m "cbom_initial"
   python scripts/run_alembic.py upgrade head
   ```
   Or after `pip install -r requirements.txt`, try `alembic revision --autogenerate -m "cbom_initial"` and `alembic upgrade head` if `alembic` is on your PATH.

---

## Authentication and API verification

The CBOM API is protected by JWT auth. All `/api/v1/cbom/*` endpoints require a Bearer token; `org_id` is taken from the token (users only see their own organization).

1. **Register** (creates Organization + User, returns JWT):
   ```bash
   curl -s -X POST http://localhost:8000/api/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{
       "email": "admin@acmedefense.gov",
       "password": "SecurePass123!",
       "full_name": "System Admin",
       "organization_name": "Acme Defense Corp"
     }' | python3 -m json.tool
   ```
   Copy the `access_token` from the response.

2. **Me** (current user + organization):
   ```bash
   curl -s http://localhost:8000/api/v1/auth/me \
     -H "Authorization: Bearer <token>" | python3 -m json.tool
   ```

3. **Protected CBOM endpoint** (e.g. threat-clock; org from token):
   ```bash
   curl -s "http://localhost:8000/api/v1/cbom/threat-clock" \
     -H "Authorization: Bearer <token>" | python3 -m json.tool
   ```

**Login** (existing user, form body; use single quotes so `!` in password is safe):
```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -d 'username=admin@acmedefense.gov&password=SecurePass123!' | python3 -m json.tool
```
(OAuth2 form uses `username` for email.)

**Copy-paste tip:** Put the token in a variable so the header is never broken by line wraps. Run from the **backend** directory (or set BASE_URL):

```bash
cd backend
TOKEN="paste_your_access_token_here"

# Finish a run (replace RUN_ID with the actual run UUID)
curl -s -X POST "http://localhost:8000/api/v1/cbom/runs/RUN_ID/finish" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Summary
curl -s "http://localhost:8000/api/v1/cbom/summary" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Threat clock
curl -s "http://localhost:8000/api/v1/cbom/threat-clock" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

- Use **one** backslash at the end of a line to continue the command; there must be no space after the backslash.
- Do **not** put `echo` or extra words after `json.tool` — that would be passed as a filename and cause errors.
- If you get `"detail": "Not authenticated"`, the token was not sent: check that `Authorization: Bearer $TOKEN` is correct and the token is in `$TOKEN`.

---

## What runs

- **With liboqs-python:** KEM round-trips (ML-KEM-512/768/1024), sign/verify (ML-DSA-65, SPHINCS+-SHA2-128f-simple), tampered-message check, and algorithm-set tests.
- **Without liboqs-python:** Only the two algorithm-set tests; the rest are skipped.
