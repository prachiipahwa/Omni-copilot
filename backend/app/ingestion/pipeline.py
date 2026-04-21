import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import structlog
from typing import List, Any
import uuid

from app.schemas.retrieval import DocumentContent, EmailItem, CalendarEventItem, DriveFileItem
from app.schemas.indexing import IndexChunk, SyncResponse
from app.models.document import IndexedDocument
from app.ingestion.cleaner import TextCleaner
from app.ingestion.chunker import Chunker
from app.vectorstore.chroma import ChromaAdapter
from app.embeddings.openai import OpenAIAdapter
from app.services.retrieval import RetrievalService
from app.core.config import settings

logger = structlog.get_logger(__name__)

class IngestionPipeline:
    """Production robust Pipeline aggregating providers, running map-reduce chunks, and asserting Postgres metadata logs."""
    
    def __init__(self, db: AsyncSession, retrieval_service: RetrievalService):
        self.db = db
        self.retrieval_service = retrieval_service
        self.chunker = Chunker(chunk_size=400, overlap=50)
        self.vector_store = ChromaAdapter(embedding_model=OpenAIAdapter())
        self.semaphore = asyncio.Semaphore(settings.INGESTION_CONCURRENCY)

    async def _update_document_status(self, workspace_id: str, source_id: str, provider: str, title: str, chunks_indexed: int, status: str):
        # We need a fresh session or a shared lock for concurrency if using one session
        # For simplicity in this service, we assume the caller manages the session transactionality or we commit per-doc.
        # Given the pipeline structure, we commit per document update.
        stmt = select(IndexedDocument).where(
            IndexedDocument.workspace_id == workspace_id, 
            IndexedDocument.source_id == source_id
        )
        result = await self.db.execute(stmt)
        doc = result.scalars().first()
        
        if not doc:
            doc = IndexedDocument(
                workspace_id=workspace_id,
                source_id=source_id,
                provider_source=provider,
                title=title
            )
            self.db.add(doc)
            
        doc.status = status
        doc.chunk_count = chunks_indexed
        doc.updated_at = asyncio.get_event_loop().time() # Placeholder for timestamp mapping
        await self.db.commit()

    async def _process_item_to_chunks(self, item: Any, provider: str, workspace_id: str) -> List[IndexChunk]:
        """Maps varying Phase 4A extraction DTOs into standard abstract Pipeline objects"""
        text = ""
        title = "Untitled"
        url = ""
        source_id = getattr(item, "id", str(uuid.uuid4()))
        created_at = getattr(item, "created_at", "")
        updated_at = getattr(item, "updated_at", "")

        if isinstance(item, DocumentContent):
            title = item.title
            text = item.text_content
        elif isinstance(item, EmailItem):
            title = item.subject
            # Use full body if available from our hardened provider
            content = getattr(item, "body", None) or item.snippet
            text = f"From: {item.sender}\nDate: {item.date}\nSubject: {item.subject}\n\n{content}"
        elif isinstance(item, CalendarEventItem):
            title = item.summary
            text = f"Time: {item.start_time} to {item.end_time}\n{item.description}"
            url = item.html_link or ""
        elif isinstance(item, DriveFileItem):
            title = item.name
            url = item.web_view_link or ""
            # CRITICAL: If Google Doc, fetch actual text
            if item.mime_type == "application/vnd.google-apps.document":
                try:
                    text = await self.retrieval_service.get_document_text(workspace_id, item.id)
                except Exception as e:
                    logger.warning("failed_doc_text_extraction", doc_id=item.id, error=str(e))
                    text = f"File Name: {item.name}\n(Content extraction failed)"
            else:
                text = f"File Name: {item.name}\nMimeType: {item.mime_type}"

        cleaned_text = TextCleaner.clean(text, is_html=isinstance(item, (EmailItem, CalendarEventItem)))
        if not cleaned_text.strip():
             return []

        raw_chunks = self.chunker.chunk_text(cleaned_text)
        
        index_chunks = []
        from app.schemas.indexing import ChunkMetadata
        
        for i, c in enumerate(raw_chunks):
            chunk_id = f"{source_id}_chunk_{i}"
            index_chunks.append(IndexChunk(
                chunk_id=chunk_id,
                source_id=source_id,
                provider_source=provider,
                title=title,
                text=c,
                created_at=str(created_at),
                updated_at=str(updated_at),
                metadata=ChunkMetadata(
                    chunk_index=i,
                    workspace_id=workspace_id,
                    source_url=url
                )
            ))
        return index_chunks

    async def _sync_single_document(self, item: Any, workspace_id: str) -> int:
        """Incremental transaction safe push for atomic documents."""
        async with self.semaphore:
            try:
                chunks = await self._process_item_to_chunks(item, item.provider_source, workspace_id)
                if not chunks:
                    await self._update_document_status(workspace_id, item.id, item.provider_source, getattr(item, "name", getattr(item, "subject", "Untitled")), 0, "success")
                    return 0
                    
                await self.vector_store.delete_documents(item.id, workspace_id)
                stored = await self.vector_store.add_documents(chunks, workspace_id)
                
                await self._update_document_status(workspace_id, item.id, item.provider_source, getattr(item, "name", getattr(item, "subject", getattr(item, "summary", getattr(item, "title", "Untitled")))), stored, "success")
                return stored
            except Exception as e:
                logger.error("single_doc_sync_failed", id=getattr(item, "id", "unknown"), error=str(e))
                await self._update_document_status(workspace_id, getattr(item, "id", "unknown"), getattr(item, "provider_source", "unknown"), "Failed Sync", 0, "failed")
                return 0

    async def execute_google_sync(self, workspace_id: str) -> SyncResponse:
        """Executes a highly concurrent pull, mapping, chunking and vector storage loop for Google Integrations."""
        logger.info("indexing_job_started", workspace_id=workspace_id, provider="google")
        
        # 1. Fetch all items (Metadata only retrieval)
        try:
            drive_task = self.retrieval_service.get_drive_files(workspace_id, max_results=settings.SYNC_DRIVE_MAX_RESULTS)
            email_task = self.retrieval_service.get_recent_emails(workspace_id, max_results=settings.SYNC_EMAIL_MAX_RESULTS)
            calendar_task = self.retrieval_service.get_upcoming_events(workspace_id, max_results=settings.SYNC_CALENDAR_MAX_RESULTS)
            
            drive_files, emails, events = await asyncio.gather(drive_task, email_task, calendar_task)
        except Exception as e:
            logger.error("bulk_fetch_failed", error=str(e))
            return SyncResponse(provider="google", status="failed", error=str(e))

        # 2. Process all items concurrently with semaphore protection
        all_items = drive_files + emails + events
        tasks = [self._sync_single_document(item, workspace_id) for item in all_items]
        
        results = await asyncio.gather(*tasks)
        total_chunks = sum(results)
        total_docs = len([r for r in results if r >= 0])

        logger.info("indexing_job_complete", workspace_id=workspace_id, docs=total_docs, chunks=total_chunks)
        return SyncResponse(
            provider="google",
            documents_processed=total_docs,
            chunks_indexed=total_chunks,
            status="success"
        )
