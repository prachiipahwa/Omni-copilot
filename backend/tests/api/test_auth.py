import pytest
from app.db.session import SessionLocal
from app.models.user import User

@pytest.mark.asyncio
async def test_auth_me_unauthorized(async_client):
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"

@pytest.mark.asyncio
async def test_logout_behavior(async_client):
    # Call logout without being authenticated (should still succeed and clear cookie)
    response = await async_client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    
    set_cookie = response.headers.get("set-cookie", "")
    # Check that it wipes access_token
    assert 'access_token=";' in set_cookie or "access_token=;" in set_cookie
    assert "Max-Age=0" in set_cookie or "expires=" in set_cookie.lower()

@pytest.mark.asyncio
async def test_oauth_callback_failure_paths(async_client):
    # Test missing payload
    response = await async_client.get("/api/v1/auth/callback/google")
    assert response.status_code == 400
    assert "Missing code or state" in response.json()["detail"]

    # Test error returned from google
    response = await async_client.get("/api/v1/auth/callback/google?error=access_denied")
    assert response.status_code == 400
    assert "OAuth failed" in response.json()["detail"]

    # Test valid payload but invalid state token (protects against CSRF)
    client_cookies = {"oauth_state": "legit_state_123"}
    async_client.cookies.update(client_cookies)
    response = await async_client.get("/api/v1/auth/callback/google?code=fakecode&state=hacker_state")
    assert response.status_code == 400
    assert "Invalid state token" in response.json()["detail"]
