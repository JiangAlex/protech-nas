"""Shared test fixtures for ProTech NAS backend tests."""

import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app


@pytest.fixture
async def client():
    """Async HTTP test client with auth token."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Login to get token
        resp = await ac.post("/api/auth/login", data={"username": "admin", "password": "admin123"})
        if resp.status_code == 200:
            token = resp.json().get("access_token", "")
            ac.headers["Authorization"] = f"Bearer {token}"
        yield ac


@pytest.fixture
async def anon_client():
    """Async HTTP test client without auth."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
