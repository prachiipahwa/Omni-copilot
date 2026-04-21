from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.base_class import Base

class IndexedDocument(Base):
    """
    Persists metadata about documents that have been pushed to the vector store.
    This links the vector embeddings (stored in Chroma) back to Postgres logical space.
    """
    __tablename__ = "indexed_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # "google_drive", "gmail", "google_calendar", etc.
    provider_source = Column(String, nullable=False, index=True)
    
    # Original remote ID (e.g. Google Drive File ID)
    source_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=True)
    
    # "pending", "success", "failed"
    status = Column(String, default="pending", nullable=False)
    
    chunk_count = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    workspace = relationship("Workspace", back_populates="indexed_documents")
