"""Vedic Knowledge Agent — integrated with JARVIS orchestrator."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Any

from .indian_knowledge import KnowledgeEngine, QueryResult
from .indian_knowledge.base import KnowledgeBase, KnowledgeEntry, DifficultyLevel
from .indian_knowledge.embeddings import EmbeddingEngine, get_embedding_engine
from .indian_knowledge.concept_graph import ConceptGraph, get_concept_graph
from .indian_knowledge.multilingual import (
    MultilingualProcessor, get_multilingual_processor,
    SupportedLanguage, detect_language, expand_query_with_transliterations
)
from .indian_knowledge.web_fallback import (
    WebIngestionPipeline, search_web, fetch_and_validate,
    WebSource, SourceType, ValidationStatus
)
from .indian_knowledge.corpus_manager import CorpusManager, get_corpus_manager, CorpusValidationReport
from .agent_manager import get_agent_manager, AgentDefinition, PermissionLevel

logger = logging.getLogger(__name__)


class ResponseDepth:
    SHORT = "short"
    DETAILED = "detailed"
    BEGINNER = "beginner"
    ADVANCED = "advanced"
    COMPARISON = "comparison"
    SOURCE_FOCUSED = "source_focused"
    HISTORICAL = "historical"


@dataclass
class VedicQueryContext:
    original_query: str
    processed_query: str
    detected_language: SupportedLanguage
    expanded_queries: list[str]
    depth: str
    domain_filter: Optional[str] = None
    category_filter: Optional[str] = None
    concept_focus: list[str] = None

    def __post_init__(self):
        if self.concept_focus is None:
            self.concept_focus = []


@dataclass
class VedicResponse:
    answer: str
    sources: list[dict]
    concepts: list[str]
    cross_domain_links: dict[str, list[str]]
    confidence: float
    depth: str
    language: SupportedLanguage
    used_web_fallback: bool
    web_sources: list[dict] = None

    def __post_init__(self):
        if self.web_sources is None:
            self.web_sources = []


class VedicKnowledgeAgent:
    """
    Vedic Knowledge Agent for JARVIS.

    Priority 1: Local verified Vedic Knowledge Corpus
    Priority 2: Previously verified/indexed external sources
    Priority 3: Google/Web search when required information is unavailable locally
    """

    def __init__(self, corpus_root: Optional[str] = None):
        self.corpus_manager = get_corpus_manager(corpus_root)
        self.knowledge_engine = KnowledgeEngine(self.corpus_manager.kb)
        self.embedding_engine = get_embedding_engine()
        self.concept_graph = get_concept_graph()
        self.multilingual = get_multilingual_processor()
        self.web_pipeline = WebIngestionPipeline(self.corpus_manager.corpus_root / "sources")

        self._initialized = False
        self._query_count = 0
        self._web_fallback_count = 0
        self._local_hits = 0

        logger.info("[VEDIC_AGENT] VedicKnowledgeAgent initialized")

    def initialize(self) -> CorpusValidationReport:
        if self._initialized:
            return self.corpus_manager.validate_corpus()

        report = self.corpus_manager.load_corpus()
        self._initialized = True
        logger.info(f"[VEDIC_AGENT] Corpus loaded: {report.total_documents} documents")
        return report

    def query(self, query: str, depth: str = ResponseDepth.DETAILED,
              domain: Optional[str] = None, category: Optional[str] = None) -> VedicResponse:
        if not self._initialized:
            self.initialize()

        self._query_count += 1
        context = self._process_query(query, depth, domain, category)

        local_results = self._search_local(context)

        if local_results.entries:
            self._local_hits += 1
            response = self._format_local_response(context, local_results)
        else:
            response = self._search_web_fallback(context)

        self._enrich_with_concepts(response, context)
        return response

    def _process_query(self, query: str, depth: str,
                       domain: Optional[str], category: Optional[str]) -> VedicQueryContext:
        ml_result = self.multilingual.process_query(query)

        return VedicQueryContext(
            original_query=query,
            processed_query=ml_result["english_query"],
            detected_language=SupportedLanguage(ml_result["detected_language"]),
            expanded_queries=ml_result["expanded_queries"],
            depth=depth,
            domain_filter=domain,
            category_filter=category,
        )

    def _search_local(self, context: VedicQueryContext) -> QueryResult:
        all_entries = []

        for expanded_query in context.expanded_queries:
            result = self.knowledge_engine.query(
                expanded_query,
                domain=context.domain_filter,
                limit=10,
                min_score=0.3,
            )
            all_entries.extend(result.entries)

        seen_ids = set()
        unique_entries = []
        for entry in all_entries:
            if entry.id not in seen_ids:
                seen_ids.add(entry.id)
                unique_entries.append(entry)

        return QueryResult(
            query=context.processed_query,
            entries=unique_entries[:15],
            domain_filter=context.domain_filter,
            total_found=len(unique_entries),
            suggestions=[],
        )

    def _search_semantic(self, context: VedicQueryContext) -> list[tuple[float, dict]]:
        results = self.embedding_engine.search(
            context.processed_query,
            top_k=10,
            domain_filter=context.domain_filter,
            category_filter=context.category_filter,
        )
        return [(score, meta.__dict__) for score, meta in results]

    def _search_concepts(self, context: VedicQueryContext) -> list[tuple[float, dict]]:
        if not context.concept_focus:
            return []

        results = self.embedding_engine.search_by_concept(
            context.concept_focus,
            top_k=10,
            domain_filter=context.domain_filter,
        )
        return [(score, meta.__dict__) for score, meta in results]

    def _format_local_response(self, context: VedicQueryContext, results: QueryResult) -> VedicResponse:
        if not results.entries:
            return self._empty_response(context, "No local knowledge found")

        answer_parts = []
        sources = []
        concepts = set()

        for entry in results.entries:
            formatted = self._format_entry(entry, context.depth, context.detected_language)
            answer_parts.append(formatted)

            sources.append({
                "entry_id": entry.id,
                "title": entry.title,
                "domain": entry.domain,
                "category": entry.category,
                "source": entry.metadata.get("source", "Unknown"),
                "source_type": entry.metadata.get("source_type", "unknown"),
                "chapter": entry.metadata.get("chapter"),
                "section": entry.metadata.get("section"),
                "verse": entry.metadata.get("verse"),
                "translator": entry.metadata.get("translator"),
                "commentator": entry.metadata.get("commentator"),
            })

            concepts.update(entry.metadata.get("concepts", []))
            concepts.update(entry.metadata.get("topics", []))
            concepts.update(entry.tags)

        cross_domain = self._get_cross_domain_links(list(concepts))

        answer = self._join_answer_parts(answer_parts, context.depth, context.detected_language)

        return VedicResponse(
            answer=answer,
            sources=sources,
            concepts=list(concepts)[:15],
            cross_domain_links=cross_domain,
            confidence=0.9 if results.entries else 0.3,
            depth=context.depth,
            language=context.detected_language,
            used_web_fallback=False,
        )

    def _search_web_fallback(self, context: VedicQueryContext) -> VedicResponse:
        self._web_fallback_count += 1
        logger.info(f"[VEDIC_AGENT] Web fallback for: {context.processed_query}")

        domain = context.domain_filter or "vedic_literature"
        category = context.category_filter or "general"

        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        new_entries = loop.run_until_complete(
            self.web_pipeline.search_and_ingest(context.processed_query, domain, category, max_results=3)
        )

        if new_entries:
            for entry in new_entries:
                domain_obj = self.corpus_manager.kb.get_domain(entry.domain)
                if domain_obj:
                    domain_obj.add_entry(entry)
                self.corpus_manager._chunk_and_embed(entry)

            self.corpus_manager.concept_graph.build_from_knowledge_base(self.corpus_manager.kb)

            local_results = self._search_local(context)
            if local_results.entries:
                response = self._format_local_response(context, local_results)
                response.used_web_fallback = True
                response.web_sources = [
                    {"title": e.metadata.get("source", ""), "url": e.metadata.get("source_url", "")}
                    for e in new_entries
                ]
                return response

        search_result = loop.run_until_complete(search_web(context.processed_query, max_results=5))

        web_sources = []
        answer_parts = []

        for source in search_result.sources:
            if source.validation_status == ValidationStatus.VALIDATED:
                web_sources.append({
                    "title": source.title,
                    "url": source.url,
                    "source_type": source.source_type.value,
                    "validation": source.validation_notes,
                })
                answer_parts.append(f"**Source:** {source.title}\n{source.content[:1500]}")

        if answer_parts:
            answer = "\n\n---\n\n".join(answer_parts)
            answer = self._translate_if_needed(answer, context.detected_language)
        else:
            answer = self._empty_response(context, "No reliable web sources found").answer

        return VedicResponse(
            answer=answer,
            sources=[],
            concepts=[],
            cross_domain_links={},
            confidence=0.5,
            depth=context.depth,
            language=context.detected_language,
            used_web_fallback=True,
            web_sources=web_sources,
        )

    def _format_entry(self, entry: KnowledgeEntry, depth: str, language: SupportedLanguage) -> str:
        parts = []

        if depth in (ResponseDepth.DETAILED, ResponseDepth.ADVANCED, ResponseDepth.SOURCE_FOCUSED, ResponseDepth.HISTORICAL):
            parts.append(f"## {entry.title}")
            parts.append(f"**Domain:** {entry.domain} | **Category:** {entry.category}")

            if depth in (ResponseDepth.SOURCE_FOCUSED, ResponseDepth.HISTORICAL):
                source = entry.metadata.get("source", "Unknown")
                source_type = entry.metadata.get("source_type", "unknown")
                parts.append(f"**Source:** {source} ({source_type})")
                if entry.metadata.get("translator"):
                    parts.append(f"**Translator:** {entry.metadata['translator']}")
                if entry.metadata.get("commentator"):
                    parts.append(f"**Commentator:** {entry.metadata['commentator']}")
                if entry.metadata.get("chapter"):
                    parts.append(f"**Chapter:** {entry.metadata['chapter']}")
                if entry.metadata.get("verse"):
                    parts.append(f"**Verse:** {entry.metadata['verse']}")
                if entry.metadata.get("source_url"):
                    parts.append(f"**URL:** {entry.metadata['source_url']}")

        if depth == ResponseDepth.BEGINNER:
            parts.append(self._simplify_content(entry.content))
        elif depth == ResponseDepth.ADVANCED:
            parts.append(entry.content)
        elif depth == ResponseDepth.COMPARISON:
            parts.append(self._format_for_comparison(entry))
        else:
            parts.append(entry.content[:2000] + ("..." if len(entry.content) > 2000 else ""))

        if entry.examples and depth in (ResponseDepth.DETAILED, ResponseDepth.BEGINNER, ResponseDepth.ADVANCED):
            parts.append("\n**Examples:**")
            for ex in entry.examples[:3]:
                parts.append(f"- {ex}")

        if entry.references and depth in (ResponseDepth.SOURCE_FOCUSED, ResponseDepth.HISTORICAL, ResponseDepth.ADVANCED):
            parts.append("\n**References:**")
            for ref in entry.references[:5]:
                parts.append(f"- {ref}")

        result = "\n".join(parts)
        return self._translate_if_needed(result, language)

    def _simplify_content(self, content: str) -> str:
        sentences = content.split('. ')
        simple = []
        for s in sentences[:5]:
            s = s.strip()
            if s and len(s) > 20:
                simple.append(s)
        return '. '.join(simple) + ('.' if simple else '')

    def _format_for_comparison(self, entry: KnowledgeEntry) -> str:
        return f"**{entry.title}** ({entry.domain}/{entry.category}):\n{entry.content[:1500]}"

    def _join_answer_parts(self, parts: list[str], depth: str, language: SupportedLanguage) -> str:
        if depth == ResponseDepth.SHORT:
            return parts[0][:500] if parts else ""
        return "\n\n---\n\n".join(parts)

    def _translate_if_needed(self, text: str, language: SupportedLanguage) -> str:
        if language == SupportedLanguage.ENGLISH:
            return text
        return self.multilingual.format_response(text, language)

    def _empty_response(self, context: VedicQueryContext, message: str) -> VedicResponse:
        translated = self._translate_if_needed(message, context.detected_language)
        return VedicResponse(
            answer=translated,
            sources=[],
            concepts=[],
            cross_domain_links={},
            confidence=0.0,
            depth=context.depth,
            language=context.detected_language,
            used_web_fallback=False,
        )

    def _enrich_with_concepts(self, response: VedicResponse, context: VedicQueryContext):
        if not response.concepts:
            return

        for concept in response.concepts[:5]:
            related = self.concept_graph.get_related_concepts(concept, limit=5)
            if related:
                response.cross_domain_links[concept] = [c for c, _ in related]

    def _get_cross_domain_links(self, concepts: list[str]) -> dict[str, list[str]]:
        links = {}
        for concept in concepts[:5]:
            cross_domain = self.concept_graph.get_cross_domain_concepts(concept)
            if cross_domain:
                links[concept] = cross_domain
        return links

    def explain(self, topic: str, depth: str = ResponseDepth.DETAILED) -> str:
        response = self.query(topic, depth=depth)
        return response.answer

    def compare(self, concept1: str, concept2: str, depth: str = ResponseDepth.COMPARISON) -> str:
        query = f"Compare {concept1} and {concept2}"
        response = self.query(query, depth=depth)
        return response.answer

    def get_concept_details(self, concept: str) -> dict:
        node = self.concept_graph.get_concept(concept)
        if not node:
            return {"found": False, "concept": concept}

        return {
            "found": True,
            "concept": node.canonical_name,
            "aliases": node.aliases,
            "domains": node.domains,
            "categories": node.categories,
            "related_concepts": node.related_concepts,
            "entry_count": len(node.entry_ids),
            "source_evidence": node.source_evidence,
            "languages": node.languages,
        }

    def get_domain_overview(self, domain: str) -> str:
        return self.knowledge_engine.get_domain_overview(domain)

    def get_learning_path(self, topic: str) -> list[dict]:
        return self.knowledge_engine.get_learning_path(topic)

    def get_stats(self) -> dict:
        corpus_stats = self.corpus_manager.get_corpus_stats()
        return {
            "agent": {
                "queries_processed": self._query_count,
                "local_hits": self._local_hits,
                "web_fallbacks": self._web_fallback_count,
                "local_hit_rate": round(self._local_hits / max(self._query_count, 1) * 100, 1),
            },
            "corpus": corpus_stats,
        }

    def validate_corpus(self) -> CorpusValidationReport:
        return self.corpus_manager.validate_corpus()

    def ingest_web_source(self, query: str, domain: str, category: str) -> list:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.web_pipeline.search_and_ingest(query, domain, category))

    def get_web_ingestion_report(self) -> dict:
        return self.web_pipeline.get_ingestion_report()


_vedic_agent: VedicKnowledgeAgent | None = None


def get_vedic_agent(corpus_root: Optional[str] = None) -> VedicKnowledgeAgent:
    global _vedic_agent
    if _vedic_agent is None:
        _vedic_agent = VedicKnowledgeAgent(corpus_root)
    return _vedic_agent


async def execute_vedic_knowledge_agent(args: dict, context: dict | None = None) -> dict:
    agent = get_vedic_agent()
    query = args.get("query", "")
    depth = args.get("depth", "detailed")
    domain = args.get("domain")
    category = args.get("category")

    response = agent.query(query, depth=depth, domain=domain, category=category)

    return {
        "success": True,
        "answer": response.answer,
        "sources": response.sources,
        "concepts": response.concepts,
        "cross_domain_links": response.cross_domain_links,
        "confidence": response.confidence,
        "depth": response.depth,
        "language": response.language.value,
        "used_web_fallback": response.used_web_fallback,
        "web_sources": response.web_sources,
    }