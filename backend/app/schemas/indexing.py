from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

class ChunkMetadata(BaseModel):
    chunk_index: int
    workspace_id: str
    source_url: str = ""
    # Add any future signal hashes or strict parameters here for vector indexing stability.
    version_hash: str = ""

class IndexChunk(BaseModel):
    chunk_id: str
    source_id: str
    provider_source: str
    title: str = "Unknown"
    text: str
    created_at: str = ""
    updated_at: str = ""
    metadata: ChunkMetadata

    
class IndexedDocumentStatus(BaseModel):
    id: str
    source_id: str
    provider_source: str
    title: Optional[str] = None
    status: str
    chunk_count: int
    updated_at: datetime
    
class SyncResponse(BaseModel):
    provider: str
    documents_processed: int
    chunks_indexed: int
    status: str
