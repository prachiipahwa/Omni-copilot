import pytest
from app.core.security import generate_csrf_token

@pytest.mark.asyncio
async def test_csrf_cookie_is_set(async_client):
    response = await async_client.get("/api/v1/csrf-token")
    assert response.status_code == 200
    
    json_data = response.json()
    assert "csrf_token" in json_data
    
    cookie_header = response.headers.get("set-cookie")
    assert cookie_header is not None
    assert "HttpOnly" in cookie_header
    assert "csrf_token=" in cookie_header

def test_csrf_token_generator_strength():
    token1 = generate_csrf_token()
    token2 = generate_csrf_token()
    # 32 bytes urlsafe is 43 chars usually
    assert len(token1) > 30
    assert token1 != token2
