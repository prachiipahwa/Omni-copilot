from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from uuid import UUID
from typing import List, Optional

from app.models.chat import ChatSession, Message
from app.schemas.chat import ChatSessionCreate, MessageCreate

class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(self, user_id: UUID, session_in: ChatSessionCreate) -> ChatSession:
        db_session = ChatSession(user_id=user_id, title=session_in.title or "New Chat")
        self.db.add(db_session)
        await self.db.commit()
        await self.db.refresh(db_session)
        return db_session

    async def get_sessions_for_user(self, user_id: UUID, limit: int = 20, skip: int = 0) -> List[ChatSession]:
        stmt = (
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_session(self, session_id: UUID, user_id: UUID) -> Optional[ChatSession]:
        stmt = (
            select(ChatSession)
            .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .options(selectinload(ChatSession.messages))
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def add_message(self, session_id: UUID, user_id: UUID, message_in: MessageCreate) -> Message:
        # Verify ownership
        session = await self.get_session(session_id, user_id)
        if not session:
            raise ValueError("Chat session not found or access denied")
            
        new_msg = Message(
            session_id=session_id,
            role=message_in.role,
            content=message_in.content,
            meta_data=message_in.meta_data
        )
        self.db.add(new_msg)
        await self.db.commit()
        await self.db.refresh(new_msg)
        return new_msg
