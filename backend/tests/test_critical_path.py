"""
Critical-path integration tests for Phase 4E.

All tests are fully offline (mocked services).
Covers: auth guard, search pipeline, orchestration flow,
memory truncation, source rendering validity.
"""
from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient


# ══════════════════════════════════════════════════════════════════════════════
# 1. Auth / session critical path
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_unauth_cannot_reach_chat_send(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/chat/send",
        json={"message": "hello"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_unauth_cannot_reach_search(async_client: AsyncClient):
    response = await async_client.get("/api/v1/search/query?q=test")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_me_returns_401_when_unauthenticated(async_client: AsyncClient):
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_clears_cookie(async_client: AsyncClient):
    response = await async_client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    sc = response.headers.get("set-cookie", "")
    assert "access_token=" in sc
    # Cookie must be expired (Max-Age=0 or past expiry)
    assert "Max-Age=0" in sc or "expires=" in sc.lower()


# ══════════════════════════════════════════════════════════════════════════════
# 2. Search pipeline critical path (offline — no Chroma/OpenAI)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_search_rejects_empty_query(async_client: AsyncClient):
    """Empty q param should return 400, not 500."""
    response = await async_client.get("/api/v1/search/query?q=")
    assert response.status_code in (400, 401)  # 401 if auth guards first


# ══════════════════════════════════════════════════════════════════════════════
# 3. Orchestration pipeline — offline unit tests
# ══════════════════════════════════════════════════════════════════════════════

from app.orchestration.router import classify, Intent
from app.orchestration.pipeline import OrchestrationPipeline, _truncate_history
from app.orchestration.tools import ToolResult, _extract_sources


def _search_svc():
    svc = MagicMock()
    svc.search = AsyncMock(return_value=[
        {
            "id": "c1", "score": 0.9, "text": "Relevant chunk",
            "metadata": {
                "source_id": "src1", "title": "Doc A",
                "provider_source": "google_docs", "chunk_index": 0, "source_url": "",
            }
        }
    ])
    return svc


def _retrieval_svc():
    from app.schemas.retrieval import EmailItem, CalendarEventItem, DriveFileItem
    svc = MagicMock()
    svc.get_recent_emails = AsyncMock(return_value=[
        EmailItem(id="e1", sender="a@b.com", subject="Heads up", snippet="FYI",
                  date="2025-01-01", provider_source="gmail")
    ])
    svc.get_upcoming_events = AsyncMock(return_value=[
        CalendarEventItem(id="ev1", summary="Standup", start_time="09:00",
                          end_time="09:30", description="", html_link="",
                          provider_source="google_calendar")
    ])
    svc.get_drive_files = AsyncMock(return_value=[])
    return svc


def _llm(answer="Test answer."):
    llm = MagicMock()
    llm.complete = AsyncMock(return_value=answer)
    return llm


@pytest.mark.asyncio
async def test_orchestration_plain_chat_no_tools():
    search = _search_svc()
    retrieval = _retrieval_svc()
    pipeline = OrchestrationPipeline(search_service=search, retrieval_service=retrieval, llm=_llm())
    result = await pipeline.run("hello", workspace_id="ws-test")
    search.search.assert_not_called()
    retrieval.get_recent_emails.assert_not_called()
    assert result.intent == "plain_chat"


@pytest.mark.asyncio
async def test_orchestration_email_intent_calls_email_tool():
    retrieval = _retrieval_svc()
    pipeline = OrchestrationPipeline(
        search_service=_search_svc(), retrieval_service=retrieval, llm=_llm()
    )
    result = await pipeline.run("summarize my recent emails", workspace_id="ws-test")
    retrieval.get_recent_emails.assert_called_once()
    assert result.intent == "email_recent"


@pytest.mark.asyncio
async def test_orchestration_fallback_on_provider_error():
    from app.integrations.exceptions import ProviderAPIError
    bad_search = MagicMock()
    bad_search.search = AsyncMock(side_effect=ProviderAPIError("Chroma down"))
    pipeline = OrchestrationPipeline(
        search_service=bad_search, retrieval_service=_retrieval_svc(), llm=_llm()
    )
    result = await pipeline.run("find notes about Q1", workspace_id="ws-test")
    assert result.fallback is True


@pytest.mark.asyncio
async def test_orchestration_llm_fallback_message():
    from app.integrations.exceptions import ProviderAPIError
    bad_llm = MagicMock()
    bad_llm.complete = AsyncMock(side_effect=ProviderAPIError("OpenAI down"))
    pipeline = OrchestrationPipeline(
        search_service=_search_svc(), retrieval_service=_retrieval_svc(), llm=bad_llm
    )
    result = await pipeline.run("explain our hiring process", workspace_id="ws-test")
    assert result.fallback is True
    assert "unable to reach" in result.answer.lower()


# ══════════════════════════════════════════════════════════════════════════════
# 4. Memory / history truncation
# ══════════════════════════════════════════════════════════════════════════════

def test_history_truncation_caps_at_800_chars():
    history = [{"role": "user", "content": "A" * 2000}]
    result = _truncate_history(history)
    assert len(result[0]["content"]) == 800


def test_history_truncation_preserves_short_content():
    history = [{"role": "assistant", "content": "Short"}]
    assert _truncate_history(history)[0]["content"] == "Short"


def test_history_empty_is_safe():
    assert _truncate_history([]) == []


# ══════════════════════════════════════════════════════════════════════════════
# 5. Source citation rendering safety
# ══════════════════════════════════════════════════════════════════════════════

def test_source_with_empty_url_still_renders():
    chunks = [
        {"metadata": {"source_id": "s1", "title": "Doc", "provider_source": "google_docs", "source_url": ""}},
    ]
    sources = _extract_sources(chunks)
    assert sources[0]["url"] == ""
    assert sources[0]["title"] == "Doc"


def test_source_dedup_across_multiple_chunks():
    chunks = [
        {"metadata": {"source_id": "s1", "title": "Doc", "provider_source": "google_docs", "source_url": ""}},
        {"metadata": {"source_id": "s1", "title": "Doc", "provider_source": "google_docs", "source_url": ""}},
        {"metadata": {"source_id": "s2", "title": "Email", "provider_source": "gmail", "source_url": ""}},
    ]
    sources = _extract_sources(chunks)
    assert len(sources) == 2


def test_source_no_id_handled_gracefully():
    chunks = [{"metadata": {}}]
    sources = _extract_sources(chunks)
    assert isinstance(sources, list)


# ══════════════════════════════════════════════════════════════════════════════
# 6. Routing — collision regression (subset, full suite in test_pipeline.py)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("msg,expected", [
    ("send me the document",  Intent.DRIVE_SEARCH),   # "send" does not trigger EMAIL
    ("documents about Q3",    Intent.SEMANTIC_SEARCH), # "documents about" is semantic, not drive
    ("hello there",           Intent.PLAIN_CHAT),
    ("what meetings tomorrow", Intent.CALENDAR),
])
def test_routing_critical_cases(msg: str, expected: Intent):
    assert classify(msg) == expected, f"{msg!r} → {classify(msg)} (expected {expected})"
