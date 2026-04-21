"""
Intent classification for inbound user messages.

Uses a fast, deterministic rule-based classifier.  No LLM call needed for
routing — this keeps latency low and routing behaviour predictable/testable.

Design rules:
- More specific patterns must appear BEFORE more general ones.
- Each pattern is anchored with \\b to prevent substring collisions.
- Plain-chat check runs before tool routing — it is always the cheapest path.
- Unknown short messages fall to PLAIN_CHAT; longer unknown messages fall to
  GROUNDED_ANSWER so we always attempt a RAG answer rather than staying silent.

Intent taxonomy:
  SEMANTIC_SEARCH  — explicit "search/find/notes about <topic>"
  EMAIL_RECENT     — inbox / mail / unread
  CALENDAR         — meetings / events / schedule
  DRIVE_SEARCH     — files / drive / spreadsheets
  GROUNDED_ANSWER  — general question requiring RAG context
  PLAIN_CHAT       — greeting / chit-chat / capability question
"""
from __future__ import annotations

import re
from enum import Enum
from functools import lru_cache


class Intent(str, Enum):
    SEMANTIC_SEARCH = "semantic_search"
    EMAIL_RECENT    = "email_recent"
    CALENDAR        = "calendar"
    DRIVE_SEARCH    = "drive_search"
    GROUNDED_ANSWER = "grounded_answer"
    PLAIN_CHAT      = "plain_chat"


# ── Compiled rule table ────────────────────────────────────────────────────────
# Order matters strictly: first full-pattern match wins.
# Rules are compiled once at import time.

_RAW_RULES: list[tuple[Intent, list[str]]] = [
    # ── Email — must come before CALENDAR to win on "emails today"
    (Intent.EMAIL_RECENT, [
        r"\bemail(?:s)?\b",
        r"\binbox\b",
        r"\bunread\b",
        r"\bmail\b",
        r"\bgmail\b",
        r"\bsent\s+(?:me|to|an)\b",   # "sent me", "sent to" — NOT "send me"
        r"\breply\b",
        r"\bthread\b",
    ]),

    # ── Calendar — "today" and "tomorrow" are calendar keywords but only when
    #    paired with meeting/event/schedule context or standalone schedules.
    #    "today" alone is too ambiguous — excluded.
    (Intent.CALENDAR, [
        r"\bmeeting(?:s)?\b",
        r"\bcalendar\b",
        r"\bschedule\b",
        r"\bevent(?:s)?\b",
        r"\bappointment(?:s)?\b",
        r"\btomorrow\b",               # "what's tomorrow" implies calendar
        r"\bstandup\b",
        r"\breminder\b",
        r"\bblock(?:ed)?\s+time\b",
    ]),

    # ── Drive — explicit drive/file keywords only; "document" alone is too
    #    broad (users say "find documents about X" meaning semantic search).
    (Intent.DRIVE_SEARCH, [
        r"\bdrive\b",
        r"\bspreadsheet(?:s)?\b",
        r"\bslide(?:s|deck)?\b",
        r"\bpdf\b",
        r"\bshared\s+file(?:s)?\b",
        r"\bmy\s+file(?:s)?\b",
        r"\blist\s+(?:my\s+)?file(?:s)?\b",
    ]),

    # ── Semantic search — explicit search/find/notes keywords
    (Intent.SEMANTIC_SEARCH, [
        r"\bsearch\b",
        r"\bfind\b",
        r"\bnotes?\s+(?:about|on|regarding)\b",
        r"\bdocs?\s+(?:about|on|regarding)\b",
        r"\bdocuments?\s+(?:about|on)\b",
        r"\bwhat\b.*\bsaid\b",
        r"\bmentioned\b",
        r"\brecord(?:s|ed)?\s+(?:about|of)\b",
    ]),

    # ── Grounded answer — requires knowledge retrieval but no specific tool
    (Intent.GROUNDED_ANSWER, [
        r"\bsummariz",
        r"\bsummary\b",
        r"\bexplain\b",
        r"\btell\s+me\s+about\b",
        r"\bwhat\s+is\b",
        r"\bwhat\s+are\b",
        r"\bwho\s+is\b",
        r"\bhow\s+(?:to|do|can|does)\b",
        r"\bwhy\s+(?:did|does|is|are)\b",
        r"\bwhat\s+(?:was|were|happened)\b",
    ]),
]

# Compiled once at module load
_RULES: list[tuple[Intent, list[re.Pattern]]] = [
    (intent, [re.compile(p, re.IGNORECASE) for p in patterns])
    for intent, patterns in _RAW_RULES
]

_PLAIN_CHAT_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in [
        r"^(hi|hello|hey|good\s+(?:morning|afternoon|evening)|howdy|sup)\b",
        r"^(thanks|thank\s+you|bye|goodbye|see\s+you)\b",
        r"^(how\s+are\s+you|what\s+can\s+you\s+do|what\s+are\s+you)\b",
        r"^(ok|okay|got\s+it|sure|sounds\s+good|nice|great|perfect|cool)\b",
    ]
]


@lru_cache(maxsize=512)
def classify(message: str) -> Intent:
    """
    Classify a user message into an Intent.

    Deterministic — never calls any external service.
    Result is cached (lru_cache) so repeated identical messages cost nothing.
    """
    text = message.strip()
    if not text:
        return Intent.PLAIN_CHAT

    # 1. Plain chat first — cheapest check, most specific
    for pattern in _PLAIN_CHAT_PATTERNS:
        if pattern.search(text):
            return Intent.PLAIN_CHAT

    # 2. Ordered rule matching
    for intent, patterns in _RULES:
        for pattern in patterns:
            if pattern.search(text):
                return intent

    # 3. Default: question mark or long message → attempt grounded RAG
    #    Short (< 4 tokens) unmatched messages → plain chat
    word_count = len(text.split())
    if "?" in text or word_count >= 6:
        return Intent.GROUNDED_ANSWER

    return Intent.PLAIN_CHAT
