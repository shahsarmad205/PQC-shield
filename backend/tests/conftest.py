"""Pytest config and fixtures. Mock audit log write for tests that trigger it."""
import pytest
from unittest.mock import AsyncMock, patch


def pytest_configure(config):
    config.addinivalue_line("markers", "asyncio: mark test as async (pytest-asyncio)")


@pytest.fixture
def mock_audit_log_write():
    """Mock MeteringService.write_audit so tests don't hit the DB."""
    with patch(
        "app.services.metering_service.MeteringService.write_audit",
        new_callable=AsyncMock,
    ):
        yield


@pytest.fixture
def pqc_service():
    """PQCService instance; skips if liboqs-python not available."""
    from app.services.pqc_service import PQCService, oqs
    if oqs is None:
        pytest.skip("liboqs not available (install liboqs-python and ensure native lib loads)")
    return PQCService()
