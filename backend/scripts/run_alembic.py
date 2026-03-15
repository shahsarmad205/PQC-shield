#!/usr/bin/env python3
"""Run Alembic using the same Python that has alembic installed. Use when 'alembic' is not on PATH."""
import sys
from pathlib import Path

# Backend root on path (for app imports when alembic runs)
_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

# Change to backend so alembic.ini and alembic/ are found
import os
os.chdir(_backend)

from alembic.config import main as alembic_main

if __name__ == "__main__":
    sys.exit(alembic_main(argv=sys.argv[1:]))
