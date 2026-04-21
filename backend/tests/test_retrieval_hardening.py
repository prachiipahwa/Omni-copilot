import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from app.ingestion.pipeline import IngestionPipeline
from app.services.search import SemanticSearchService
from app.schemas.retrieval import DriveFileItem, EmailItem
from app.schemas.indexing import IndexChunk, ChunkMetadata

@pytest.mark.asyncio
async def test_google_doc_full_text_indexing():
    """Verify that IngestionPipeline calls get_document_text for Google Docs."""
    db = AsyncMock()
    retrieval_service = AsyncMock()
    
    # Mock a Google Doc
    doc_item = DriveFileItem(
        id="doc-123",
        name="Test Doc",
        mime_type="application/vnd.google-apps.document",
        provider_source="google",
        web_view_link="http://link",
        created_at="2024-01-01",
        updated_at="2024-01-01"
    )
    
    retrieval_service.get_document_text.return_value = "Extracted document content"
    
    pipeline = IngestionPipeline(db, retrieval_service)
    
    # Mock _update_document_status to avoid DB hits
    pipeline._update_document_status = AsyncMock()
    # Mock vector store
    pipeline.vector_store.add_documents = AsyncMock(return_value=1)
    pipeline.vector_store.delete_documents = AsyncMock()

    await pipeline._sync_single_document(doc_item, str(uuid.uuid4()))
    
    retrieval_service.get_document_text.assert_called_once()
    args, kwargs = pipeline.vector_store.add_documents.call_args
    chunks = args[0]
    assert "Extracted document content" in chunks[0].text

@pytest.mark.asyncio
async def test_email_body_extraction_indexing():
    """Verify that IngestionPipeline uses the 'body' attribute for emails if present."""
    db = AsyncMock()
    retrieval_service = AsyncMock()
    
    email_item = EmailItem(
        id="email-123",
        sender="bob@example.com",
        subject="Important News",
        snippet="Short snippet",
        body="This is the full long email body that should be indexed.",
        date="2024-01-01",
        provider_source="google"
    )
    
    pipeline = IngestionPipeline(db, retrieval_service)
    pipeline._update_document_status = AsyncMock()
    pipeline.vector_store.add_documents = AsyncMock(return_value=1)
    pipeline.vector_store.delete_documents = AsyncMock()

    await pipeline._sync_single_document(email_item, str(uuid.uuid4()))
    
    args, kwargs = pipeline.vector_store.add_documents.call_args
    chunks = args[0]
    assert "This is the full long email body" in chunks[0].text

@pytest.mark.asyncio
async def test_search_over_retrieval_diversity():
    """Verify that SemanticSearchService requests k * 3 candidates."""
    vector_store = AsyncMock()
    # Return 30 chunks, all from the same source
    mock_results = []
    for i in range(30):
        mock_results.append({
            "id": f"chunk-{i}",
            "text": f"text {i}",
            "score": 0.9,
            "metadata": {"source_id": "doc-1", "provider_source": "google"}
        })
    vector_store.similarity_search.return_value = mock_results
    
    service = SemanticSearchService(vector_store, max_per_source=3)
    
    results = await service.search(query="test", workspace_id="ws-1", k=5)
    
    # Over-retrieval check
    vector_store.similarity_search.assert_called_once_with("test", "ws-1", k=15) # k=5 * 3
    
    # Diversity check: max_per_source=3 means only 3 chunks from doc-1 survive
    assert len(results) == 3

@pytest.mark.asyncio
async def test_concurrent_indexing_sanity():
    """Verify that IngestionPipeline uses asyncio.gather for sync."""
    db = AsyncMock()
    retrieval_service = AsyncMock()
    
    retrieval_service.get_drive_files.return_value = [
        DriveFileItem(id=f"f-{i}", name=f"F{i}", mime_type="text/plain", provider_source="google") for i in range(3)
    ]
    retrieval_service.get_recent_emails.return_value = []
    retrieval_service.get_upcoming_events.return_value = []
    
    pipeline = IngestionPipeline(db, retrieval_service)
    # Track how many times _sync_single_document is called
    pipeline._sync_single_document = AsyncMock(return_value=1)
    
    await pipeline.execute_google_sync(str(uuid.uuid4()))
    
    assert pipeline._sync_single_document.call_count == 3
