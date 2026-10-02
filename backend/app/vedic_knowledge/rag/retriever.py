"""RAG / Semantic Retrieval for Vedic Knowledge System."""

import logging
import hashlib
from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict

from ..base import (
    VedicKnowledgeBase,
    VedicKnowledgeEntry,
    KnowledgeChunk,
    SourceType,
    Language,
    VedicDomain,
)
from ..multilingual.processor import get_multilingual_processor

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Result from a retrieval operation."""
    query: str
    chunks: list[KnowledgeChunk]
    entries: list[VedicKnowledgeEntry]
    scores: list[float]
    retrieval_method: str
    total_candidates: int
    language: Language


@dataclass
class RetrievalConfig:
    """Configuration for retrieval."""
    keyword_weight: float = 1.0
    semantic_weight: float = 1.5
    metadata_boost: float = 2.0
    concept_boost: float = 2.5
    exact_source_boost: float = 3.0
    max_chunks_per_entry: int = 3
    min_score_threshold: float = 0.3
    cross_domain: bool = True


class KeywordIndex:
    """Inverted index for keyword search."""

    def __init__(self):
        self._index: dict[str, set[str]] = defaultdict(set)  # term -> entry_ids
        self._chunk_index: dict[str, set[str]] = defaultdict(set)  # term -> chunk_ids

    def add_entry(self, entry: VedicKnowledgeEntry):
        terms = self._extract_terms(entry)
        for term in terms:
            self._index[term].add(entry.id)
            for chunk in entry.chunks:
                self._chunk_index[term].add(chunk.id)

    def add_chunk(self, chunk: KnowledgeChunk):
        terms = self._extract_terms_from_text(chunk.content)
        for term in terms:
            self._chunk_index[term].add(chunk.id)

    def _extract_terms(self, entry: VedicKnowledgeEntry) -> set[str]:
        terms = set()
        # Title terms
        terms.update(self._extract_terms_from_text(entry.title))
        # Content terms
        terms.update(self._extract_terms_from_text(entry.content))
        # Tags
        terms.update(tag.lower() for tag in entry.tags)
        # Concepts
        terms.update(c.lower() for c in entry.source_metadata.concepts)
        # Keywords
        terms.update(k.lower() for k in entry.source_metadata.keywords)
        # Topics
        terms.update(t.lower() for t in entry.source_metadata.topics)
        # Domain/Category
        terms.add(entry.domain.value)
        terms.add(entry.category)
        terms.add(entry.subcategory)
        return terms

    def _extract_terms_from_text(self, text: str) -> set[str]:
        # Simple tokenization - can be enhanced
        words = text.lower().split()
        # Filter out very short words and common stopwords
        stopwords = {"the", "and", "or", "of", "in", "to", "a", "is", "for", "with", "on", "as", "by", "an", "be", "this", "that", "from"}
        return {w for w in words if len(w) >= 3 and w not in stopwords}

    def search(self, query: str, limit: int = 20) -> list[str]:
        query_terms = self._extract_terms_from_text(query)
        if not query_terms:
            return []

        entry_scores: dict[str, int] = defaultdict(int)
        for term in query_terms:
            # Exact match
            if term in self._index:
                for entry_id in self._index[term]:
                    entry_scores[entry_id] += 3
            # Partial match
            for idx_term, entry_ids in self._index.items():
                if term in idx_term or idx_term in term:
                    for entry_id in entry_ids:
                        entry_scores[entry_id] += 1

        # Sort by score
        sorted_entries = sorted(entry_scores.items(), key=lambda x: x[1], reverse=True)
        return [eid for eid, _ in sorted_entries[:limit]]

    def search_chunks(self, query: str, limit: int = 20) -> list[str]:
        query_terms = self._extract_terms_from_text(query)
        if not query_terms:
            return []

        chunk_scores: dict[str, int] = defaultdict(int)
        for term in query_terms:
            if term in self._chunk_index:
                for chunk_id in self._chunk_index[term]:
                    chunk_scores[chunk_id] += 3
            for idx_term, chunk_ids in self._chunk_index.items():
                if term in idx_term or idx_term in term:
                    for chunk_id in chunk_ids:
                        chunk_scores[chunk_id] += 1

        sorted_chunks = sorted(chunk_scores.items(), key=lambda x: x[1], reverse=True)
        return [cid for cid, _ in sorted_chunks[:limit]]


class SemanticRetriever:
    """Semantic retriever with multiple retrieval strategies."""

    def __init__(self, knowledge_base: VedicKnowledgeBase, config: RetrievalConfig | None = None):
        self.kb = knowledge_base
        self.config = config or RetrievalConfig()
        self._keyword_index = KeywordIndex()
        self._chunk_map: dict[str, KnowledgeChunk] = {}  # chunk_id -> chunk
        self._entry_chunk_map: dict[str, list[str]] = defaultdict(list)  # entry_id -> chunk_ids
        self._initialized = False
        self._multilingual = get_multilingual_processor()

    def initialize(self):
        """Build indices from knowledge base."""
        if self._initialized:
            return

        logger.info("[RAG] Building keyword index...")
        for domain in self.kb.domains.values():
            for entry in domain.entries.values():
                self._keyword_index.add_entry(entry)
                for chunk in entry.chunks:
                    self._chunk_map[chunk.id] = chunk
                    self._entry_chunk_map[entry.id].append(chunk.id)

        self._initialized = True
        logger.info(f"[RAG] Index built: {len(self._keyword_index._index)} terms, {len(self._chunk_map)} chunks")

    def retrieve(
        self,
        query: str,
        domain: str | VedicDomain | None = None,
        limit: int = 10,
        language: Language = Language.ENGLISH,
    ) -> RetrievalResult:
        """Main retrieval method combining keyword and semantic search."""
        if not self._initialized:
            self.initialize()

        # Process multilingual query
        detected_lang, english_query, sanskrit_terms = self._multilingual.process(query)
        effective_language = language if language != Language.ENGLISH else detected_lang

        # Expand query with Sanskrit terms
        expanded_query = english_query
        if sanskrit_terms:
            expanded_query += " " + " ".join(sanskrit_terms)

        # Keyword search
        keyword_entry_ids = self._keyword_index.search(expanded_query, limit * 3)
        keyword_chunk_ids = self._keyword_index.search_chunks(expanded_query, limit * 3)

        # Collect candidates
        candidate_entries: dict[str, float] = {}
        candidate_chunks: dict[str, float] = {}

        # Score keyword matches
        for entry_id in keyword_entry_ids:
            entry = self.kb.get_entry(entry_id)
            if entry and (not domain or entry.domain.value == (domain.value if isinstance(domain, VedicDomain) else domain)):
                score = self._score_entry(entry, expanded_query, sanskrit_terms)
                if score >= self.config.min_score_threshold:
                    candidate_entries[entry_id] = score

        for chunk_id in keyword_chunk_ids:
            chunk = self._chunk_map.get(chunk_id)
            if chunk:
                entry = self.kb.get_entry(chunk.source_metadata.document_id)
                if entry and (not domain or entry.domain.value == (domain.value if isinstance(domain, VedicDomain) else domain)):
                    score = self._score_chunk(chunk, expanded_query, sanskrit_terms)
                    if score >= self.config.min_score_threshold:
                        candidate_chunks[chunk_id] = score

        # Sort and limit
        sorted_entries = sorted(candidate_entries.items(), key=lambda x: x[1], reverse=True)
        sorted_chunks = sorted(candidate_chunks.items(), key=lambda x: x[1], reverse=True)

        # Limit chunks per entry
        final_chunks = []
        entry_chunk_count = defaultdict(int)
        for chunk_id, score in sorted_chunks:
            chunk = self._chunk_map[chunk_id]
            entry_id = chunk.source_metadata.document_id
            if entry_chunk_count[entry_id] < self.config.max_chunks_per_entry:
                final_chunks.append((chunk_id, score))
                entry_chunk_count[entry_id] += 1
            if len(final_chunks) >= limit:
                break

        # Get entries for chunks
        final_entries = []
        seen_entries = set()
        for chunk_id, _ in final_chunks:
            chunk = self._chunk_map[chunk_id]
            entry_id = chunk.source_metadata.document_id
            if entry_id not in seen_entries:
                entry = self.kb.get_entry(entry_id)
                if entry:
                    final_entries.append(entry)
                    seen_entries.add(entry_id)

        # Add top entries that weren't included via chunks
        for entry_id, score in sorted_entries:
            if entry_id not in seen_entries and len(final_entries) < limit:
                entry = self.kb.get_entry(entry_id)
                if entry:
                    final_entries.append(entry)
                    seen_entries.add(entry_id)

        return RetrievalResult(
            query=query,
            chunks=[self._chunk_map[cid] for cid, _ in final_chunks],
            entries=final_entries[:limit],
            scores=[s for _, s in final_chunks],
            retrieval_method="keyword+semantic",
            total_candidates=len(candidate_entries) + len(candidate_chunks),
            language=effective_language,
        )

    def retrieve_by_concept(self, concept: str, limit: int = 10) -> RetrievalResult:
        """Retrieve entries related to a specific concept."""
        return self.retrieve(concept, limit=limit)

    def retrieve_by_source(self, source: str, limit: int = 10) -> RetrievalResult:
        """Retrieve entries from a specific source."""
        entries = []
        for domain in self.kb.domains.values():
            for entry in domain.entries.values():
                if source.lower() in entry.source_metadata.source.lower():
                    entries.append(entry)
                    if len(entries) >= limit:
                        break
        return RetrievalResult(
            query=f"source:{source}",
            chunks=[],
            entries=entries[:limit],
            scores=[1.0] * len(entries),
            retrieval_method="exact_source",
            total_candidates=len(entries),
            language=Language.ENGLISH,
        )

    def retrieve_by_metadata(
        self,
        category: str | None = None,
        subcategory: str | None = None,
        source_type: SourceType | None = None,
        tags: list[str] | None = None,
        limit: int = 10,
    ) -> RetrievalResult:
        """Retrieve entries by metadata filters."""
        entries = []
        for domain in self.kb.domains.values():
            for entry in domain.entries.values():
                if category and entry.category != category:
                    continue
                if subcategory and entry.subcategory != subcategory:
                    continue
                if source_type and entry.source_metadata.source_type != source_type:
                    continue
                if tags and not any(t in entry.tags for t in tags):
                    continue
                entries.append(entry)
                if len(entries) >= limit:
                    break

        return RetrievalResult(
            query=f"metadata_filter",
            chunks=[],
            entries=entries[:limit],
            scores=[1.0] * len(entries),
            retrieval_method="metadata_filter",
            total_candidates=len(entries),
            language=Language.ENGLISH,
        )

    def _score_entry(self, entry: VedicKnowledgeEntry, query: str, sanskrit_terms: list[str]) -> float:
        score = entry.matches_query(query) * self.config.keyword_weight

        # Boost for Sanskrit concept matches
        for term in sanskrit_terms:
            if term in entry.source_metadata.concepts:
                score += self.config.concept_boost
            for concept in entry.source_metadata.concepts:
                if term in concept.lower() or concept.lower() in term:
                    score += self.config.concept_boost * 0.5

        # Boost for exact source type matches
        if entry.source_metadata.source_type in (SourceType.PRIMARY_TEXT, SourceType.TRANSLATION):
            score += self.config.exact_source_boost * 0.5

        return score

    def _score_chunk(self, chunk: KnowledgeChunk, query: str, sanskrit_terms: list[str]) -> float:
        score = 0.0
        query_lower = query.lower()
        content_lower = chunk.content.lower()

        # Keyword matches in chunk
        for term in query_lower.split():
            if len(term) >= 3 and term in content_lower:
                score += 1.0

        # Sanskrit term boost
        for term in sanskrit_terms:
            if term.lower() in content_lower:
                score += self.config.concept_boost

        # Source type boost
        if chunk.source_metadata.source_type in (SourceType.PRIMARY_TEXT, SourceType.TRANSLATION):
            score += self.config.exact_source_boost * 0.3

        return score


class HybridRetriever:
    """Hybrid retriever combining local corpus with web fallback."""

    def __init__(self, knowledge_base: VedicKnowledgeBase):
        self.local_retriever = SemanticRetriever(knowledge_base)
        self._web_fallback_enabled = True

    def retrieve(
        self,
        query: str,
        domain: str | VedicDomain | None = None,
        limit: int = 10,
        language: Language = Language.ENGLISH,
        use_web_fallback: bool = True,
    ) -> tuple[RetrievalResult, bool]:
        """Retrieve from local corpus, with optional web fallback indicator."""
        result = self.local_retriever.retrieve(query, domain, limit, language)

        # Check if we should suggest web fallback
        needs_web_fallback = (
            use_web_fallback
            and self._web_fallback_enabled
            and (len(result.entries) < 3 or max(result.scores, default=0) < 0.5)
        )

        return result, needs_web_fallback

    def enable_web_fallback(self, enabled: bool = True):
        self._web_fallback_enabled = enabled

    def initialize(self):
        self.local_retriever.initialize()