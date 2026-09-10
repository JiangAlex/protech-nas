"""Tests for the unauthenticated dashboard metrics endpoint (phase 1, no token)."""

import pytest


@pytest.mark.asyncio
async def test_public_metrics_no_auth(anon_client):
    """GET /api/dashboard/metrics must be accessible WITHOUT auth and return system info."""
    resp = await anon_client.get("/api/dashboard/metrics")
    assert resp.status_code == 200
    data = resp.json()
    # System overview keys produced by get_system_info()
    assert "cpu" in data
    assert "memory" in data
    assert "disk" in data
    assert "percent" in data["cpu"]
    assert "percent" in data["memory"]
    assert "percent" in data["disk"]


@pytest.mark.asyncio
async def test_authenticated_dashboard_still_requires_auth(anon_client):
    """The original GET /api/dashboard must still require auth (regression guard)."""
    resp = await anon_client.get("/api/dashboard")
    assert resp.status_code == 401
