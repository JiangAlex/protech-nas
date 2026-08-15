"""Authentication tests for ProTech NAS API."""

import pytest
from datetime import datetime, timedelta, timezone
from jose import jwt


class TestLoginEndpoint:
    """Test cases for /api/auth/login endpoint."""

    @pytest.mark.asyncio
    async def test_login_success(self, async_client):
        """Test successful login with valid credentials."""
        response = await async_client.post(
            "/api/auth/login",
            data={"username": "testadmin", "password": "testpassword123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0

    @pytest.mark.asyncio
    async def test_login_invalid_username(self, async_client):
        """Test login failure with invalid username."""
        response = await async_client.post(
            "/api/auth/login",
            data={"username": "wronguser", "password": "testpassword123"}
        )
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_invalid_password(self, async_client):
        """Test login failure with invalid password."""
        response = await async_client.post(
            "/api/auth/login",
            data={"username": "testadmin", "password": "wrongpassword"}
        )
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_empty_credentials(self, async_client):
        """Test login with empty credentials returns authentication error."""
        response = await async_client.post(
            "/api/auth/login",
            data={"username": "", "password": ""}
        )
        # Empty password is treated as invalid credentials -> 401 Unauthorized
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_missing_password(self, async_client):
        """Test login failure with missing password field."""
        response = await async_client.post(
            "/api/auth/login",
            data={"username": "testadmin"}
        )
        assert response.status_code == 422  # Validation error


class TestJWTToken:
    """Test cases for JWT token generation and validation."""

    @pytest.mark.asyncio
    async def test_token_contains_required_claims(self, async_client):
        """Test that token contains necessary JWT claims."""
        response = await async_client.post(
            "/api/auth/login",
            data={"username": "testadmin", "password": "testpassword123"}
        )
        token = response.json()["access_token"]
        
        # Decode without verification to inspect claims
        from src.config import settings
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        assert "sub" in payload  # subject (username)
        assert payload["sub"] == "testadmin"
        assert "exp" in payload  # expiration time

    @pytest.mark.asyncio
    async def test_token_expiration(self, async_client):
        """Test that token has correct expiration time."""
        from src.config import settings
        
        response = await async_client.post(
            "/api/auth/login",
            data={"username": "testadmin", "password": "testpassword123"}
        )
        token = response.json()["access_token"]
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        
        # Token should expire in approximately JWT_EXPIRE_MINUTES (60 min)
        delta = exp_time - now
        assert 59 <= delta.total_seconds() / 60 <= 61

    @pytest.mark.asyncio
    async def test_token_is_valid_jwt(self, async_client):
        """Test that returned token is a valid JWT format."""
        response = await async_client.post(
            "/api/auth/login",
            data={"username": "testadmin", "password": "testpassword123"}
        )
        token = response.json()["access_token"]
        
        # JWT should have 3 parts separated by dots
        parts = token.split(".")
        assert len(parts) == 3


class TestTokenVerification:
    """Test cases for token verification via /api/auth/me endpoint."""

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
    async def test_get_me_with_malformed_authorization_header(self, async_client):
        """Test /api/auth/me with malformed auth header returns 401."""
        headers = {"Authorization": "NotBearer some-token"}
        response = await async_client.get("/api/auth/me", headers=headers)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_with_expired_token_format(self, async_client):
        """Test /api/auth/me with structurally valid but non-functional token."""
        # Create a token with wrong secret
        from src.config import settings
        expired_token = jwt.encode(
            {"sub": "testadmin", "exp": datetime.now(timezone.utc) - timedelta(hours=1)},
            "wrong-secret",
            algorithm=settings.JWT_ALGORITHM
        )
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = await async_client.get("/api/auth/me", headers=headers)
        assert response.status_code == 401


class TestProtectedEndpoints:
    """Test authorization checks on auth-protected endpoints."""

    @pytest.mark.asyncio
    async def test_auth_me_endpoint_requires_auth(self, async_client):
        """Test that /api/auth/me requires authentication."""
        response = await async_client.get("/api/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_auth_me_endpoint_with_valid_token(self, async_client, auth_headers):
        """Test that /api/auth/me works with valid token."""
        response = await async_client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_login_endpoint_public(self, async_client):
        """Test that /api/auth/login is publicly accessible."""
        response = await async_client.post(
            "/api/auth/login",
            data={"username": "testadmin", "password": "testpassword123"}
        )
        assert response.status_code == 200
