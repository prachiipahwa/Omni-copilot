from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.workspace import Workspace
from sqlalchemy.future import select

from app.schemas.retrieval import DriveFileItem, EmailItem, CalendarEventItem, DocumentContent
from app.services.retrieval import RetrievalService
from app.api.v1.endpoints.integrations import get_current_workspace

router = APIRouter()

from app.integrations.exceptions import IntegrationError, IntegrationNotAttachedError, MissingScopeError, TokenRevokedError

def _handle_retrieval_exception(e: Exception):
    """Normalizes provider layer errors out to HTTP context safely."""
    if isinstance(e, IntegrationNotAttachedError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    elif isinstance(e, (MissingScopeError, TokenRevokedError)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Provider access denied: {str(e)}")
    elif isinstance(e, IntegrationError):
        # Includes ProviderAPIError and generic integration boundaries
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    else:
        # Fallback for ValueError (e.g. absent refresh token)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/google/drive", response_model=List[DriveFileItem])
async def list_drive_files(
    max_results: int = 10,
    workspace_id: UUID = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    service = RetrievalService(db)
    try:
        return await service.get_drive_files(workspace_id, max_results)
    except Exception as e:
        _handle_retrieval_exception(e)

@router.get("/google/docs/{document_id}", response_model=DocumentContent)
async def read_google_doc(
    document_id: str,
    workspace_id: UUID = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    service = RetrievalService(db)
    try:
        return await service.get_document_content(workspace_id, document_id)
    except Exception as e:
        _handle_retrieval_exception(e)

@router.get("/google/gmail", response_model=List[EmailItem])
async def list_recent_emails(
    max_results: int = 10,
    workspace_id: UUID = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    service = RetrievalService(db)
    try:
        return await service.get_recent_emails(workspace_id, max_results)
    except Exception as e:
        _handle_retrieval_exception(e)

@router.get("/google/calendar", response_model=List[CalendarEventItem])
async def list_calendar_events(
    max_results: int = 10,
    workspace_id: UUID = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    service = RetrievalService(db)
    try:
        return await service.get_upcoming_events(workspace_id, max_results)
    except Exception as e:
        _handle_retrieval_exception(e)
