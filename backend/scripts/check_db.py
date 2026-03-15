#!/usr/bin/env python3
"""Quick database connectivity check. Run from backend/. Requires PostgreSQL and DATABASE_URL."""
import asyncio
import sys
from pathlib import Path

# Ensure backend root is on path when running as python scripts/check_db.py
_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from sqlalchemy import text

from app.core.database import engine


async def check():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        row = result.scalar()
    assert row == 1
    print("OK: database connection succeeded (SELECT 1 => 1)")


if __name__ == "__main__":
    try:
        asyncio.run(check())
    except OSError as e:
        if "5432" in str(e) or "Connect" in str(e) or "refused" in str(e).lower():
            print("Database connection failed: PostgreSQL is not running or not reachable on localhost:5432.")
            print("Start PostgreSQL (e.g. brew services start postgresql@14) and ensure the DB/user from .env exist.")
        else:
            raise
        sys.exit(1)
