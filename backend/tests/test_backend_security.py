"""
Security-specific integration tests for Omni Copilot.
Focuses on CSRF Double-Submit validation.
"""
from __future__ import annotations
import pytest
import uuid
from httpx import AsyncClient
from app.core.security import create_access_token, generate_csrf_token

@pytest.mark.asyncio
async def test_csrf_initialization(async_client: AsyncClient):
    """Verify that calling /csrf sets a non-HttpOnly cookie."""
    response = await async_client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    
    cookies = response.cookies
    assert "csrf_token" in cookies
    sc = response.headers.get("set-cookie", "")
    assert "csrf_token=" in sc
    assert "HttpOnly" not in sc

@pytest.mark.asyncio
async def test_csrf_protection_missing_header(async_client: AsyncClient):
    """Mutating request with no CSRF header must fail with 403."""
    user_id = uuid.uuid4()
    token = create_access_token(subject=str(user_id))
    async_client.cookies.set("access_token", f"Bearer {token}")
    async_client.cookies.set("csrf_token", "legit-token")
    
    response = await async_client.post(
        "/api/v1/chat/send",
        json={"message": "hello"}
    )
    assert response.status_code == 403
    assert "Missing CSRF header" in response.json()["detail"]

@pytest.mark.asyncio
async def test_csrf_protection_mismatch(async_client: AsyncClient):
    """Mutating request with mismatched header/cookie must fail with 403."""
    user_id = uuid.uuid4()
    token = create_access_token(subject=str(user_id))
    async_client.cookies.set("access_token", f"Bearer {token}")
    async_client.cookies.set("csrf_token", "cookie-token")
    
    response = await async_client.post(
        "/api/v1/chat/send",
        json={"message": "hello"},
        headers={"X-CSRF-Token": "hacker-token"}
    )
    assert response.status_code == 403
    assert "token mismatch" in response.json()["detail"]

@pytest.mark.asyncio
async def test_csrf_protection_success_format(async_client: AsyncClient):
    """
    Mutating request with matching header/cookie passes CSRF check.
    It will fail with 404 if the user doesn't exist in DB, 
    but it must NOT fail with 403.
    """
    user_id = uuid.uuid4()
    token = create_access_token(subject=str(user_id))
    csrf = "matching-token"
    async_client.cookies.set("access_token", f"Bearer {token}")
    async_client.cookies.set("csrf_token", csrf)
    
    response = await async_client.post(
        "/api/v1/chat/send",
        json={"message": "hello"},
        headers={"X-CSRF-Token": csrf}
    )
    # Passed CSRF check, reached user resolution (which fails with 404 because user is mock)
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"
