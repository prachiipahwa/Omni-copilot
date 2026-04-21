import chromadb
import asyncio
from typing import List, Dict, Any, Optional
from app.schemas.indexing import IndexChunk
from app.vectorstore.base import VectorStoreAdapter
from app.embeddings.base import EmbeddingsAdapter


class ChromaAdapter(VectorStoreAdapter):
    def __init__(self, persist_directory: str = "./vector_data", embedding_model: Optional[EmbeddingsAdapter] = None):
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.embedding_model = embedding_model

    def _get_collection(self, workspace_id: str):
        return self.client.get_or_create_collection(
            name=f"workspace_{workspace_id.replace('-', '_')}",
            metadata={"hnsw:space": "cosine"}
        )

    # ── Ingestion ──────────────────────────────────────────────

    def _add_docs_sync(self, chunks: List[IndexChunk], workspace_id: str, embeddings: Optional[List[List[float]]] = None) -> int:
        if not chunks:
            return 0

        collection = self._get_collection(workspace_id)

        ids = [c.chunk_id for c in chunks]
        documents = [c.text for c in chunks]
        metadatas = []
        for c in chunks:
            meta = c.metadata.model_dump()
            meta["source_id"] = c.source_id
            meta["provider_source"] = c.provider_source
            meta["title"] = c.title
            metadatas.append(meta)

        upsert_kwargs: Dict[str, Any] = {
            "ids": ids,
            "documents": documents,
            "metadatas": metadatas
        }
        if embeddings:
            upsert_kwargs["embeddings"] = embeddings

        collection.upsert(**upsert_kwargs)
        return len(ids)

    async def add_documents(self, chunks: List[IndexChunk], workspace_id: str) -> int:
        embeddings = None
        if self.embedding_model:
            texts = [c.text for c in chunks]
            embeddings = await self.embedding_model.embed_documents(texts)

        return await asyncio.to_thread(self._add_docs_sync, chunks, workspace_id, embeddings)

    # ── Search ─────────────────────────────────────────────────

    def _search_sync(
        self,
        query: str,
        workspace_id: str,
        k: int,
        query_embedding: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]:
        collection = self._get_collection(workspace_id)

        query_kwargs: Dict[str, Any] = {
            "n_results": k,
            "include": ["documents", "metadatas", "distances"],
        }
        if query_embedding:
            query_kwargs["query_embeddings"] = [query_embedding]
        else:
            query_kwargs["query_texts"] = [query]

        results = collection.query(**query_kwargs)

        formatted: List[Dict[str, Any]] = []
        if results and results.get("documents") and len(results["documents"][0]) > 0:
            doc_group = results["documents"][0]
            meta_group = results["metadatas"][0] if results.get("metadatas") else []
            id_group = results["ids"][0]
            # Chroma returns cosine *distances* (0 = identical, 2 = opposite).
            dist_group = results["distances"][0] if results.get("distances") else []

            for i, doc in enumerate(doc_group):
                distance = dist_group[i] if i < len(dist_group) else None
                # Convert cosine distance → similarity score (1 - distance)
                score = round(1.0 - distance, 4) if distance is not None else 0.0
                formatted.append({
                    "id": id_group[i],
                    "text": doc,
                    "score": score,
                    "metadata": meta_group[i] if i < len(meta_group) else {},
                })

        return formatted

    async def similarity_search(self, query: str, workspace_id: str, k: int = 5) -> List[Dict[str, Any]]:
        query_embedding = None
        if self.embedding_model:
            query_embedding = await self.embedding_model.embed_query(query)
        return await asyncio.to_thread(self._search_sync, query, workspace_id, k, query_embedding)

    # ── Deletion ───────────────────────────────────────────────

    def _delete_sync(self, source_id: str, workspace_id: str) -> bool:
        collection = self._get_collection(workspace_id)
        collection.delete(where={"source_id": source_id})
        return True

    async def delete_documents(self, source_id: str, workspace_id: str) -> bool:
        return await asyncio.to_thread(self._delete_sync, source_id, workspace_id)
