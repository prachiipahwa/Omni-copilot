import uuid
from sqlalchemy import Column, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base_class import Base
from app.models.mixins import TimestampMixin

class Integration(Base, TimestampMixin):
    __tablename__ = "integrations"
    __table_args__ = (
        UniqueConstraint('workspace_id', 'provider', name='uix_workspace_provider'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String, index=True, nullable=False)
    
    # Store encrypted credentials or refresh tokens (No longer plaintext JSON)
    credentials = Column(String, nullable=False) 
    
    status = Column(String, default="active") # active, disconnected, error
    
    workspace = relationship("Workspace", back_populates="integrations")
