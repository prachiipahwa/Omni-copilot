import pytest
from sqlalchemy.exc import IntegrityError
from app.models.workspace import Workspace
from app.models.user import User
from app.models.integration import Integration
from app.db.session import SessionLocal

@pytest.mark.asyncio
async def test_integration_unique_constraint(setup_test_db):
    async with SessionLocal() as session:
        # Create user & workspace
        user = User(email="test@example.com")
        session.add(user)
        await session.commit()
        
        workspace = Workspace(name="Acme", owner_id=user.id)
        session.add(workspace)
        await session.commit()
        
        # Add first integration
        int1 = Integration(workspace_id=workspace.id, provider="google", credentials="enc1")
        session.add(int1)
        await session.commit()
        
        # Attempt to add duplicate provider to same workspace
        int2 = Integration(workspace_id=workspace.id, provider="google", credentials="enc2")
        session.add(int2)
        
        with pytest.raises(IntegrityError):
            await session.commit()
