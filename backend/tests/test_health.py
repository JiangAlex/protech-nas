"""Tests for health and auth endpoints."""

import pytest


@pytest.mark.asyncio
async def test_health(anon_client):
    """Health endpoint should be accessible without auth."""
    resp = await anon_client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_root(anon_client):
    """Root endpoint returns service info."""
    resp = await anon_client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "protech-nas"
    assert "version" in data


@pytest.mark.asyncio
async def test_login_success(anon_client):
    """Valid credentials return JWT token."""
    resp = await anon_client.post("/api/auth/login", data={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_fail(anon_client):
    """Invalid credentials return 401."""
    resp = await anon_client.post("/api/auth/login", data={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_auth(anon_client):
    """Protected endpoint requires auth."""
    resp = await anon_client.get("/api/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_with_auth(client):
    """Auth/me returns current user with valid token."""
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "admin"
