from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.chat import ChatSessionCreate, ChatSessionResponse, MessageCreate, MessageResponse
from app.services.chat import ChatService

router = APIRouter()

@router.post("/", response_model=ChatSessionResponse)
async def create_chat_session(
    session_in: ChatSessionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = ChatService(db)
    try:
        return await service.create_session(user.id, session_in)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create chat session")

@router.get("/", response_model=List[ChatSessionResponse])
async def get_chat_sessions(
    limit: int = 20,
    skip: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = ChatService(db)
    return await service.get_sessions_for_user(user.id, limit, skip)

@router.get("/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = ChatService(db)
    session = await service.get_session(session_id, user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.post("/{session_id}/messages", response_model=MessageResponse)
async def add_message(
    session_id: UUID,
    message_in: MessageCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = ChatService(db)
    try:
        return await service.add_message(session_id, user.id, message_in)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to process message")
