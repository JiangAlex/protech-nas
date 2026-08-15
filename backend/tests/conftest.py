"""Pytest fixtures and configuration for ProTech NAS tests."""

import os
import pytest
from unittest.mock import patch, MagicMock

# Set test environment variables before importing app
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["ADMIN_USER"] = "testadmin"
os.environ["ADMIN_PASSWORD"] = "testpassword123"
os.environ["JWT_EXPIRE_MINUTES"] = "60"
os.environ["LOG_LEVEL"] = "ERROR"
os.environ["LOG_FORMAT"] = "console"


@pytest.fixture
def mock_subprocess():
    """Mock subprocess calls for system commands."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="test", stderr="")
        yield mock_run


@pytest.fixture
def app():
    """Create minimal test application with only auth router."""
    from fastapi import FastAPI
    from src.auth import router as auth_router
    
    test_app = FastAPI(title="ProTech NAS Test")
    test_app.include_router(auth_router)
    
    return test_app


@pytest.fixture
async def async_client(app):
    """Create async client for async tests."""
    from httpx import AsyncClient, ASGITransport
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_token(async_client):
    """Get authentication token by logging in with test credentials."""
    response = await async_client.post(
        "/api/auth/login",
        data={"username": "testadmin", "password": "testpassword123"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
async def auth_headers(auth_token):
    """Get authorization headers with bearer token."""
    return {"Authorization": f"Bearer {auth_token}"}
