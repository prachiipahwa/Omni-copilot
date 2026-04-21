"""
Orchestration pipeline — the single composition point for a chat turn.

Responsibilities:
1. Classify intent
2. Select and execute tool(s) — each tool is independently guarded
3. Assemble grounded context
4. Call LLM with context + windowed history
5. Return structured ChatTurnResult

Stateless: holds no per-request state between calls.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.orchestration.router import Intent, classify
from app.orchestration.llm import LLMAdapter
from app.orchestration.tools import (
    ToolResult,
    tool_semantic_search,
    tool_email_recent,
    tool_calendar_upcoming,
    tool_drive_search,
)
from app.services.search import SemanticSearchService
from app.services.retrieval import RetrievalService
from app.integrations.exceptions import ProviderAPIError

logger = structlog.get_logger(__name__)

# Maximum individual history message content length (chars).
# Prevents one huge pasted document in an earlier turn from blowing up context.
_MAX_HISTORY_MSG_CHARS = 800


@dataclass
class ChatTurnResult:
    answer: str
    intent: str
    tools_used: list[str] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
    fallback: bool = False
    latency_ms: float = 0.0


def _truncate_history(history: list[dict[str, str]]) -> list[dict[str, str]]:
    """Cap each history message to avoid context explosion from long earlier turns."""
    return [
        {"role": h["role"], "content": h["content"][:_MAX_HISTORY_MSG_CHARS]}
        for h in history
    ]


class OrchestrationPipeline:
    """
    Stateless per-request pipeline. All dependencies injected.
    """

    def __init__(
        self,
        search_service: SemanticSearchService,
        retrieval_service: RetrievalService,
        llm: LLMAdapter | None = None,
    ):
        self.search_service = search_service
        self.retrieval_service = retrieval_service
        self.llm = llm or LLMAdapter()

    async def run(
        self,
        message: str,
        workspace_id: str,
        history: list[dict[str, str]] | None = None,
    ) -> ChatTurnResult:
        t0 = time.monotonic()
        intent = classify(message)
        logger.info("chat_intent_classified", intent=intent.value, workspace_id=workspace_id)

        # ── Tool execution — each path is independently guarded ────────────────
        primary_result: ToolResult | None = None
        augment_result: ToolResult | None = None
        fallback = False

        # ── SEMANTIC_SEARCH and GROUNDED_ANSWER — single code path ────────────
        if intent in (Intent.SEMANTIC_SEARCH, Intent.GROUNDED_ANSWER):
            primary_result = await self._safe_tool(
                tool_semantic_search(
                    query=message,
                    workspace_id=workspace_id,
                    search_service=self.search_service,
                ),
                "semantic_search",
            )

        # ── EMAIL_RECENT — primary retrieval + optional semantic augment ───────
        elif intent == Intent.EMAIL_RECENT:
            primary_result = await self._safe_tool(
                tool_email_recent(
                    workspace_id=workspace_id,
                    retrieval_service=self.retrieval_service,
                ),
                "email_recent",
            )
            # Augment independently — failure does not affect primary result
            augment_result = await self._safe_tool(
                tool_semantic_search(
                    query=message,
                    workspace_id=workspace_id,
                    search_service=self.search_service,
                    k=5,
                ),
                "semantic_search_augment",
            )

        # ── CALENDAR ──────────────────────────────────────────────────────────
        elif intent == Intent.CALENDAR:
            primary_result = await self._safe_tool(
                tool_calendar_upcoming(
                    workspace_id=workspace_id,
                    retrieval_service=self.retrieval_service,
                ),
                "calendar_upcoming",
            )

        # ── DRIVE_SEARCH — primary listing + optional semantic augment ─────────
        elif intent == Intent.DRIVE_SEARCH:
            primary_result = await self._safe_tool(
                tool_drive_search(
                    workspace_id=workspace_id,
                    retrieval_service=self.retrieval_service,
                ),
                "drive_search",
            )
            augment_result = await self._safe_tool(
                tool_semantic_search(
                    query=message,
                    workspace_id=workspace_id,
                    search_service=self.search_service,
                    k=5,
                ),
                "semantic_search_augment",
            )

        # PLAIN_CHAT: no tools, direct LLM

        # ── Merge primary + augment results ────────────────────────────────────
        context, sources, tools_used = self._merge_results(primary_result, augment_result)
        if primary_result and not primary_result.success:
            fallback = True

        # ── LLM call ───────────────────────────────────────────────────────────
        safe_history = _truncate_history(history or [])
        try:
            answer = await self.llm.complete(
                user_message=message,
                context=context,
                history=safe_history,
            )
        except ProviderAPIError as e:
            logger.error("llm_call_failed", error=str(e))
            answer = (
                "I'm unable to reach the AI provider right now. "
                "Please try again in a moment."
            )
            fallback = True

        latency_ms = round((time.monotonic() - t0) * 1000, 1)
        logger.info(
            "chat_turn_complete",
            intent=intent.value,
            tools=tools_used,
            sources=len(sources),
            fallback=fallback,
            latency_ms=latency_ms,
        )

        return ChatTurnResult(
            answer=answer,
            intent=intent.value,
            tools_used=tools_used,
            sources=sources,
            fallback=fallback,
            latency_ms=latency_ms,
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    async def _safe_tool(coro: Any, label: str) -> ToolResult:
        """
        Wraps a tool coroutine so that any exception — including those that
        escaped the tool's own handler — is always caught and returned as a
        failed ToolResult.  This prevents one tool's error from aborting the
        entire turn.
        """
        try:
            result = await coro
            return result
        except Exception as e:
            logger.warning("tool_uncaught_exception", tool=label, error=str(e))
            return ToolResult(tool_name=label, success=False, error=str(e))

    @staticmethod
    def _merge_results(
        primary: ToolResult | None,
        augment: ToolResult | None,
    ) -> tuple[str, list[dict[str, Any]], list[str]]:
        """
        Combine primary and augment into a single context block.
        Augment is appended only if it succeeded AND contains data.
        Sources are deduplicated by id.
        """
        parts: list[str] = []
        all_sources: list[dict[str, Any]] = []
        seen_source_ids: set[str] = set()
        tools_used: list[str] = []

        for result in (primary, augment):
            if result is None or not result.success or not result.data:
                continue
            parts.append(result.data)
            tools_used.append(result.tool_name)
            for s in result.sources or []:
                sid = s.get("id", "")
                if sid not in seen_source_ids:
                    seen_source_ids.add(sid)
                    all_sources.append(s)

        return "\n\n".join(parts), all_sources, tools_used
