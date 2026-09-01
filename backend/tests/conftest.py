"""Shared pytest fixtures for the NexusAI backend tests.

Ensures the backend package is importable and the database is seeded
with the canonical Ali Garments demo data before tests run.
"""

import os
import sys

# Make the backend package importable regardless of where pytest runs from
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# The app engine uses a relative SQLite path — anchor CWD to backend/
os.chdir(BACKEND_DIR)

import pytest

from app.config import settings
from app.database import SessionLocal
from app.models.business import Business


@pytest.fixture(scope="session", autouse=True)
def _ensure_seeded():
    """Seed the demo data once if the database is empty."""
    db = SessionLocal()
    try:
        if not db.query(Business).first():
            from seed import seed
            seed()
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def _hermetic_llm():
    """Keep the whole test session off the live Gemini API.

    A real key may exist in backend/.env — tests must never spend quota,
    depend on network latency, or flake on provider errors. Tests that
    exercise the client itself mock urlopen (see tests/test_llm.py).
    """
    original = settings.gemini_api_key
    settings.gemini_api_key = ""
    yield
    settings.gemini_api_key = original


@pytest.fixture()
def db():
    """Fresh session per test; rolled back is not needed (read-only tests)."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
