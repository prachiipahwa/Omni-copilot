from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from sqlalchemy.future import select

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.indexing import SyncResponse, IndexedDocumentStatus
from app.models.document import IndexedDocument
from app.services.retrieval import RetrievalService
from app.ingestion.pipeline import IngestionPipeline
from app.api.v1.endpoints.integrations import get_current_workspace

router = APIRouter()

@router.post("/sync/{provider}", response_model=SyncResponse)
async def trigger_sync(
    provider: str,
    background_tasks: BackgroundTasks,
    workspace_id: UUID = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    """
    Synchronously runs vector injection for the requested provider's data.
    Uses IngestionPipeline to securely crawl, clean, encode, and vector-map the boundaries.
    """
    if provider != "google":
        raise HTTPException(status_code=400, detail="Only 'google' provider currently supported.")

    retrieval_service = RetrievalService(db)
    pipeline = IngestionPipeline(db, retrieval_service)
    
    try:
        # In a purely background setup: background_tasks.add_task(pipeline.execute_google_sync, str(workspace_id))
        # For Phase 4B visual test validation, we execute it inline to return explicit vector counts:
        return await pipeline.execute_google_sync(str(workspace_id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status", response_model=list[IndexedDocumentStatus])
async def get_index_status(
    workspace_id: UUID = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    """Returns the vector-mapping ingestion states tied to postgres."""
    stmt = select(IndexedDocument).where(IndexedDocument.workspace_id == workspace_id).order_by(IndexedDocument.updated_at.desc())
    result = await db.execute(stmt)
    docs = result.scalars().all()
    
    return [
        IndexedDocumentStatus(
            id=str(d.id),
            source_id=d.source_id,
            provider_source=d.provider_source,
            title=d.title,
            status=d.status,
            chunk_count=d.chunk_count,
            updated_at=d.updated_at
        ) for d in docs
    ]
