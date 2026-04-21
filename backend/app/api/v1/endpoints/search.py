from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from uuid import UUID
from functools import lru_cache

from app.api.v1.endpoints.integrations import get_current_workspace
from app.services.search import SemanticSearchService
from app.services.context import ContextAssemblyService
from app.vectorstore.chroma import ChromaAdapter
from app.embeddings.openai import OpenAIAdapter
from app.integrations.exceptions import ProviderAPIError

router = APIRouter()

# ── Singleton service factory ──────────────────────────────────────────────────
# ChromaAdapter opens a PersistentClient (file handle + SQLite connection).
# OpenAIAdapter holds an AsyncOpenAI client (connection pool).
# Creating new instances per-request wastes resources and bypasses connection
# pooling.  We use lru_cache(maxsize=1) to build one shared instance for the
# process lifetime.  This is safe because neither object holds per-request state.

@lru_cache(maxsize=1)
def _build_search_service() -> SemanticSearchService:
    store = ChromaAdapter(embedding_model=OpenAIAdapter())
    return SemanticSearchService(vector_store=store)


def get_search_service() -> SemanticSearchService:
    """FastAPI dependency — returns the process-level singleton."""
    return _build_search_service()


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/query")
async def execute_semantic_search(
    q: str,
    k: int = 5,
    filter: Optional[str] = None,
    score_threshold: Optional[float] = None,
    workspace_id: UUID = Depends(get_current_workspace),
    search_service: SemanticSearchService = Depends(get_search_service),
):
    """
    Semantic chunk retrieval against the workspace vector store.
    Returns ranked, deduplicated, threshold-filtered chunks.
    """
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required.")

    try:
        results = await search_service.search(
            query=q,
            workspace_id=str(workspace_id),
            k=k,
            source_filter=filter,
            score_threshold=score_threshold,
        )
        return {"results": results, "count": len(results)}
    except ProviderAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/context")
async def execute_context_assembly(
    q: str,
    k: int = 15,
    max_tokens: int = 3000,
    workspace_id: UUID = Depends(get_current_workspace),
    search_service: SemanticSearchService = Depends(get_search_service),
):
    """
    Retrieves relevant chunks and assembles a token-budget-aware context
    string ready for LLM injection (Phase 4D).
    """
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required.")

    try:
        results = await search_service.search(
            query=q,
            workspace_id=str(workspace_id),
            k=k,
        )
        assembly = ContextAssemblyService(max_tokens=max_tokens)
        context_string = assembly.assemble(results)
        return {"context": context_string, "sources_used": len({r.get("metadata", {}).get("source_id") for r in results})}
    except ProviderAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Context assembly failed: {str(e)}")
