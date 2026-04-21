from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID


class ChatSendRequest(BaseModel):
    message: str
    session_id: Optional[UUID] = None   # None = create new session


class SourceCitation(BaseModel):
    id: str
    title: str
    provider: str
    url: str = ""


class ChatTurnResponse(BaseModel):
    session_id: str
    message_id: str
    answer: str
    intent: str
    tools_used: List[str]
    sources: List[SourceCitation]
    fallback: bool
    latency_ms: float


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime
    meta_data: Optional[Any] = None


class ChatSessionSummary(BaseModel):
    id: str
    title: Optional[str]
    created_at: datetime
    message_count: int = 0
