from abc import ABC, abstractmethod
from typing import List, Dict, Any
from app.schemas.indexing import IndexChunk

class VectorStoreAdapter(ABC):
    """
    Abstract bridge for AI Vector DB orchestrations.
    Guarantees architectural independence from any single provider (Chroma, Pinecone, Weaviate).
    """

    @abstractmethod
    async def add_documents(self, chunks: List[IndexChunk], workspace_id: str) -> int:
        """Inserts indexed chunks mapped safely to the tenant boundary."""
        pass

    @abstractmethod
    async def similarity_search(self, query: str, workspace_id: str, k: int = 5) -> List[Dict[str, Any]]:
        """Finds closest chunks rigidly bound to workspace_id to prevent data leakage."""
        pass

    @abstractmethod
    async def delete_documents(self, source_id: str, workspace_id: str) -> bool:
        """Clears out outdated structures by their original payload identity."""
        pass
