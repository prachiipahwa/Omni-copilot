from typing import List, Dict, Any
import tiktoken


class ContextAssemblyService:
    """
    Converts ranked vector chunks into a structured, token-budget-aware
    context string suitable for injection into an LLM system prompt.

    Design principles:
    - Group chunks by source for coherent reading
    - Best-scoring sources appear first
    - Strict token budget enforcement — never exceed max_tokens
    - Metadata headers for LLM grounding (provider, title, link)
    """

    def __init__(self, max_tokens: int = 3000, model: str = "gpt-4o"):
        self.max_tokens = max_tokens
        self.encoder = tiktoken.encoding_for_model(model)

    def _count_tokens(self, text: str) -> int:
        return len(self.encoder.encode(text))

    def assemble(self, chunks: List[Dict[str, Any]]) -> str:
        if not chunks:
            return ""

        # ── 1. Group by source_id ──────────────────────────
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        source_best_score: Dict[str, float] = {}
        for c in chunks:
            meta = c.get("metadata", {})
            src_id = meta.get("source_id", "unknown")
            grouped.setdefault(src_id, []).append(c)
            score = c.get("score", 0.0)
            if score > source_best_score.get(src_id, 0.0):
                source_best_score[src_id] = score

        # ── 2. Order sources by best chunk score (desc) ────
        sorted_source_ids = sorted(
            grouped.keys(),
            key=lambda sid: source_best_score.get(sid, 0.0),
            reverse=True,
        )

        # ── 3. Assemble with strict token budget ──────────
        assembled_parts: List[str] = []
        budget_remaining = self.max_tokens

        for src_id in sorted_source_ids:
            doc_chunks = grouped[src_id]
            meta = doc_chunks[0].get("metadata", {})
            title = meta.get("title", "Untitled")
            provider = meta.get("provider_source", "knowledge_base").upper()
            url = meta.get("source_url", "")
            url_suffix = f" | {url}" if url else ""

            header = f"--- [{provider}] {title}{url_suffix} ---\n"
            header_cost = self._count_tokens(header)

            if header_cost >= budget_remaining:
                break  # Can't even fit the header

            # Sort chunks within this source by chunk_index
            doc_chunks.sort(key=lambda x: x.get("metadata", {}).get("chunk_index", 0))

            body_lines: List[str] = []
            body_cost = 0
            for c in doc_chunks:
                line = c.get("text", "").strip()
                if not line:
                    continue
                line_cost = self._count_tokens(line) + 1  # +1 for newline
                if header_cost + body_cost + line_cost > budget_remaining:
                    break
                body_lines.append(line)
                body_cost += line_cost

            if not body_lines:
                continue  # Nothing fit; skip this source entirely

            block = header + "\n".join(body_lines) + "\n"
            assembled_parts.append(block)
            budget_remaining -= (header_cost + body_cost)

            if budget_remaining <= 0:
                break

        return "\n".join(assembled_parts)
