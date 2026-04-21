"""
Tests for Phase 4C: SemanticSearchService and ContextAssemblyService.

All tests are fully offline — no real vector store or OpenAI calls.
MockVectorAdapter returns pre-built results with explicit score values
so threshold/diversity logic can be directly exercised.
"""
import pytest
from app.services.search import SemanticSearchService
from app.services.context import ContextAssemblyService


# ── Shared mock infrastructure ──────────────────────────────────────────────

class MockVectorAdapter:
    """Returns a fixed, score-annotated result set for deterministic tests."""

    def __init__(self, results=None):
        self._results = results if results is not None else _default_results()

    async def similarity_search(self, query, workspace, k):
        return self._results[:k]

    async def add_documents(self, chunks, ws):
        return 0

    async def delete_documents(self, sid, ws):
        return True


def _default_results():
    return [
        # doc1 — two chunks, high score
        {"id": "doc1_c0", "score": 0.85, "text": "Doc one first chunk",  "metadata": {"source_id": "doc1", "title": "Doc A", "provider_source": "google_docs", "chunk_index": 0}},
        {"id": "doc1_c1", "score": 0.80, "text": "Doc one second chunk", "metadata": {"source_id": "doc1", "title": "Doc A", "provider_source": "google_docs", "chunk_index": 1}},
        {"id": "doc1_c2", "score": 0.75, "text": "Doc one third chunk",  "metadata": {"source_id": "doc1", "title": "Doc A", "provider_source": "google_docs", "chunk_index": 2}},
        {"id": "doc1_c3", "score": 0.70, "text": "Doc one fourth chunk", "metadata": {"source_id": "doc1", "title": "Doc A", "provider_source": "google_docs", "chunk_index": 3}},
        # doc2 — moderate score
        {"id": "doc2_c0", "score": 0.60, "text": "Email snippet alpha",  "metadata": {"source_id": "doc2", "title": "Email B", "provider_source": "gmail", "chunk_index": 0}},
        # doc3 — below threshold
        {"id": "doc3_c0", "score": 0.10, "text": "Very low relevance",   "metadata": {"source_id": "doc3", "title": "Noise C", "provider_source": "google_drive", "chunk_index": 0}},
        # duplicate ID (should be deduped)
        {"id": "doc1_c0", "score": 0.85, "text": "Doc one first chunk",  "metadata": {"source_id": "doc1", "title": "Doc A", "provider_source": "google_docs", "chunk_index": 0}},
    ]


# ── Deduplication ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_deduplication_removes_repeated_id():
    """Chunk with the same ID returned twice should be collapsed to one."""
    service = SemanticSearchService(MockVectorAdapter(), score_threshold=0.0, max_per_source=99)
    results = await service.search("test", "ws1", k=10)
    ids = [r["id"] for r in results]
    assert ids.count("doc1_c0") == 1


# ── Score threshold ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_threshold_drops_low_score_chunks():
    """doc3_c0 has score 0.10 — below the 0.25 default — should be excluded."""
    service = SemanticSearchService(MockVectorAdapter(), score_threshold=0.25, max_per_source=99)
    results = await service.search("test", "ws1", k=10)
    source_ids = [r["id"] for r in results]
    assert "doc3_c0" not in source_ids


@pytest.mark.asyncio
async def test_threshold_keeps_chunks_at_or_above_cutoff():
    service = SemanticSearchService(MockVectorAdapter(), score_threshold=0.25, max_per_source=99)
    results = await service.search("test", "ws1", k=10)
    # doc1 + doc2 chunks all have score >= 0.25
    assert all(r["score"] >= 0.25 for r in results)


@pytest.mark.asyncio
async def test_zero_threshold_keeps_everything():
    service = SemanticSearchService(MockVectorAdapter(), score_threshold=0.0, max_per_source=99)
    results = await service.search("test", "ws1", k=10)
    # doc3_c0 (score=0.10) must survive
    assert any(r["id"] == "doc3_c0" for r in results)


@pytest.mark.asyncio
async def test_custom_threshold_passed_per_call():
    """Per-call score_threshold should override instance default."""
    service = SemanticSearchService(MockVectorAdapter(), score_threshold=0.0, max_per_source=99)
    results = await service.search("test", "ws1", k=10, score_threshold=0.80)
    assert all(r["score"] >= 0.80 for r in results)


# ── Source diversity ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_source_diversity_caps_per_source():
    """With max_per_source=2, doc1's four chunks should be capped at 2."""
    service = SemanticSearchService(MockVectorAdapter(), score_threshold=0.0, max_per_source=2)
    results = await service.search("test", "ws1", k=10)
    doc1_count = sum(1 for r in results if r["metadata"]["source_id"] == "doc1")
    assert doc1_count <= 2


@pytest.mark.asyncio
async def test_source_diversity_still_includes_other_sources():
    """Even after capping doc1, doc2 should still appear in results."""
    service = SemanticSearchService(MockVectorAdapter(), score_threshold=0.25, max_per_source=1)
    results = await service.search("test", "ws1", k=10)
    sources_present = {r["metadata"]["source_id"] for r in results}
    assert "doc1" in sources_present
    assert "doc2" in sources_present


# ── Provider source filter ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_source_filter_restricts_provider():
    service = SemanticSearchService(MockVectorAdapter(), score_threshold=0.0, max_per_source=99)
    results = await service.search("test", "ws1", k=10, source_filter="gmail")
    assert all(r["metadata"]["provider_source"] == "gmail" for r in results)
    assert len(results) == 1  # only doc2_c0 is gmail


# ── Result ordering ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_results_are_sorted_descending_by_score():
    service = SemanticSearchService(MockVectorAdapter(), score_threshold=0.0, max_per_source=99)
    results = await service.search("test", "ws1", k=10)
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


# ── ContextAssemblyService ────────────────────────────────────────────────────

def _make_chunks():
    """Minimal scored chunks for context assembly tests."""
    return [
        {"id": "d1_c0", "score": 0.9, "text": "Alpha content from doc one.",
         "metadata": {"source_id": "d1", "title": "Doc One", "provider_source": "google_docs", "chunk_index": 0, "source_url": ""}},
        {"id": "d2_c0", "score": 0.5, "text": "Beta content from email.",
         "metadata": {"source_id": "d2", "title": "Email Two", "provider_source": "gmail", "chunk_index": 0, "source_url": ""}},
    ]


def test_context_assembly_contains_best_source_first():
    """Highest-scoring source should appear before lower-scoring one."""
    svc = ContextAssemblyService(max_tokens=3000)
    out = svc.assemble(_make_chunks())
    pos_d1 = out.find("Doc One")
    pos_d2 = out.find("Email Two")
    assert pos_d1 != -1
    assert pos_d2 != -1
    assert pos_d1 < pos_d2  # doc one (score 0.9) precedes email (score 0.5)


def test_context_assembly_header_format():
    svc = ContextAssemblyService(max_tokens=3000)
    out = svc.assemble(_make_chunks())
    assert "--- [GOOGLE_DOCS] Doc One ---" in out
    assert "--- [GMAIL] Email Two ---" in out


def test_context_assembly_token_budget_respected():
    """With a tiny budget, only the first source (or fraction) should fit."""
    svc = ContextAssemblyService(max_tokens=25)
    out = svc.assemble(_make_chunks())
    # The budget is so tight that at least one source must be excluded
    assert "--- [GMAIL] Email Two ---" not in out


def test_context_assembly_empty_input():
    svc = ContextAssemblyService(max_tokens=3000)
    assert svc.assemble([]) == ""


def test_context_assembly_text_appears_in_output():
    svc = ContextAssemblyService(max_tokens=3000)
    out = svc.assemble(_make_chunks())
    assert "Alpha content from doc one." in out
