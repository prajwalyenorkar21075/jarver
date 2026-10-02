"""VedicKnowledgeAgent — specialized agent for Vedic & Indic knowledge."""

import logging
from dataclasses import dataclass
from typing import Optional

from .base import (
    VedicKnowledgeBase,
    VedicKnowledgeEntry,
    QueryResult,
    ExplainResult,
    DifficultyLevel,
    Language,
    VedicDomain,
    SourceType,
)
from .engine import VedicKnowledgeEngine
from .rag.retriever import SemanticRetriever, HybridRetriever, RetrievalConfig
from .multilingual.processor import get_multilingual_processor, MultilingualQueryProcessor
from .web.search import get_web_search_client, WebSearchConfig, WebSearchClient
from .ingestion.ingester import CorpusManager

logger = logging.getLogger(__name__)


@dataclass
class AgentResponse:
    """Response from the VedicKnowledgeAgent."""
    answer: str
    sources: list[dict]
    query: str
    language: Language
    depth: str
    used_web_fallback: bool
    web_results: list[dict] = None
    concept_graph: dict = None


class VedicKnowledgeAgent:
    """
    Specialized agent for answering questions using the Vedic Knowledge Corpus.

    Priority 1: Local verified Vedic Knowledge Corpus
    Priority 2: Previously verified/indexed external sources
    Priority 3: Google/Web search when required information is unavailable locally
    """

    def __init__(
        self,
        knowledge_base: VedicKnowledgeBase,
        enable_web_fallback: bool = True,
        web_search_config: WebSearchConfig | None = None,
    ):
        self.kb = knowledge_base
        self.engine = VedicKnowledgeEngine(knowledge_base)
        self.retriever = SemanticRetriever(knowledge_base, RetrievalConfig())
        self.hybrid_retriever = HybridRetriever(knowledge_base)
        self.hybrid_retriever.enable_web_fallback(enable_web_fallback)

        self._multilingual = get_multilingual_processor()
        self._web_client: WebSearchClient | None = None
        self._web_config = web_search_config or WebSearchConfig()
        self._enable_web_fallback = enable_web_fallback

        self._corpus_manager = CorpusManager(knowledge_base)

        # Initialize retriever
        self.retriever.initialize()

        logger.info("[VEDIC_AGENT] VedicKnowledgeAgent initialized")

    async def answer(
        self,
        query: str,
        domain: str | VedicDomain | None = None,
        depth: str = "intermediate",
        language: Language = Language.ENGLISH,
        use_web_fallback: bool = True,
    ) -> AgentResponse:
        """Answer a question using the knowledge base with fallback."""
        # Process multilingual query
        detected_lang, english_query, sanskrit_terms = self._multilingual.process(query)
        effective_language = language if language != Language.ENGLISH else detected_lang

        # Step 1: Search local corpus
        retrieval_result, needs_web = self.hybrid_retriever.retrieve(
            english_query,
            domain=domain,
            limit=10,
            language=effective_language,
            use_web_fallback=use_web_fallback and self._enable_web_fallback,
        )

        # Step 2: Generate answer from local results
        if retrieval_result.entries:
            explanation = self.engine.explain(
                english_query,
                depth=depth,
                language=effective_language,
            )

            # Limit to entries we actually retrieved
            used_entries = [e for e in explanation.entries_used
                          if any(e == re.id for re in retrieval_result.entries)]

            answer = self._format_answer(
                explanation.explanation,
                retrieval_result.entries,
                english_query,
                effective_language,
                depth,
            )

            sources = self._format_sources(retrieval_result.entries)

            return AgentResponse(
                answer=answer,
                sources=sources,
                query=query,
                language=effective_language,
                depth=depth,
                used_web_fallback=False,
            )

        # Step 3: Web fallback if enabled and needed
        if (use_web_fallback and self._enable_web_fallback and
            (needs_web or not retrieval_result.entries)):

            web_results = await self._search_web(english_query, domain)
            if web_results:
                # Use web results to construct answer
                answer = self._format_web_answer(web_results, english_query, effective_language, depth)
                sources = self._format_web_sources(web_results)

                return AgentResponse(
                    answer=answer,
                    sources=sources,
                    query=query,
                    language=effective_language,
                    depth=depth,
                    used_web_fallback=True,
                    web_results=[r.to_dict() for r in web_results],
                )

        # Step 4: No results found
        suggestions = retrieval_result.suggestions
        if sanskrit_terms:
            suggestions.insert(0, f"Detected Sanskrit terms: {', '.join(sanskrit_terms)}")

        return AgentResponse(
            answer=f"No knowledge found for '{query}'.\n\nSuggestions:\n" + "\n".join(f"- {s}" for s in suggestions),
            sources=[],
            query=query,
            language=effective_language,
            depth=depth,
            used_web_fallback=False,
        )

    async def explain(
        self,
        topic: str,
        depth: str = "intermediate",
        language: Language = Language.ENGLISH,
    ) -> AgentResponse:
        """Get detailed explanation of a topic."""
        detected_lang, english_topic, sanskrit_terms = self._multilingual.process(topic)
        effective_language = language if language != Language.ENGLISH else detected_lang

        result = self.engine.explain(english_topic, depth=depth, language=effective_language)

        if result.entries_used:
            sources = []
            for entry_id in result.entries_used:
                entry = self.kb.get_entry(entry_id)
                if entry:
                    sources.append(self._format_source(entry))

            return AgentResponse(
                answer=result.explanation,
                sources=sources,
                query=topic,
                language=effective_language,
                depth=depth,
                used_web_fallback=False,
            )
        else:
            # Try web fallback
            if self._enable_web_fallback:
                web_results = await self._search_web(english_topic)
                if web_results:
                    answer = self._format_web_answer(web_results, english_topic, effective_language, depth)
                    return AgentResponse(
                        answer=answer,
                        sources=self._format_web_sources(web_results),
                        query=topic,
                        language=effective_language,
                        depth=depth,
                        used_web_fallback=True,
                        web_results=[r.to_dict() for r in web_results],
                    )

            return AgentResponse(
                answer=f"No knowledge found for '{topic}'.",
                sources=[],
                query=topic,
                language=effective_language,
                depth=depth,
                used_web_fallback=False,
            )

    async def compare(
        self,
        concept: str,
        domain1: str | VedicDomain,
        domain2: str | VedicDomain,
        language: Language = Language.ENGLISH,
    ) -> AgentResponse:
        """Compare a concept across two domains."""
        detected_lang, english_concept, _ = self._multilingual.process(concept)
        effective_language = language if language != Language.ENGLISH else detected_lang

        # Get results from both domains
        result1 = self.retriever.retrieve(english_concept, domain=domain1, limit=5, language=effective_language)
        result2 = self.retriever.retrieve(english_concept, domain=domain2, limit=5, language=effective_language)

        if not result1.entries and not result2.entries:
            return AgentResponse(
                answer=f"No knowledge found for '{concept}' in either domain.",
                sources=[],
                query=concept,
                language=effective_language,
                depth="comparison",
                used_web_fallback=False,
            )

        # Build comparison
        output = [f"# Comparison: {concept} in {domain1} vs {domain2}", ""]

        if result1.entries:
            output.append(f"## {domain1}")
            for entry in result1.entries[:3]:
                output.append(f"### {entry.title}")
                output.append(f"**Source:** {entry.source_metadata.source} ({entry.source_metadata.source_type.value})")
                if entry.source_metadata.chapter:
                    output.append(f"**Chapter:** {entry.source_metadata.chapter}")
                if entry.source_metadata.verse:
                    output.append(f"**Verse:** {entry.source_metadata.verse}")
                output.append(entry.content[:500] + "..." if len(entry.content) > 500 else entry.content)
                output.append("")

        if result2.entries:
            output.append(f"## {domain2}")
            for entry in result2.entries[:3]:
                output.append(f"### {entry.title}")
                output.append(f"**Source:** {entry.source_metadata.source} ({entry.source_metadata.source_type.value})")
                if entry.source_metadata.chapter:
                    output.append(f"**Chapter:** {entry.source_metadata.chapter}")
                if entry.source_metadata.verse:
                    output.append(f"**Verse:** {entry.source_metadata.verse}")
                output.append(entry.content[:500] + "..." if len(entry.content) > 500 else entry.content)
                output.append("")

        output.append("---")
        output.append("*Comparison based on available corpus sources. For comprehensive study, consult original texts.*")

        all_entries = result1.entries + result2.entries
        sources = self._format_sources(all_entries)

        return AgentResponse(
            answer="\n".join(output),
            sources=sources,
            query=concept,
            language=effective_language,
            depth="comparison",
            used_web_fallback=False,
        )

    async def get_concept_graph(self, concept: str) -> dict:
        """Get concept relationship graph."""
        return self.engine.get_concept_graph(concept)

    def get_learning_path(self, topic: str) -> list[dict]:
        """Get structured learning path."""
        return self.engine.get_learning_path(topic)

    def get_domain_overview(self, domain_name: str) -> str:
        """Get domain overview."""
        return self.engine.get_domain_overview(domain_name)

    def search(
        self,
        query: str,
        domain: str | VedicDomain | None = None,
        limit: int = 10,
        language: Language = Language.ENGLISH,
    ) -> QueryResult:
        """Direct search without answer generation."""
        detected_lang, english_query, _ = self._multilingual.process(query)
        effective_language = language if language != Language.ENGLISH else detected_lang

        return self.engine.query(english_query, domain=domain, limit=limit, language=effective_language)

    def _format_answer(
        self,
        explanation: str,
        entries: list[VedicKnowledgeEntry],
        query: str,
        language: Language,
        depth: str,
    ) -> str:
        """Format the final answer."""
        # For now, return the explanation as-is
        # In production, this would adapt to language and depth
        return explanation

    def _format_sources(self, entries: list[VedicKnowledgeEntry]) -> list[dict]:
        """Format sources for response."""
        sources = []
        for entry in entries:
            sources.append(self._format_source(entry))
        return sources

    def _format_source(self, entry: VedicKnowledgeEntry) -> dict:
        """Format a single source."""
        return {
            "entry_id": entry.id,
            "title": entry.title,
            "domain": entry.domain.value,
            "category": entry.category,
            "subcategory": entry.subcategory,
            "source": entry.source_metadata.source,
            "source_type": entry.source_metadata.source_type.value,
            "chapter": entry.source_metadata.chapter,
            "verse": entry.source_metadata.verse,
            "source_url": entry.source_metadata.source_url,
            "retrieved_at": entry.source_metadata.retrieved_at,
        }

    def _format_web_answer(
        self,
        web_results: list,
        query: str,
        language: Language,
        depth: str,
    ) -> str:
        """Format answer from web results."""
        output = [f"# Web Search Results for: {query}", ""]
        output.append("⚠️ **Note:** These results are from web search and have not been fully verified. "
                      "Please cross-reference with primary texts.")
        output.append("")

        for i, result in enumerate(web_results[:5], 1):
            output.append(f"## {i}. {result.title}")
            output.append(f"**Source:** {result.url}")
            output.append(f"**Type:** {result.source_type.value}")
            output.append(f"**Confidence:** {result.confidence:.0%}")
            output.append(f"**Snippet:** {result.snippet}")
            output.append("")

        return "\n".join(output)

    def _format_web_sources(self, web_results: list) -> list[dict]:
        """Format web sources."""
        return [r.to_dict() for r in web_results]

    async def _search_web(
        self,
        query: str,
        domain: str | VedicDomain | None = None,
    ) -> list:
        """Search the web for additional information."""
        if self._web_client is None:
            self._web_client = get_web_search_client(self._web_config)

        vedic_domain = None
        if domain:
            if isinstance(domain, str):
                try:
                    vedic_domain = VedicDomain(domain)
                except ValueError:
                    pass
            else:
                vedic_domain = domain

        return await self._web_client.search(query, domain=vedic_domain, limit=self._web_config.max_results)

    # Corpus management methods
    def ingest_corpus(self, path: str) -> dict:
        """Ingest corpus from path."""
        result = self._corpus_manager.ingest(path)
        return {
            "files_processed": result.files_processed,
            "entries_added": result.entries_added,
            "chunks_created": result.chunks_created,
            "duplicates_skipped": result.duplicates_skipped,
            "errors": result.errors,
        }

    def validate_corpus(self) -> dict:
        """Validate the corpus."""
        return self._corpus_manager.validate()

    def get_corpus_report(self) -> str:
        """Get corpus validation report."""
        return self._corpus_manager.generate_report()

    def get_stats(self) -> dict:
        """Get agent and corpus stats."""
        return {
            "corpus": self.kb.get_stats(),
            "agent": {
                "web_fallback_enabled": self._enable_web_fallback,
                "domains_loaded": len(self.kb.domains),
            },
        }


# Convenience function for creating agent with default corpus
def create_vedic_knowledge_agent(
    knowledge_base: VedicKnowledgeBase | None = None,
    enable_web_fallback: bool = True,
) -> VedicKnowledgeAgent:
    """Create a VedicKnowledgeAgent, optionally with a provided knowledge base."""
    if knowledge_base is None:
        # Create empty knowledge base - would be populated via ingestion
        knowledge_base = VedicKnowledgeBase()

    return VedicKnowledgeAgent(
        knowledge_base=knowledge_base,
        enable_web_fallback=enable_web_fallback,
    )