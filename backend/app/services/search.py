from typing import List, Dict, Any, Optional
import structlog
import time
from app.vectorstore.base import VectorStoreAdapter

logger = structlog.get_logger(__name__)

# ── Configuration constants ────────────────────────────────
DEFAULT_SCORE_THRESHOLD = 0.25      # Min cosine similarity to keep a result
MAX_CHUNKS_PER_SOURCE = 3           # Prevent one source from flooding results
OVER_RETRIEVAL_FACTOR = 3           # Multiply k to ensure enough diverse candidates


class SemanticSearchService:
    """
    Orchestrates vector retrieval with production-grade ranking, deduplication,
    score thresholding, and source-diversity controls.
    """

    def __init__(
        self,
        vector_store: VectorStoreAdapter,
        score_threshold: float = DEFAULT_SCORE_THRESHOLD,
        max_per_source: int = MAX_CHUNKS_PER_SOURCE,
    ):
        self.vector_store = vector_store
        self.score_threshold = score_threshold
        self.max_per_source = max_per_source

    @staticmethod
    def _dedupe(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove chunks with identical IDs, keeping the first (highest-ranked) occurrence."""
        seen_ids: set = set()
        unique: List[Dict[str, Any]] = []
        for c in chunks:
            cid = c.get("id")
            if cid not in seen_ids:
                seen_ids.add(cid)
                unique.append(c)
        return unique

    def _enforce_source_diversity(self, chunks: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        """
        Caps the number of chunks from any single source_id.
        Preserves the original ranking order so the best chunks survive.
        Returns up to 'limit' total chunks after pruning.
        """
        source_counts: Dict[str, int] = {}
        diverse: List[Dict[str, Any]] = []
        for c in chunks:
            if len(diverse) >= limit:
                break
            src = c.get("metadata", {}).get("source_id", "unknown")
            count = source_counts.get(src, 0)
            if count < self.max_per_source:
                diverse.append(c)
                source_counts[src] = count + 1
        return diverse

    async def search(
        self,
        query: str,
        workspace_id: str,
        k: int = 10,
        source_filter: Optional[str] = None,
        score_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Full retrieval pipeline with OVER-RETRIEVAL to protect diversity:
        1. Request k * OVER_RETRIEVAL candidates from vector store
        2. Deduplicate identical chunks
        3. Filter by provider_source if requested
        4. Apply score threshold
        5. Prune by source diversity (max_per_source)
        6. Cap result at final k
        """
        t0 = time.monotonic()
        effective_threshold = score_threshold if score_threshold is not None else self.score_threshold
        
        # Over-retrieve to compensate for diversity pruning
        candidate_k = k * OVER_RETRIEVAL_FACTOR

        raw_results = await self.vector_store.similarity_search(query, workspace_id, k=candidate_k)

        # 1. Dedupe
        results = self._dedupe(raw_results)

        # 2. Provider filter
        if source_filter:
            results = [r for r in results if r.get("metadata", {}).get("provider_source") == source_filter]

        # 3. Score threshold
        results = [r for r in results if r.get("score", 0.0) >= effective_threshold]

        # 4. Source diversity (with final k limit)
        results = self._enforce_source_diversity(results, limit=k)

        # 5. Final stable sort
        results.sort(key=lambda x: x.get("score", 0.0), reverse=True)

        elapsed_ms = round((time.monotonic() - t0) * 1000, 1)
        logger.info(
            "semantic_search_hardened",
            workspace_id=workspace_id,
            k=k,
            requested_candidates=candidate_k,
            final_count=len(results),
            elapsed_ms=elapsed_ms,
        )
        return results
