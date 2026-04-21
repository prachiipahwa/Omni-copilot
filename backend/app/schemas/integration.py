from uuid import UUID
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class IntegrationResponse(BaseModel):
    id: UUID
    provider: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class IntegrationStatusResponse(BaseModel):
    provider: str
    is_connected: bool
    status_label: str
