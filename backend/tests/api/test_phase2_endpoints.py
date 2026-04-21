import pytest
from app.models.user import User
from app.db.session import SessionLocal

@pytest.mark.asyncio
async def test_integration_status_requires_auth(async_client):
    response = await async_client.get("/api/v1/integrations/status")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_create_chat_session_requires_auth(async_client):
    response = await async_client.post("/api/v1/chats/", json={"title": "Test Auth"})
    assert response.status_code == 401
