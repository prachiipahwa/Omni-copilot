from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.integration import IntegrationStatusResponse
from app.services.integration import IntegrationService
from sqlalchemy.future import select

router = APIRouter()

async def get_current_workspace(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> UUID:
    """Mock getting the active workspace for a user. In production, this might come from a header."""
    stmt = select(Workspace).where(Workspace.owner_id == user.id)
    result = await db.execute(stmt)
    workspace = result.scalars().first()
    if not workspace:
        # Auto-create default workspace for Phase 2 demo purposes
        workspace = Workspace(name=f"{user.full_name or 'User'}'s Workspace", owner_id=user.id)
        db.add(workspace)
        await db.commit()
        await db.refresh(workspace)
    return workspace.id

@router.get("/status", response_model=List[IntegrationStatusResponse])
async def get_integration_status(
    workspace_id: UUID = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    service = IntegrationService(db)
    return await service.get_status_for_workspace(workspace_id)
