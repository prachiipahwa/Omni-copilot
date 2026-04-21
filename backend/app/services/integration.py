from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from typing import List

from app.models.integration import Integration
from app.schemas.integration import IntegrationStatusResponse

class IntegrationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_status_for_workspace(self, workspace_id: UUID) -> List[IntegrationStatusResponse]:
        """Provides status of integrations without exposing encrypted credentials."""
        # For Phase 2, we just return mock defaults if none exist in DB
        SUPPORTED_PROVIDERS = ["google_drive", "slack", "notion"]
        
        stmt = select(Integration).where(Integration.workspace_id == workspace_id)
        result = await self.db.execute(stmt)
        active_integrations = result.scalars().all()
        active_providers = {i.provider: i for i in active_integrations}
        
        statuses = []
        for provider in SUPPORTED_PROVIDERS:
            integration = active_providers.get(provider)
            is_connected = integration is not None and integration.status == "active"
            statuses.append(IntegrationStatusResponse(
                provider=provider,
                is_connected=is_connected,
                status_label="Connected" if is_connected else "Disconnected"
            ))
            
        return statuses
