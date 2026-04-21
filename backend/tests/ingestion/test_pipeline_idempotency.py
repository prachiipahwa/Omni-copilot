import pytest
from app.ingestion.pipeline import IngestionPipeline
from app.schemas.retrieval import DocumentContent

@pytest.mark.asyncio
async def test_chunk_determinism():
    """Assert deterministic UUIDs to prevent vector leakage"""
    # Create the pipeline mock bypassing DB initialization natively for unit scopes
    class MockService:
        pass
        
    pipeline = IngestionPipeline(db=None, retrieval_service=MockService())
    
    mock_doc = DocumentContent(id="test_123", text_content="Word " * 1000)
    
    chunks_pass_1 = pipeline._process_item_to_chunks(mock_doc, "google_docs", workspace_id="ws_1")
    chunks_pass_2 = pipeline._process_item_to_chunks(mock_doc, "google_docs", workspace_id="ws_1")
    
    assert len(chunks_pass_1) > 0
    assert chunks_pass_1[0].chunk_id == chunks_pass_2[0].chunk_id
    assert chunks_pass_1[-1].chunk_id == chunks_pass_2[-1].chunk_id
    assert chunks_pass_1[0].chunk_id == "test_123_chunk_0"
