"""
Chat orchestration endpoint — the only route in the codebase that touches
the OrchestrationPipeline.  Handlers are intentionally thin.
"""
from __future__ import annotations

import uuid
from functools import lru_cache
from typing import List
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_current_user, get_db
from app.api.v1.endpoints.integrations import get_current_workspace
from app.api.v1.endpoints.search import get_search_service
from app.integrations.exceptions import ProviderAPIError
from app.models.chat import ChatSession, Message
from app.models.user import User
from app.orchestration.llm import LLMAdapter
from app.orchestration.pipeline import OrchestrationPipeline
from app.schemas.chat_turn import (
    ChatMessageResponse,
    ChatSendRequest,
    ChatSessionSummary,
    ChatTurnResponse,
    SourceCitation,
)
from app.services.retrieval import RetrievalService

logger = structlog.get_logger(__name__)
router = APIRouter()

# Maximum turns of history to pass to the LLM
_HISTORY_WINDOW = 10   # 10 messages = 5 turns
# Per-message content cap — prevents one huge earlier message from bloating context
_MAX_HISTORY_MSG_CHARS = 800


# ── Singleton factories ────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_llm() -> LLMAdapter:
    return LLMAdapter()


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get_or_create_session(
    db: AsyncSession,
    user_id: UUID,
    session_id: UUID | None,
    first_message: str,
) -> ChatSession:
    if session_id:
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
                ChatSession.deleted_at.is_(None),
            )
        )
        session = result.scalars().first()
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found.")
        return session

    # Auto-title from first 60 chars of message
    title = first_message[:60].strip()
    session = ChatSession(user_id=user_id, title=title)
    db.add(session)
    await db.flush()  # populate session.id before using it
    return session


async def _load_history(db: AsyncSession, session_id: UUID) -> list[dict]:
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id, Message.role.in_(["user", "assistant"]))
        .order_by(Message.created_at.asc())
    )
    messages = result.scalars().all()
    # Apply window + per-message content cap
    windowed = messages[-_HISTORY_WINDOW:]
    return [
        {"role": m.role, "content": m.content[:_MAX_HISTORY_MSG_CHARS]}
        for m in windowed
    ]


async def _persist_turn(
    db: AsyncSession,
    session_id: UUID,
    user_message: str,
    assistant_answer: str,
    meta: dict,
) -> Message:
    """Persist both messages in a single atomic commit."""
    user_msg = Message(session_id=session_id, role="user", content=user_message)
    asst_msg = Message(
        session_id=session_id,
        role="assistant",
        content=assistant_answer,
        meta_data=meta,
    )
    db.add(user_msg)
    db.add(asst_msg)
    # Single commit — if this fails, neither message is persisted (atomic)
    await db.commit()
    await db.refresh(asst_msg)
    return asst_msg


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/send", response_model=ChatTurnResponse)
async def send_message(
    body: ChatSendRequest,
    workspace_id: UUID = Depends(get_current_workspace),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Main orchestrated chat endpoint.  Classifies intent, calls tools,
    assembles grounded context, calls LLM, persists turn, returns response.
    """
    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # ── Session resolution ────────────────────────────────────────────────────
    session = await _get_or_create_session(db, user.id, body.session_id, message)

    # ── History ───────────────────────────────────────────────────────────────
    history = await _load_history(db, session.id)

    # ── Pipeline execution ────────────────────────────────────────────────────
    retrieval_service = RetrievalService(db)
    pipeline = OrchestrationPipeline(
        search_service=get_search_service(),
        retrieval_service=retrieval_service,
        llm=_get_llm(),
    )

    try:
        result = await pipeline.run(
            message=message,
            workspace_id=str(workspace_id),
            history=history,
        )
    except ProviderAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # ── Persist turn ──────────────────────────────────────────────────────────
    asst_msg = await _persist_turn(
        db,
        session.id,
        message,
        result.answer,
        {
            "intent": result.intent,
            "tools_used": result.tools_used,
            "sources": result.sources,
            "fallback": result.fallback,
        },
    )

    return ChatTurnResponse(
        session_id=str(session.id),
        message_id=str(asst_msg.id),
        answer=result.answer,
        intent=result.intent,
        tools_used=result.tools_used,
        sources=[SourceCitation(**s) for s in result.sources if _valid_source(s)],
        fallback=result.fallback,
        latency_ms=result.latency_ms,
    )


@router.get("/sessions", response_model=List[ChatSessionSummary])
async def list_sessions(
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user.id, ChatSession.deleted_at.is_(None))
        .order_by(ChatSession.created_at.desc())
        .limit(limit)
    )
    sessions = result.scalars().all()
    return [
        ChatSessionSummary(
            id=str(s.id),
            title=s.title,
            created_at=s.created_at,
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_session_messages(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify ownership
    sess_result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == user.id,
        )
    )
    if not sess_result.scalars().first():
        raise HTTPException(status_code=404, detail="Session not found.")

    msg_result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
    )
    messages = msg_result.scalars().all()
    return [
        ChatMessageResponse(
            id=str(m.id),
            role=m.role,
            content=m.content,
            created_at=m.created_at,
            meta_data=m.meta_data,
        )
        for m in messages
    ]


# ── Utility ────────────────────────────────────────────────────────────────────

def _valid_source(s: dict) -> bool:
    return bool(s.get("id") and s.get("title") and s.get("provider"))
