"""
Orchestration tool wrappers.

Each tool is a thin async function that calls one existing service,
handles timeout, and returns a ToolResult.  Tools never call each other.
The pipeline composes them.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.services.search import SemanticSearchService
from app.services.context import ContextAssemblyService
from app.services.retrieval import RetrievalService

logger = structlog.get_logger(__name__)

TOOL_TIMEOUT_SECONDS = 8.0  # hard ceiling per individual tool call


@dataclass
class ToolResult:
    tool_name: str
    success: bool
    data: Any = None
    error: str | None = None
    sources: list[dict[str, Any]] = field(default_factory=list)


# ── Helper ─────────────────────────────────────────────────────────────────────

async def _with_timeout(coro, tool_name: str) -> Any:
    try:
        return await asyncio.wait_for(coro, timeout=TOOL_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        logger.warning("tool_timeout", tool=tool_name, timeout_s=TOOL_TIMEOUT_SECONDS)
        raise TimeoutError(f"Tool '{tool_name}' timed out after {TOOL_TIMEOUT_SECONDS}s")


# ── Tools ──────────────────────────────────────────────────────────────────────

async def tool_semantic_search(
    query: str,
    workspace_id: str,
    search_service: SemanticSearchService,
    k: int = 10,
) -> ToolResult:
    try:
        results = await _with_timeout(
            search_service.search(query=query, workspace_id=workspace_id, k=k),
            "semantic_search",
        )
        assembler = ContextAssemblyService(max_tokens=2500)
        context = assembler.assemble(results)
        return ToolResult(
            tool_name="semantic_search",
            success=True,
            data=context,
            sources=_extract_sources(results),
        )
    except Exception as e:
        logger.warning("tool_semantic_search_failed", error=str(e))
        return ToolResult(tool_name="semantic_search", success=False, error=str(e))


async def tool_email_recent(
    workspace_id: str,
    retrieval_service: RetrievalService,
    max_results: int = 8,
) -> ToolResult:
    from uuid import UUID
    try:
        emails = await _with_timeout(
            retrieval_service.get_recent_emails(UUID(workspace_id), max_results=max_results),
            "email_recent",
        )
        lines = []
        sources = []
        for e in emails:
            snippet = f"From: {e.sender} | {e.date}\nSubject: {e.subject}\n{e.snippet}"
            lines.append(snippet)
            sources.append({"title": e.subject, "provider": "gmail", "id": e.id})
        return ToolResult(
            tool_name="email_recent",
            success=True,
            data="\n\n".join(lines),
            sources=sources,
        )
    except Exception as e:
        logger.warning("tool_email_recent_failed", error=str(e))
        return ToolResult(tool_name="email_recent", success=False, error=str(e))


async def tool_calendar_upcoming(
    workspace_id: str,
    retrieval_service: RetrievalService,
    max_results: int = 8,
) -> ToolResult:
    from uuid import UUID
    try:
        events = await _with_timeout(
            retrieval_service.get_upcoming_events(UUID(workspace_id), max_results=max_results),
            "calendar_upcoming",
        )
        lines = []
        sources = []
        for ev in events:
            line = f"{ev.summary} | {ev.start_time} → {ev.end_time}"
            if ev.description:
                line += f"\n{ev.description}"
            lines.append(line)
            sources.append({"title": ev.summary, "provider": "google_calendar", "id": ev.id})
        return ToolResult(
            tool_name="calendar_upcoming",
            success=True,
            data="\n\n".join(lines),
            sources=sources,
        )
    except Exception as e:
        logger.warning("tool_calendar_upcoming_failed", error=str(e))
        return ToolResult(tool_name="calendar_upcoming", success=False, error=str(e))


async def tool_drive_search(
    workspace_id: str,
    retrieval_service: RetrievalService,
    max_results: int = 6,
) -> ToolResult:
    from uuid import UUID
    try:
        files = await _with_timeout(
            retrieval_service.get_drive_files(UUID(workspace_id), max_results=max_results),
            "drive_search",
        )
        lines = []
        sources = []
        for f in files:
            lines.append(f"[{f.mime_type}] {f.name} — {f.web_view_link or 'no link'}")
            sources.append({"title": f.name, "provider": "google_drive", "id": f.id, "url": f.web_view_link or ""})
        return ToolResult(
            tool_name="drive_search",
            success=True,
            data="\n".join(lines),
            sources=sources,
        )
    except Exception as e:
        logger.warning("tool_drive_search_failed", error=str(e))
        return ToolResult(tool_name="drive_search", success=False, error=str(e))


# ── Source extraction helper ───────────────────────────────────────────────────

def _extract_sources(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """De-duplicates and formats source citations from vector chunk metadata."""
    seen: set[str] = set()
    sources = []
    for c in chunks:
        meta = c.get("metadata", {})
        src_id = meta.get("source_id", "")
        if src_id in seen:
            continue
        seen.add(src_id)
        sources.append({
            "id": src_id,
            "title": meta.get("title", "Untitled"),
            "provider": meta.get("provider_source", "unknown"),
            "url": meta.get("source_url", ""),
        })
    return sources
