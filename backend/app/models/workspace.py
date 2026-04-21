import uuid
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base_class import Base
from app.models.mixins import TimestampMixin, SoftDeleteMixin

class Workspace(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "workspaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, index=True, nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    owner = relationship("User", back_populates="workspaces")
    integrations = relationship("Integration", back_populates="workspace", cascade="all, delete-orphan")
    indexed_documents = relationship("IndexedDocument", back_populates="workspace", cascade="all, delete-orphan")
