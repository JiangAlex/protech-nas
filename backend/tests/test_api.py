"""General API tests for ProTech NAS Backend."""

import pytest


class TestLoginEndpoint:
    """Test cases for login endpoint response format."""

    @pytest.mark.asyncio
    async def test_login_success_response_format(self, async_client):
        """Test successful login response has correct format."""
        response = await async_client.post(
            "/api/auth/login",
            data={"username": "testadmin", "password": "testpassword123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_failure_response_format(self, async_client):
        """Test login failure response has detail field."""
        response = await async_client.post(
            "/api/auth/login",
            data={"username": "wrong", "password": "wrong"}
        )
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)

    @pytest.mark.asyncio
    async def test_login_response_content_type(self, async_client):
        """Test login response returns JSON content type."""
        response = await async_client.post(
            "/api/auth/login",
            data={"username": "testadmin", "password": "testpassword123"}
        )
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")


class TestTokenVerificationEndpoint:
    """Test /api/auth/me endpoint for token verification."""

    @pytest.mark.asyncio
    async def test_get_me_with_valid_token(self, async_client, auth_headers):
        """Test /api/auth/me with valid token returns user info."""
        response = await async_client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testadmin"

    @pytest.mark.asyncio
    async def test_get_me_without_token(self, async_client):
        """Test /api/auth/me without token returns 401."""
        response = await async_client.get("/api/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_with_invalid_token(self, async_client):
        """Test /api/auth/me with invalid token returns 401."""
        headers = {"Authorization": "Bearer invalid.token.here"}
        response = await async_client.get("/api/auth/me", headers=headers)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_response_format(self, async_client, auth_headers):
        """Test /api/auth/me response has correct format."""
        response = await async_client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "username" in data


class TestAuthenticationFlow:
    """Test complete authentication flow."""

    @pytest.mark.asyncio
    async def test_full_auth_flow(self, async_client):
        """Test complete login -> token use -> access protected resource flow."""
        # Step 1: Login
        login_response = await async_client.post(
            "/api/auth/login",
            data={"username": "testadmin", "password": "testpassword123"}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Step 2: Use token to access protected endpoint
        headers = {"Authorization": f"Bearer {token}"}
        me_response = await async_client.get("/api/auth/me", headers=headers)
        assert me_response.status_code == 200
        assert me_response.json()["username"] == "testadmin"

    @pytest.mark.asyncio
    async def test_token_reuse(self, async_client, auth_headers):
        """Test that the same token can be used multiple times."""
        # Use token first time
        response1 = await async_client.get("/api/auth/me", headers=auth_headers)
        assert response1.status_code == 200
        
        # Use token again
        response2 = await async_client.get("/api/auth/me", headers=auth_headers)
        assert response2.status_code == 200
        
        # Both responses should be identical
        assert response1.json() == response2.json()


class TestHTTPMethods:
    """Test HTTP method handling on endpoints."""

    @pytest.mark.asyncio
    async def test_get_on_login_returns_method_not_allowed(self, async_client):
        """Test that GET on login endpoint returns 405."""
        response = await async_client.get("/api/auth/login")
        # FastAPI returns 405 for wrong HTTP method
        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_post_on_get_me_returns_method_not_allowed(self, async_client):
        """Test that POST on /api/auth/me returns 405."""
        response = await async_client.post("/api/auth/me")
        assert response.status_code == 405


class TestErrorResponses:
    """Test error response format consistency."""

    @pytest.mark.asyncio
    async def test_401_error_has_detail(self, async_client):
        """Test that 401 errors include detail field."""
        response = await async_client.get("/api/auth/me")
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_invalid_token_error_message(self, async_client):
        """Test that invalid token returns appropriate error message."""
        headers = {"Authorization": "Bearer invalid.token"}
        response = await async_client.get("/api/auth/me", headers=headers)
        assert response.status_code == 401
        assert "detail" in response.json()


class TestEndpointExistence:
    """Test that expected endpoints are accessible."""

    @pytest.mark.asyncio
    async def test_login_endpoint_exists(self, async_client):
        """Test that login endpoint is registered."""
        response = await async_client.post(
            "/api/auth/login",
            data={"username": "testadmin", "password": "testpassword123"}
        )
        # Should not return 404
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_me_endpoint_exists(self, async_client):
        """Test that /api/auth/me endpoint is registered."""
        response = await async_client.get("/api/auth/me")
        # Should not return 404 (even if 401)
        assert response.status_code != 404
