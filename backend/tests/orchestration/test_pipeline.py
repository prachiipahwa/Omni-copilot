"""
Tests for Phase 4D orchestration layer — hardened suite.

All tests are fully offline — no OpenAI calls, no DB, no Chroma.
Covers: routing accuracy, collision detection, pipeline tool selection,
partial failures, history truncation, source formatting, and merge logic.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.orchestration.router import Intent, classify
from app.orchestration.pipeline import OrchestrationPipeline, ChatTurnResult, _truncate_history
from app.orchestration.tools import ToolResult, _extract_sources


# ══════════════════════════════════════════════════════════════════════════════
# 1. Routing / intent classification — correctness
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("msg,expected", [
    # Email
    ("summarize my recent emails",       Intent.EMAIL_RECENT),
    ("what emails did I get?",           Intent.EMAIL_RECENT),
    ("show me my inbox",                 Intent.EMAIL_RECENT),
    ("check my gmail",                   Intent.EMAIL_RECENT),
    ("any unread messages?",             Intent.EMAIL_RECENT),
    # Calendar
    ("what meetings do I have tomorrow?", Intent.CALENDAR),
    ("any events this week?",            Intent.CALENDAR),
    ("show my schedule",                 Intent.CALENDAR),
    ("what's on my calendar?",           Intent.CALENDAR),
    # Drive
    ("list my drive files",              Intent.DRIVE_SEARCH),
    ("show me my spreadsheets",          Intent.DRIVE_SEARCH),
    ("find files in my drive",           Intent.DRIVE_SEARCH),
    # Semantic search
    ("find notes about the Q1 roadmap",  Intent.SEMANTIC_SEARCH),
    ("search docs about hiring process", Intent.SEMANTIC_SEARCH),
    ("what did Alice mention about budget?", Intent.SEMANTIC_SEARCH),
    # Grounded answer
    ("what is the company refund policy?", Intent.GROUNDED_ANSWER),
    ("explain the onboarding process",   Intent.GROUNDED_ANSWER),
    ("how do I request time off?",       Intent.GROUNDED_ANSWER),
    # Plain chat
    ("hi there",    Intent.PLAIN_CHAT),
    ("hello",       Intent.PLAIN_CHAT),
    ("thanks",      Intent.PLAIN_CHAT),
    ("ok got it",   Intent.PLAIN_CHAT),
    ("sounds good", Intent.PLAIN_CHAT),
])
def test_intent_classification(msg: str, expected: Intent):
    assert classify(msg) == expected, f"classify({msg!r}) should be {expected}, was {classify(msg)}"


# ── Collision / false-positive regression tests ───────────────────────────────

@pytest.mark.parametrize("msg,must_not_be", [
    # "send me" must NOT trigger EMAIL_RECENT (was caused by \bsent\b)
    ("send me the document",      Intent.EMAIL_RECENT),
    # "documents about X" should be SEMANTIC_SEARCH, not DRIVE_SEARCH
    ("documents about our Q3 goals", Intent.DRIVE_SEARCH),
    # "today" alone should not trigger CALENDAR (too ambiguous)
    ("what about today",          Intent.CALENDAR),
    # short unknown message should not be GROUNDED_ANSWER
    ("ok",                        Intent.GROUNDED_ANSWER),
])
def test_no_routing_collision(msg: str, must_not_be: Intent):
    result = classify(msg)
    assert result != must_not_be, (
        f"classify({msg!r}) = {result} — expected NOT to be {must_not_be}"
    )


def test_classify_caches_result():
    """LRU cache should return exact same Intent object for identical input."""
    r1 = classify("find my notes on budgeting")
    r2 = classify("find my notes on budgeting")
    assert r1 is r2


def test_classify_empty_string():
    assert classify("") == Intent.PLAIN_CHAT


# ══════════════════════════════════════════════════════════════════════════════
# 2. Fixture factories
# ══════════════════════════════════════════════════════════════════════════════

def _mock_search_service():
    svc = MagicMock()
    svc.search = AsyncMock(return_value=[
        {
            "id": "c1", "score": 0.85, "text": "Relevant chunk about Q1.",
            "metadata": {
                "source_id": "src1", "title": "Q1 Report",
                "provider_source": "google_docs", "chunk_index": 0, "source_url": "",
            }
        }
    ])
    return svc


def _mock_retrieval_service():
    from app.schemas.retrieval import EmailItem, CalendarEventItem, DriveFileItem
    svc = MagicMock()
    svc.get_recent_emails = AsyncMock(return_value=[
        EmailItem(id="e1", sender="boss@co.com", subject="Budget Q1",
                  snippet="Numbers attached", date="2025-01-10", provider_source="gmail")
    ])
    svc.get_upcoming_events = AsyncMock(return_value=[
        CalendarEventItem(id="ev1", summary="Weekly Standup", start_time="09:00",
                          end_time="09:30", description="Team sync", html_link="",
                          provider_source="google_calendar")
    ])
    svc.get_drive_files = AsyncMock(return_value=[
        DriveFileItem(id="f1", name="Budget.xlsx", mime_type="application/vnd.openxmlformats",
                      web_view_link="https://drive.google.com/f1",
                      provider_source="google_drive", updated_at=None)
    ])
    return svc


def _mock_llm(answer: str = "Here is your answer."):
    llm = MagicMock()
    llm.complete = AsyncMock(return_value=answer)
    return llm


# ══════════════════════════════════════════════════════════════════════════════
# 3. Tool selection — correct tool called for each intent
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_email_intent_calls_email_tool():
    retrieval = _mock_retrieval_service()
    pipeline = OrchestrationPipeline(
        search_service=_mock_search_service(),
        retrieval_service=retrieval,
        llm=_mock_llm(),
    )
    result = await pipeline.run("show my recent emails", workspace_id="ws-1")
    retrieval.get_recent_emails.assert_called_once()
    assert result.intent == Intent.EMAIL_RECENT.value


@pytest.mark.asyncio
async def test_calendar_intent_calls_calendar_tool():
    retrieval = _mock_retrieval_service()
    pipeline = OrchestrationPipeline(
        search_service=_mock_search_service(),
        retrieval_service=retrieval,
        llm=_mock_llm(),
    )
    result = await pipeline.run("what meetings do I have tomorrow?", workspace_id="ws-1")
    retrieval.get_upcoming_events.assert_called_once()
    assert result.intent == Intent.CALENDAR.value


@pytest.mark.asyncio
async def test_drive_intent_calls_drive_tool():
    retrieval = _mock_retrieval_service()
    pipeline = OrchestrationPipeline(
        search_service=_mock_search_service(),
        retrieval_service=retrieval,
        llm=_mock_llm(),
    )
    result = await pipeline.run("list my drive files", workspace_id="ws-1")
    retrieval.get_drive_files.assert_called_once()
    assert result.intent == Intent.DRIVE_SEARCH.value


@pytest.mark.asyncio
async def test_grounded_intent_calls_semantic_search():
    search = _mock_search_service()
    pipeline = OrchestrationPipeline(
        search_service=search,
        retrieval_service=_mock_retrieval_service(),
        llm=_mock_llm(),
    )
    result = await pipeline.run("what is the refund policy?", workspace_id="ws-1")
    search.search.assert_called()
    assert result.intent == Intent.GROUNDED_ANSWER.value


@pytest.mark.asyncio
async def test_plain_chat_calls_no_tools():
    retrieval = _mock_retrieval_service()
    search = _mock_search_service()
    pipeline = OrchestrationPipeline(
        search_service=search,
        retrieval_service=retrieval,
        llm=_mock_llm(),
    )
    await pipeline.run("hello", workspace_id="ws-1")
    retrieval.get_recent_emails.assert_not_called()
    retrieval.get_upcoming_events.assert_not_called()
    search.search.assert_not_called()


# ══════════════════════════════════════════════════════════════════════════════
# 4. Partial tool failure — graceful degradation
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_primary_tool_failure_sets_fallback():
    from app.integrations.exceptions import ProviderAPIError
    failing_retrieval = _mock_retrieval_service()
    failing_retrieval.get_recent_emails = AsyncMock(side_effect=ProviderAPIError("Gmail down"))

    pipeline = OrchestrationPipeline(
        search_service=_mock_search_service(),
        retrieval_service=failing_retrieval,
        llm=_mock_llm(),
    )
    result = await pipeline.run("show my recent emails", workspace_id="ws-1")
    # Pipeline still returns an answer (LLM called without context)
    assert isinstance(result, ChatTurnResult)
    assert result.fallback is True


@pytest.mark.asyncio
async def test_augment_failure_does_not_kill_primary():
    """If semantic augment fails, primary email result should still be used."""
    failing_search = MagicMock()
    failing_search.search = AsyncMock(side_effect=Exception("Chroma down"))

    retrieval = _mock_retrieval_service()
    pipeline = OrchestrationPipeline(
        search_service=failing_search,
        retrieval_service=retrieval,
        llm=_mock_llm(),
    )
    result = await pipeline.run("show my recent emails", workspace_id="ws-1")
    # Answer delivered — primary email tool succeeded
    assert result.answer == "Here is your answer."
    # email_recent tool should still appear in tools_used
    assert "email_recent" in result.tools_used


@pytest.mark.asyncio
async def test_llm_failure_returns_graceful_message():
    from app.integrations.exceptions import ProviderAPIError
    failing_llm = MagicMock()
    failing_llm.complete = AsyncMock(side_effect=ProviderAPIError("OpenAI down"))

    pipeline = OrchestrationPipeline(
        search_service=_mock_search_service(),
        retrieval_service=_mock_retrieval_service(),
        llm=failing_llm,
    )
    result = await pipeline.run("what is the refund policy?", workspace_id="ws-1")
    assert result.fallback is True
    assert "unable to reach" in result.answer.lower()


# ══════════════════════════════════════════════════════════════════════════════
# 5. History truncation
# ══════════════════════════════════════════════════════════════════════════════

def test_history_truncation_caps_content_length():
    long_content = "A" * 2000
    history = [{"role": "user", "content": long_content}]
    result = _truncate_history(history)
    assert len(result[0]["content"]) == 800


def test_history_truncation_preserves_role():
    history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
    ]
    result = _truncate_history(history)
    assert result[0]["role"] == "user"
    assert result[1]["role"] == "assistant"


def test_history_truncation_short_content_unchanged():
    history = [{"role": "user", "content": "Short message"}]
    result = _truncate_history(history)
    assert result[0]["content"] == "Short message"


# ══════════════════════════════════════════════════════════════════════════════
# 6. Source deduplication and formatting
# ══════════════════════════════════════════════════════════════════════════════

def test_source_extraction_deduplicates_by_id():
    chunks = [
        {"metadata": {"source_id": "s1", "title": "Doc A", "provider_source": "google_docs", "source_url": ""}},
        {"metadata": {"source_id": "s1", "title": "Doc A", "provider_source": "google_docs", "source_url": ""}},
        {"metadata": {"source_id": "s2", "title": "Email B", "provider_source": "gmail", "source_url": ""}},
    ]
    sources = _extract_sources(chunks)
    assert len(sources) == 2
    assert [s["id"] for s in sources].count("s1") == 1


def test_source_extraction_includes_url():
    chunks = [
        {"metadata": {"source_id": "s1", "title": "My Doc", "provider_source": "google_docs",
                      "source_url": "https://docs.google.com/abc"}},
    ]
    sources = _extract_sources(chunks)
    assert sources[0]["url"] == "https://docs.google.com/abc"


def test_source_extraction_empty_source_id_handled():
    chunks = [{"metadata": {}}]
    sources = _extract_sources(chunks)
    # Empty source_id is valid — should not crash
    assert isinstance(sources, list)


# ══════════════════════════════════════════════════════════════════════════════
# 7. Merge results
# ══════════════════════════════════════════════════════════════════════════════

def test_merge_deduplicates_sources_across_tools():
    from app.orchestration.pipeline import OrchestrationPipeline
    primary = ToolResult(
        tool_name="email_recent", success=True,
        data="Email data",
        sources=[{"id": "s1", "title": "Email", "provider": "gmail", "url": ""}],
    )
    augment = ToolResult(
        tool_name="semantic_search", success=True,
        data="Semantic data",
        sources=[
            {"id": "s1", "title": "Email", "provider": "gmail", "url": ""},  # duplicate
            {"id": "s2", "title": "Doc B", "provider": "google_docs", "url": ""},
        ],
    )
    context, sources, tools = OrchestrationPipeline._merge_results(primary, augment)
    source_ids = [s["id"] for s in sources]
    assert source_ids.count("s1") == 1
    assert "s2" in source_ids
    assert len(tools) == 2


def test_merge_failed_primary_excluded():
    from app.orchestration.pipeline import OrchestrationPipeline
    failed = ToolResult(tool_name="email_recent", success=False, error="timeout")
    augment = ToolResult(
        tool_name="semantic_search", success=True, data="Some context", sources=[],
    )
    context, sources, tools = OrchestrationPipeline._merge_results(failed, augment)
    assert "email_recent" not in tools
    assert "semantic_search" in tools
    assert context == "Some context"
