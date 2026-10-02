"""Deep Research Agent - Multi-hop retrieval agent with cited reports.

Ported from OpenJARVIS (Stanford Hazy Research).
Searches across sources and produces narrative answers with inline citations.
"""

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class DeepResearchAgent:
    def __init__(self, max_turns: int = 8):
        self.max_turns = max_turns
        self._sources: list[dict] = []

    async def research(self, query: str, llm_call=None, search_fn=None) -> dict[str, Any]:
        self._sources = []
        context_parts = []
        turn = 0

        system_prompt = self._build_system_prompt()

        if search_fn:
            while turn < self.max_turns:
                turn += 1
                logger.info(f"Deep research turn {turn}/{self.max_turns}")

                search_query = query if turn == 1 else self._generate_followup(query, context_parts, llm_call)
                results = await search_fn(search_query)

                if isinstance(results, list):
                    for r in results:
                        source = {"title": r.get("title", ""), "snippet": r.get("content", ""), "turn": turn}
                        self._sources.append(source)
                        context_parts.append(f"[Source {len(self._sources)}] {r.get('title', 'Unknown')}: {r.get('content', '')[:500]}")
                elif isinstance(results, str):
                    self._sources.append({"title": "Search Result", "snippet": results, "turn": turn})
                    context_parts.append(results[:1000])

                if len(self._sources) >= self.max_turns * 2:
                    break

        synthesized = await self._synthesize(query, context_parts, llm_call)

        return {
            "report": synthesized,
            "sources": self._sources,
            "turns": turn,
            "generated_at": datetime.now().isoformat(),
        }

    async def _synthesize(self, query: str, context: list[str], llm_call) -> str:
        if not context:
            return "No sources found for the research query."

        if llm_call is None:
            combined = "\n\n".join(context[:5])
            return f"Research findings for: {query}\n\n{combined}\n\nSources consulted: {len(self._sources)}"

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {
                "role": "user",
                "content": f"Query: {query}\n\nCollected evidence:\n\n" + "\n---\n".join(context[:10]) + "\n\nSynthesize a comprehensive answer with inline citations [Source N].",
            },
        ]

        response = await llm_call(messages)
        return response.get("content", "Unable to synthesize research findings.")

    def _generate_followup(self, original_query: str, context: list[str], llm_call) -> str:
        if llm_call is None:
            return original_query
        return original_query

    def _build_system_prompt(self) -> str:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        return f"""You are JARVIS Deep Research, a multi-hop research agent.
Current time: {now}

Your task:
1. Search across available data sources thoroughly
2. Cross-reference findings from multiple sources
3. Synthesize a comprehensive narrative with inline citations
4. Flag conflicting information or gaps in coverage

Always cite sources as [Source N] where N is the source number.
Be thorough but concise. Prioritize accuracy over completeness."""
