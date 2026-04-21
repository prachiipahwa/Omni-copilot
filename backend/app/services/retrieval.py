from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from typing import List
import structlog

from app.models.integration import Integration
from app.core.encryption import decrypt_dict, encrypt_dict
from app.integrations.google.provider import GoogleConnector
from app.schemas.retrieval import DriveFileItem, EmailItem, CalendarEventItem, DocumentContent
from app.integrations.exceptions import TokenExpiredError, IntegrationNotAttachedError

logger = structlog.get_logger(__name__)

class RetrievalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_valid_google_token(self, workspace_id: UUID) -> str:
        stmt = select(Integration).where(Integration.workspace_id == workspace_id, Integration.provider == "google")
        result = await self.db.execute(stmt)
        integration = result.scalars().first()
        
        if not integration or not integration.credentials:
            raise IntegrationNotAttachedError("Google Integration is not connected or missing credentials")

        creds = decrypt_dict(integration.credentials)
        access_token = creds.get("access_token")
        return access_token

    async def refresh_and_save_google_token(self, workspace_id: UUID) -> str:
        stmt = select(Integration).where(Integration.workspace_id == workspace_id, Integration.provider == "google")
        result = await self.db.execute(stmt)
        integration = result.scalars().first()
        
        if not integration:
             raise IntegrationNotAttachedError("Integration not found")
        
        creds = decrypt_dict(integration.credentials)
        refresh_token = creds.get("refresh_token")
        if not refresh_token:
            logger.warning("No refresh token available during expiration catch", workspace_id=str(workspace_id))
            raise ValueError("No refresh token available to reauthorize")

        provider = GoogleConnector()
        new_payload = await provider.refresh_credentials(refresh_token)
        
        creds["access_token"] = new_payload.get("access_token")
        if new_payload.get("refresh_token"):
             creds["refresh_token"] = new_payload.get("refresh_token")
             
        integration.credentials = encrypt_dict(creds)
        await self.db.commit()
        logger.info("Successfully refreshed and rotated Provider token", provider="google", workspace_id=str(workspace_id))
        return creds["access_token"]

    async def handle_provider_request(self, workspace_id: UUID, task_func):
        """Orchestrates DB decryption, executing the provider, and aggressively catching token drops EXACTLY ONCE."""
        token = await self._get_valid_google_token(workspace_id)
        try:
            return await task_func(token)
        except TokenExpiredError:
            logger.info("Token expired intercept. Requesting provider refresh.", provider="google")
            refreshed_token = await self.refresh_and_save_google_token(workspace_id)
            return await task_func(refreshed_token)

    async def get_drive_files(self, workspace_id: UUID, max_results: int = 10) -> List[DriveFileItem]:
        provider = GoogleConnector()
        async def _task(token: str):
            raw_files = await provider.list_drive_files(token, max_results)
            return [DriveFileItem(**f) for f in raw_files]
        return await self.handle_provider_request(workspace_id, _task)

    async def get_document_content(self, workspace_id: UUID, document_id: str) -> DocumentContent:
        provider = GoogleConnector()
        async def _task(token: str):
            text = await provider.get_document_text(token, document_id)
            return DocumentContent(id=document_id, title="Extracted", text_content=text)
        return await self.handle_provider_request(workspace_id, _task)

    async def get_recent_emails(self, workspace_id: UUID, max_results: int = 10) -> List[EmailItem]:
        provider = GoogleConnector()
        async def _task(token: str):
            raw_emails = await provider.list_recent_emails(token, max_results)
            return [EmailItem(**e) for e in raw_emails]
        return await self.handle_provider_request(workspace_id, _task)

    async def get_upcoming_events(self, workspace_id: UUID, max_results: int = 10) -> List[CalendarEventItem]:
        provider = GoogleConnector()
        async def _task(token: str):
            raw_events = await provider.list_upcoming_events(token, max_results)
            return [CalendarEventItem(**e) for e in raw_events]
        return await self.handle_provider_request(workspace_id, _task)
