import pytest
from app.db.session import SessionLocal

@pytest.mark.asyncio
async def test_retrieval_endpoints_unauthenticated(async_client):
    res = await async_client.get("/api/v1/retrieval/google/drive")
    assert res.status_code == 401

@pytest.mark.asyncio
async def test_retrieval_missing_integration(async_client, setup_test_db):
    """
    Given a logged in user with NO integration row.
    When querying /api/v1/retrieval/google/drive.
    Then it should return 404 Integration Not Attached.
    """
    # Skipping heavy mock flow, assuming client gets authenticated
    # by generating token or forcing deps override here:
    from app.api.deps import get_current_user
    from app.models.user import User

    async def mock_user():
        # UUID random for mock
        import uuid
        return User(id=uuid.uuid4(), email="test@test.com", is_active=True)
        
    async_client.app.dependency_overrides[get_current_user] = mock_user
    
    # We pass random uuid since the Workspace doesn't have an integration mapped
    res = await async_client.get("/api/v1/retrieval/google/drive")
    # Will fail 404 because no workspace / integration exists attached to this user mock!
    # IntegrationNotAttached propagates to 404
    assert res.status_code == 404
    assert "not connected" in res.json()["detail"].lower()
    
    async_client.app.dependency_overrides.clear()
