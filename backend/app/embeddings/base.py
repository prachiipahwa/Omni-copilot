from abc import ABC, abstractmethod
from typing import List

class EmbeddingsAdapter(ABC):
    """
    Abstract bridge for Vector Embeddings generating Dense vectors natively.
    Ensures architectural independence from any single provider (OpenAI, Anthropic, Local)
    """

    @abstractmethod
    async def embed_query(self, text: str) -> List[float]:
        """Embeds a single sparse query natively"""
        pass

    @abstractmethod
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embeds bulk arrays mapping to VectorStore ingestions"""
        pass
